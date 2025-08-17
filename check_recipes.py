#!/usr/bin/env python3
import os
import django

# Setup Django environment first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmbeta.settings')
django.setup()

from main.models import CraftingRecipe, CraftingRecipeMaterial

recipes = CraftingRecipe.objects.filter(is_active=True)[:5]
print("Available crafting recipes and their materials:")
for recipe in recipes:
    materials = recipe.required_materials.all()
    material_list = [f"{m.material_name} ({m.quantity_required})" for m in materials]
    print(f"- {recipe.name}: {material_list}")
