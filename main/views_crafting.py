"""
Crafting System API Views
Handles crafting recipes, attempts, and character progression through crafting
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import random

from .models import (
    Character, CraftingRecipe, CraftingAttempt, 
    ItemTemplate, InventoryItem, Skill, GameEvent
)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def available_recipes(request):
    """Get all crafting recipes available to the character"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Get all active recipes
    recipes = CraftingRecipe.objects.filter(is_active=True)
    
    available = []
    for recipe in recipes:
        can_craft, reason = recipe.can_craft(character)
        success_rate = recipe.calculate_success_rate(character)
        
        # Get required materials
        materials = []
        for material in recipe.get_required_materials():
            # Check how many character has
            try:
                inventory_item = character.inventory.get(item_template__name=material.material_name)
                have_quantity = inventory_item.quantity
            except InventoryItem.DoesNotExist:
                have_quantity = 0
            
            materials.append({
                'name': material.material_name,
                'required': material.quantity_required,
                'have': have_quantity,
                'is_sufficient': have_quantity >= material.quantity_required
            })
        
        available.append({
            'id': str(recipe.id),
            'name': recipe.name,
            'description': recipe.description,
            'category': recipe.category,
            'result_item': {
                'name': recipe.result_item.name,
                'description': recipe.result_item.description,
                'type': recipe.result_item.item_type,
                'rarity': recipe.result_item.rarity,
            },
            'result_quantity': recipe.result_quantity,
            'required_level': recipe.required_level,
            'required_skill_level': recipe.required_skill_level,
            'craft_time_seconds': recipe.craft_time_seconds,
            'experience_reward': recipe.experience_reward,
            'materials': materials,
            'can_craft': can_craft,
            'reason': reason if not can_craft else None,
            'success_rate': round(success_rate * 100, 1),
        })
    
    # Sort by category, then by required level
    available.sort(key=lambda x: (x['category'], x['required_level']))
    
    return JsonResponse({
        'success': True,
        'recipes': available,
        'character': {
            'name': character.name,
            'level': character.level,
            'crafting_skill': get_crafting_skill_level(character)
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_crafting(request):
    """Start crafting an item"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    data = json.loads(request.body)
    recipe_id = data.get('recipe_id')
    
    if not recipe_id:
        return JsonResponse({'error': 'Recipe ID required'}, status=400)
    
    recipe = get_object_or_404(CraftingRecipe, id=recipe_id, is_active=True)
    
    # Check if character can act
    if not character.can_act():
        return JsonResponse({'error': 'Character cannot craft (in combat or no stamina)'}, status=400)
    
    # Check if character can craft this recipe
    can_craft, reason = recipe.can_craft(character)
    if not can_craft:
        return JsonResponse({'error': reason}, status=400)
    
    # Calculate success rate
    success_rate = recipe.calculate_success_rate(character)
    
    # Consume materials first (so they're used even if craft fails)
    materials_consumed = []
    for material in recipe.get_required_materials():
        if material.is_consumed:
            inventory_item = character.inventory.get(item_template__name=material.material_name)
            
            # Remove materials
            inventory_item.quantity -= material.quantity_required
            if inventory_item.quantity <= 0:
                inventory_item.delete()
            else:
                inventory_item.save()
            
            materials_consumed.append({
                'name': material.material_name,
                'quantity': material.quantity_required
            })
    
    # Attempt the craft
    is_success = random.random() <= success_rate
    
    # Create crafting attempt record
    attempt = CraftingAttempt.objects.create(
        character=character,
        recipe=recipe,
        status='success' if is_success else 'failure',
        success_rate_used=success_rate,
        materials_consumed=materials_consumed,
        completed_at=timezone.now()
    )
    
    result_items = []
    if is_success:
        # Give result items
        for _ in range(recipe.result_quantity):
            inventory_item = character.add_item_to_inventory(
                recipe.result_item.name, 
                1
            )
            result_items.append({
                'name': recipe.result_item.name,
                'quantity': 1,
                'total_quantity': inventory_item.quantity
            })
        
        # Record items created
        attempt.items_created = result_items
        attempt.save()
        
        # Give experience
        experience_gained = recipe.experience_reward
        character.gain_experience(experience_gained)
        
        # Give crafting skill experience
        crafting_skill = get_or_create_crafting_skill(character)
        crafting_skill.gain_experience(recipe.experience_reward // 2)
        
        attempt.experience_gained = experience_gained
        attempt.save()
        
        # Create success event
        GameEvent.objects.create(
            character=character,
            event_type='item_found',
            title='Crafting Success!',
            message=f"Successfully crafted {recipe.result_quantity}x {recipe.result_item.name}",
            data={
                'recipe': recipe.name,
                'items_created': result_items,
                'experience': experience_gained
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully crafted {recipe.result_quantity}x {recipe.result_item.name}!',
            'result': {
                'crafted': True,
                'items_created': result_items,
                'experience_gained': experience_gained,
                'success_rate_used': round(success_rate * 100, 1)
            }
        })
    
    else:
        # Crafting failed
        GameEvent.objects.create(
            character=character,
            event_type='item_found',
            title='Crafting Failed',
            message=f"Failed to craft {recipe.result_item.name}. Materials were consumed.",
            data={
                'recipe': recipe.name,
                'materials_lost': materials_consumed
            }
        )
        
        return JsonResponse({
            'success': True,  # API call succeeded, but crafting failed
            'message': f'Failed to craft {recipe.result_item.name}. Better luck next time!',
            'result': {
                'crafted': False,
                'materials_consumed': materials_consumed,
                'success_rate_used': round(success_rate * 100, 1)
            }
        })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def crafting_history(request):
    """Get character's recent crafting history"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Get recent crafting attempts (last 20)
    attempts = CraftingAttempt.objects.filter(
        character=character
    ).order_by('-created_at')[:20]
    
    history = []
    for attempt in attempts:
        history.append({
            'id': str(attempt.id),
            'recipe_name': attempt.recipe.name,
            'status': attempt.get_status_display(),
            'success_rate_used': round(attempt.success_rate_used * 100, 1),
            'items_created': attempt.items_created,
            'materials_consumed': attempt.materials_consumed,
            'experience_gained': attempt.experience_gained,
            'created_at': attempt.created_at.isoformat(),
        })
    
    return JsonResponse({
        'success': True,
        'crafting_history': history
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def recipe_details(request, recipe_id):
    """Get detailed information about a specific recipe"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    recipe = get_object_or_404(CraftingRecipe, id=recipe_id, is_active=True)
    
    can_craft, reason = recipe.can_craft(character)
    success_rate = recipe.calculate_success_rate(character)
    
    # Get required materials with detailed info
    materials = []
    for material in recipe.get_required_materials():
        try:
            inventory_item = character.inventory.get(item_template__name=material.material_name)
            have_quantity = inventory_item.quantity
            item_template = inventory_item.item_template
        except InventoryItem.DoesNotExist:
            have_quantity = 0
            try:
                item_template = ItemTemplate.objects.get(name=material.material_name)
            except ItemTemplate.DoesNotExist:
                item_template = None
        
        material_info = {
            'name': material.material_name,
            'required': material.quantity_required,
            'have': have_quantity,
            'is_sufficient': have_quantity >= material.quantity_required,
            'is_consumed': material.is_consumed
        }
        
        if item_template:
            material_info['description'] = item_template.description
            material_info['value'] = item_template.base_value
        
        materials.append(material_info)
    
    # Get recent crafting attempts for this recipe
    recent_attempts = CraftingAttempt.objects.filter(
        character=character,
        recipe=recipe
    ).order_by('-created_at')[:5]
    
    attempts_info = []
    for attempt in recent_attempts:
        attempts_info.append({
            'status': attempt.get_status_display(),
            'success_rate_used': round(attempt.success_rate_used * 100, 1),
            'created_at': attempt.created_at.isoformat(),
        })
    
    return JsonResponse({
        'success': True,
        'recipe': {
            'id': str(recipe.id),
            'name': recipe.name,
            'description': recipe.description,
            'category': recipe.get_category_display(),
            'result_item': {
                'name': recipe.result_item.name,
                'description': recipe.result_item.description,
                'type': recipe.result_item.get_item_type_display(),
                'rarity': recipe.result_item.get_rarity_display(),
                'base_value': recipe.result_item.base_value,
                'damage': recipe.result_item.damage,
                'defense_bonus': recipe.result_item.defense_bonus,
                'heal_amount': recipe.result_item.heal_amount,
                'heal_percentage': recipe.result_item.heal_percentage,
            },
            'result_quantity': recipe.result_quantity,
            'required_level': recipe.required_level,
            'required_skill_level': recipe.required_skill_level,
            'craft_time_seconds': recipe.craft_time_seconds,
            'experience_reward': recipe.experience_reward,
            'base_success_rate': round(recipe.base_success_rate * 100, 1),
            'materials': materials,
            'can_craft': can_craft,
            'reason': reason if not can_craft else None,
            'current_success_rate': round(success_rate * 100, 1),
            'recent_attempts': attempts_info,
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def crafting_stats(request):
    """Get character's crafting statistics"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Count crafting attempts by status
    total_attempts = CraftingAttempt.objects.filter(character=character).count()
    successful_attempts = CraftingAttempt.objects.filter(character=character, status='success').count()
    failed_attempts = CraftingAttempt.objects.filter(character=character, status='failure').count()
    
    success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    # Count by category
    category_stats = {}
    for attempt in CraftingAttempt.objects.filter(character=character):
        category = attempt.recipe.category
        if category not in category_stats:
            category_stats[category] = {'attempts': 0, 'successes': 0}
        category_stats[category]['attempts'] += 1
        if attempt.status == 'success':
            category_stats[category]['successes'] += 1
    
    # Calculate category success rates
    for category, stats in category_stats.items():
        stats['success_rate'] = (stats['successes'] / stats['attempts'] * 100) if stats['attempts'] > 0 else 0
    
    # Get crafting skill info
    crafting_skill = get_or_create_crafting_skill(character)
    
    return JsonResponse({
        'success': True,
        'stats': {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': failed_attempts,
            'overall_success_rate': round(success_rate, 1),
            'crafting_skill_level': crafting_skill.level,
            'crafting_skill_experience': crafting_skill.experience,
            'category_breakdown': category_stats,
        }
    })


def get_crafting_skill_level(character):
    """Get character's crafting skill level"""
    try:
        return character.skills.get(name='Crafting').level
    except Skill.DoesNotExist:
        return 1


def get_or_create_crafting_skill(character):
    """Get or create crafting skill for character"""
    skill, created = Skill.objects.get_or_create(
        character=character,
        name='Crafting',
        defaults={
            'skill_type': 'crafting',
            'level': 1,
            'experience': 0
        }
    )
    return skill
