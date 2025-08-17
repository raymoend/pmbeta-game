"""
Advanced Game Logic for PMBeta
Mafia-themed game mechanics inspired by P2K architecture
"""
import random
import math
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from .models import (
    Player, Flag, NPC, ResourceNode, Combat, NPCCombat, 
    FlagAttack, ResourceHarvest, ActivityExecution,
    CriminalActivity, Family, FamilyMembership, Territory
)


class CombatEngine:
    """
    Combat system for player vs NPC and player vs player
    """
    
    @staticmethod
    def calculate_combat_result(attacker_stats, defender_stats):
        """Calculate combat result based on stats"""
        attacker_power = (
            attacker_stats['strength'] + 
            attacker_stats['speed'] * 0.5 + 
            attacker_stats['accuracy'] * 0.3
        )
        
        defender_power = (
            defender_stats['defense'] + 
            defender_stats['speed'] * 0.3 +
            (defender_stats.get('hp', 100) / 100) * 10  # HP bonus
        )
        
        # Add randomness (±20%)
        attacker_roll = attacker_power * random.uniform(0.8, 1.2)
        defender_roll = defender_power * random.uniform(0.8, 1.2)
        
        # Calculate damage
        if attacker_roll > defender_roll:
            damage = int((attacker_roll - defender_roll) * random.uniform(0.5, 1.5))
            return {'winner': 'attacker', 'damage': damage}
        else:
            damage = int((defender_roll - attacker_roll) * random.uniform(0.3, 1.0))
            return {'winner': 'defender', 'damage': damage}
    
    @staticmethod
    def player_vs_npc_combat(player, npc):
        """Execute combat between player and NPC"""
        if not npc.is_alive:
            return {'success': False, 'message': 'NPC is already dead'}
        
        # Check distance
        distance = player.distance_between(player.lat, player.lon, npc.lat, npc.lon)
        if distance > 50:  # 50m combat range
            return {'success': False, 'message': 'Too far from target'}
        
        player_stats = {
            'strength': player.strength,
            'defense': player.defense,
            'speed': player.speed,
            'accuracy': player.accuracy,
            'hp': player.hp
        }
        
        npc_stats = {
            'strength': npc.strength,
            'defense': npc.defense,
            'speed': npc.speed,
            'accuracy': 10,  # Default NPC accuracy
            'hp': npc.hp
        }
        
        # Create combat record
        combat = NPCCombat.objects.create(
            player=player,
            npc=npc,
            status='initiated'
        )
        
        # Multiple combat rounds
        rounds = random.randint(1, 3)
        total_player_damage = 0
        total_npc_damage = 0
        
        for round_num in range(rounds):
            result = CombatEngine.calculate_combat_result(player_stats, npc_stats)
            
            if result['winner'] == 'attacker':
                npc_stats['hp'] -= result['damage']
                total_player_damage += result['damage']
            else:
                player_stats['hp'] -= result['damage']
                total_npc_damage += result['damage']
            
            # Check if either is defeated
            if npc_stats['hp'] <= 0 or player_stats['hp'] <= 0:
                break
        
        # Determine final result
        if npc_stats['hp'] <= 0:
            # Player wins
            npc.is_alive = False
            npc.hp = 0
            npc.last_death = timezone.now()
            npc.save()
            
            # Calculate rewards
            rewards = npc.get_kill_rewards(player.level)
            
            # Update player
            player.experience += rewards['experience']
            player.cash += rewards['gold']
            player.reputation += rewards['reputation']
            player.hp = max(1, player_stats['hp'])  # Don't let player die
            
            # Level up check
            if player.experience >= (player.level * 100):
                player.level += 1
                player.hp = 100  # Full heal on level up
                player.experience = 0
            
            player.save()
            
            # Update combat record
            combat.status = 'player_won'
            combat.player_damage_dealt = total_player_damage
            combat.npc_damage_dealt = total_npc_damage
            combat.experience_gained = rewards['experience']
            combat.gold_gained = rewards['gold']
            combat.reputation_gained = rewards['reputation']
            combat.completed_at = timezone.now()
            combat.save()
            
            return {
                'success': True,
                'victory': True,
                'message': f"Defeated {npc.name}!",
                'rewards': rewards,
                'player_damage_taken': total_npc_damage
            }
        
        elif player_stats['hp'] <= 0:
            # Player loses (but doesn't die permanently)
            player.hp = 1  # Leave at 1 HP
            player.save()
            
            combat.status = 'npc_won'
            combat.player_damage_dealt = total_player_damage
            combat.npc_damage_dealt = total_npc_damage
            combat.completed_at = timezone.now()
            combat.save()
            
            return {
                'success': True,
                'victory': False,
                'message': f"Defeated by {npc.name}! You barely escaped.",
                'player_damage_taken': total_npc_damage
            }
        
        else:
            # Draw/interrupted
            player.hp = max(1, player_stats['hp'])
            npc.hp = max(1, npc_stats['hp'])
            player.save()
            npc.save()
            
            combat.status = 'fled'
            combat.player_damage_dealt = total_player_damage
            combat.npc_damage_dealt = total_npc_damage
            combat.completed_at = timezone.now()
            combat.save()
            
            return {
                'success': True,
                'victory': False,
                'message': "Combat ended in a draw. Both parties fled.",
                'player_damage_taken': total_npc_damage
            }


class ResourceManager:
    """
    Resource harvesting and management
    """
    
    @staticmethod
    def harvest_resource(player, resource):
        """Player harvests a resource node"""
        if not resource.can_harvest():
            return {'success': False, 'message': 'Resource not ready for harvest'}
        
        # Check distance
        distance = player.distance_between(player.lat, player.lon, resource.lat, resource.lon)
        if distance > 50:  # 50m harvest range
            return {'success': False, 'message': 'Too far from resource'}
        
        # Create harvest record
        harvest = ResourceHarvest.objects.create(
            player=player,
            resource=resource,
            status='in_progress',
            duration_seconds=30  # 30 second harvest time
        )
        
        # Calculate rewards
        rewards = resource.get_harvest_rewards(player.level)
        
        # Update resource
        resource.last_harvested = timezone.now()
        resource.harvest_count += 1
        resource.hp -= random.randint(10, 30)  # Damage resource
        
        if resource.hp <= 0:
            resource.is_depleted = True
            resource.hp = 0
        
        resource.save()
        
        # Update player
        player.experience += rewards['experience']
        player.cash += rewards['gold']
        player.save()
        
        # Update harvest record
        harvest.status = 'completed'
        harvest.experience_gained = rewards['experience']
        harvest.gold_gained = rewards['gold']
        harvest.resources_gained = rewards['resources']
        harvest.resource_type = rewards['resource_type']
        harvest.completed_at = timezone.now()
        harvest.save()
        
        return {
            'success': True,
            'message': f"Harvested {resource.get_resource_type_display()}!",
            'rewards': rewards
        }


class FlagManager:
    """
    Flag placement, attacks, and territory control
    """
    
    @staticmethod
    def place_flag(player, lat, lon, name, flag_type='territory'):
        """Place a new flag"""
        # Check cost
        cost = 50000
        if player.cash < cost:
            return {'success': False, 'message': 'Not enough cash'}
        
        # Check distance from other flags (200m minimum)
        nearby_flags = Flag.objects.filter(
            lat__gte=lat - 0.002,  # ~200m
            lat__lte=lat + 0.002,
            lon__gte=lon - 0.002,
            lon__lte=lon + 0.002
        )
        
        for flag in nearby_flags:
            distance = player.distance_between(lat, lon, flag.lat, flag.lon)
            if distance < 200:
                return {'success': False, 'message': 'Too close to another flag'}
        
        # Create flag
        flag = Flag.objects.create(
            name=name,
            flag_type=flag_type,
            lat=lat,
            lon=lon,
            owner=player,
            level=1,
            hp=1000,
            max_hp=1000,
            defense_rating=50,
            income_per_hour=500,
            invulnerable_until=timezone.now() + timedelta(hours=24)  # 24h protection
        )
        
        # Deduct cost
        player.cash -= cost
        player.save()
        
        # Spawn guardian NPCs
        npcs_spawned = flag.spawn_npcs(3)
        
        return {
            'success': True,
            'message': f"Flag '{name}' placed successfully!",
            'flag': flag,
            'npcs_spawned': len(npcs_spawned)
        }
    
    @staticmethod
    def attack_flag(attacker, flag):
        """Attack a flag"""
        can_attack, reason = flag.can_be_attacked_by(attacker)
        if not can_attack:
            return {'success': False, 'message': reason}
        
        # Create attack record
        attack = FlagAttack.objects.create(
            flag=flag,
            attacker=attacker,
            status='in_progress',
            attack_strength=attacker.strength + attacker.accuracy + (attacker.level * 5)
        )
        
        # Calculate success chance
        success_chance = attack.calculate_success_chance()
        
        # Determine result
        if random.random() < success_chance:
            # Attack successful
            damage = random.randint(100, 300)
            flag.hp -= damage
            
            if flag.hp <= 0:
                # Flag captured
                old_owner = flag.owner
                flag.owner = attacker
                flag.hp = flag.max_hp // 2  # Restore to half HP
                flag.invulnerable_until = timezone.now() + timedelta(hours=12)  # 12h protection
                flag.save()
                
                # Rewards
                money_gained = random.randint(10000, 50000)
                reputation_gained = random.randint(10, 30)
                
                attacker.cash += money_gained
                attacker.reputation += reputation_gained
                attacker.save()
                
                attack.status = 'successful'
                attack.damage_dealt = damage
                attack.money_gained = money_gained
                attack.reputation_gained = reputation_gained
                attack.completed_at = timezone.now()
                attack.save()
                
                return {
                    'success': True,
                    'attack_successful': True,
                    'flag_captured': True,
                    'message': f"Captured {flag.name}!",
                    'money_gained': money_gained,
                    'reputation_gained': reputation_gained
                }
            else:
                # Damage dealt but flag not captured
                flag.save()
                
                money_gained = random.randint(1000, 5000)
                reputation_gained = random.randint(1, 5)
                
                attacker.cash += money_gained
                attacker.reputation += reputation_gained
                attacker.save()
                
                attack.status = 'successful'
                attack.damage_dealt = damage
                attack.money_gained = money_gained
                attack.reputation_gained = reputation_gained
                attack.completed_at = timezone.now()
                attack.save()
                
                return {
                    'success': True,
                    'attack_successful': True,
                    'flag_captured': False,
                    'message': f"Damaged {flag.name} for {damage} HP!",
                    'damage_dealt': damage,
                    'flag_hp_remaining': flag.hp,
                    'money_gained': money_gained,
                    'reputation_gained': reputation_gained
                }
        else:
            # Attack failed
            attack.status = 'failed'
            attack.completed_at = timezone.now()
            attack.save()
            
            return {
                'success': True,
                'attack_successful': False,
                'message': f"Attack on {flag.name} failed!"
            }


class CriminalActivityManager:
    """
    Criminal activities and job system
    """
    
    @staticmethod
    def start_criminal_activity(player, activity):
        """Player starts a criminal activity"""
        # Check requirements
        if player.level < activity.min_level:
            return {'success': False, 'message': 'Level too low'}
        
        if player.reputation < activity.min_reputation:
            return {'success': False, 'message': 'Not enough reputation'}
        
        if player.cash < activity.required_cash:
            return {'success': False, 'message': 'Not enough cash'}
        
        # Check distance
        distance = player.distance_between(player.lat, player.lon, activity.lat, activity.lon)
        if distance > 100:  # 100m range
            return {'success': False, 'message': 'Too far from activity location'}
        
        # Check cooldown
        recent_execution = ActivityExecution.objects.filter(
            player=player,
            activity=activity,
            completed_at__gte=timezone.now() - timedelta(hours=activity.cooldown_hours)
        ).first()
        
        if recent_execution:
            return {'success': False, 'message': 'Activity on cooldown'}
        
        # Create execution
        execution = ActivityExecution.objects.create(
            player=player,
            activity=activity,
            status='in_progress'
        )
        
        # Deduct upfront cost
        player.cash -= activity.required_cash
        player.save()
        
        # Simulate activity (for demo - in real game this would be time-based)
        success_chance = activity.success_chance
        
        # Modify chance based on player stats
        if player.level > activity.min_level:
            success_chance += (player.level - activity.min_level) * 0.05
        
        if player.reputation > activity.min_reputation:
            success_chance += (player.reputation - activity.min_reputation) * 0.001
        
        success_chance = min(0.95, max(0.05, success_chance))  # Clamp to 5%-95%
        
        if random.random() < success_chance:
            # Success
            payout = random.randint(activity.min_payout, activity.max_payout)
            rep_gain = random.randint(1, 5)
            heat_gain = activity.heat_gain * random.uniform(0.5, 1.5)
            
            player.cash += payout
            player.reputation += rep_gain
            player.heat_level = min(100, player.heat_level + heat_gain)
            player.save()
            
            execution.status = 'successful'
            execution.payout = payout
            execution.reputation_gained = rep_gain
            execution.heat_gained = heat_gain
            execution.completed_at = timezone.now()
            execution.save()
            
            return {
                'success': True,
                'activity_successful': True,
                'message': f"Successfully completed {activity.name}!",
                'payout': payout,
                'reputation_gained': rep_gain,
                'heat_gained': heat_gain
            }
        else:
            # Failure
            heat_gain = activity.heat_gain * random.uniform(1.0, 2.0)  # More heat on failure
            
            player.heat_level = min(100, player.heat_level + heat_gain)
            player.save()
            
            execution.status = 'failed'
            execution.heat_gained = heat_gain
            execution.completed_at = timezone.now()
            execution.save()
            
            # Chance of getting busted
            if random.random() < 0.2:  # 20% chance
                execution.status = 'busted'
                execution.save()
                
                return {
                    'success': True,
                    'activity_successful': False,
                    'busted': True,
                    'message': f"Got busted attempting {activity.name}!",
                    'heat_gained': heat_gain
                }
            
            return {
                'success': True,
                'activity_successful': False,
                'message': f"Failed to complete {activity.name}.",
                'heat_gained': heat_gain
            }


class FamilyManager:
    """
    Family/clan system management
    """
    
    @staticmethod
    def create_family(player, family_name, description=""):
        """Create a new mafia family"""
        cost = 100000  # $100k to create family
        
        if player.cash < cost:
            return {'success': False, 'message': 'Not enough cash to create family'}
        
        if Family.objects.filter(name=family_name).exists():
            return {'success': False, 'message': 'Family name already taken'}
        
        if hasattr(player, 'family_membership') and player.family_membership:
            return {'success': False, 'message': 'Already in a family'}
        
        with transaction.atomic():
            # Create family
            family = Family.objects.create(
                name=family_name,
                description=description,
                boss=player,
                treasury=0,
                reputation=0
            )
            
            # Create membership for creator as boss
            FamilyMembership.objects.create(
                family=family,
                player=player,
                role='boss'
            )
            
            # Deduct cost
            player.cash -= cost
            player.save()
        
        return {
            'success': True,
            'message': f"Family '{family_name}' created successfully!",
            'family': family
        }
    
    @staticmethod
    def join_family(player, family):
        """Player joins a family"""
        if not family.can_recruit():
            return {'success': False, 'message': 'Family not recruiting'}
        
        if hasattr(player, 'family_membership') and player.family_membership:
            return {'success': False, 'message': 'Already in a family'}
        
        # Create membership
        membership = FamilyMembership.objects.create(
            family=family,
            player=player,
            role='associate'
        )
        
        return {
            'success': True,
            'message': f"Joined {family.name} as an Associate!",
            'membership': membership
        }


class WorldEventManager:
    """
    Manage world events and periodic tasks
    """
    
    @staticmethod
    def respawn_dead_npcs():
        """Respawn NPCs that are ready to respawn"""
        dead_npcs = NPC.objects.filter(is_alive=False)
        respawned_count = 0
        
        for npc in dead_npcs:
            if npc.can_respawn():
                npc.is_alive = True
                npc.hp = npc.max_hp
                npc.last_death = None
                npc.current_target = None
                npc.save()
                respawned_count += 1
        
        return respawned_count
    
    @staticmethod
    def regenerate_resources():
        """Regenerate depleted resources"""
        depleted_resources = ResourceNode.objects.filter(is_depleted=True)
        regenerated_count = 0
        
        for resource in depleted_resources:
            if resource.can_harvest():  # This checks respawn timer
                resource.is_depleted = False
                resource.hp = resource.max_hp
                resource.last_harvested = None
                resource.save()
                regenerated_count += 1
        
        return regenerated_count
    
    @staticmethod
    def pay_flag_income():
        """Pay hourly income to flag owners"""
        active_flags = Flag.objects.filter(status='active', hp__gt=0)
        total_income = 0
        
        for flag in active_flags:
            income = flag.get_hourly_income()
            flag.owner.cash += income
            flag.owner.save()
            total_income += income
        
        return len(active_flags), total_income
