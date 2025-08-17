"""
PMBeta Combat Engine
Advanced turn-based PvE combat system for Player vs NPC battles
"""
import random
import math
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from .models import Player, NPC, CombatSession, CombatAction


class CombatEngine:
    """Main combat engine for managing PvE battles"""
    
    def __init__(self, combat_session=None):
        self.session_timeout = 600  # 10 minutes
        self.session = combat_session
    
    def can_start_combat(self, player, npc):
        """Check if combat can be initiated between player and NPC"""
        # Check if NPC is alive
        if not npc.is_alive:
            return False, "NPC is dead"
        
        # Check distance (must be within 50 meters)
        distance = player.distance_between(player.lat, player.lon, npc.lat, npc.lon)
        if distance > 50:
            return False, f"Too far away (need to be within 50m, currently {int(distance)}m)"
        
        # Check if player is already in combat
        existing_session = CombatSession.objects.filter(
            player=player,
            status__in=['player_turn', 'npc_turn', 'active']
        ).first()
        
        if existing_session:
            return False, "Already in combat with another opponent"
        
        # Check if NPC is already in combat
        existing_npc_session = CombatSession.objects.filter(
            npc=npc,
            status__in=['player_turn', 'npc_turn', 'active']
        ).first()
        
        if existing_npc_session:
            return False, "NPC is already fighting another player"
        
        # Check if player has enough HP
        if player.hp <= 0:
            return False, "Player has no health remaining"
        
        return True, "Can start combat"
    
    @transaction.atomic
    def start_combat(self, player, npc):
        """Initialize a new combat session"""
        can_start, reason = self.can_start_combat(player, npc)
        if not can_start:
            return None, reason
        
        # Create combat session
        session = CombatSession.objects.create(
            player=player,
            npc=npc,
            status='player_turn',
            turn_number=1,
            player_hp=player.hp,
            npc_hp=npc.hp,
            player_current_hp=player.hp,
            npc_current_hp=npc.hp,
            expires_at=timezone.now() + timedelta(seconds=self.session_timeout)
        )
        
        # Create initial combat action log entry
        CombatAction.objects.create(
            session=session,
            actor='system',
            action_type='attack',  # Will be used for system messages
            turn_number=0,
            target='npc',
            description=f"Combat begins! {player.user.username} vs {npc.name}"
        )
        
        return session, "Combat started successfully"
    
    def get_available_actions(self, session, actor='player'):
        """Get list of available actions for current turn"""
        if not session.is_active():
            return []
        
        base_actions = [
            {'type': 'attack', 'name': 'Attack', 'description': 'Basic attack'},
            {'type': 'defend', 'name': 'Defend', 'description': 'Reduce incoming damage'},
            {'type': 'flee', 'name': 'Flee', 'description': 'Attempt to escape combat'}
        ]
        
        # Add advanced actions based on player level
        if actor == 'player' and session.player.level >= 3:
            base_actions.extend([
                {'type': 'heavy_attack', 'name': 'Heavy Attack', 'description': 'Powerful but less accurate attack'},
                {'type': 'quick_attack', 'name': 'Quick Attack', 'description': 'Fast but weaker attack'}
            ])
        
        # Add special abilities at higher levels
        if actor == 'player' and session.player.level >= 5:
            base_actions.append({
                'type': 'special_ability', 
                'name': 'Power Strike', 
                'description': 'Enhanced attack with chance to stun'
            })
        
        return base_actions
    
    @transaction.atomic
    def execute_player_action(self, session, action_type, target='npc'):
        """Execute a player action during combat"""
        if not session.is_player_turn():
            return False, "Not player's turn"
        
        if not session.is_active():
            return False, "Combat session is not active"
        
        # Get combat stats
        player_stats = session.get_player_effective_stats()
        npc_stats = session.get_npc_effective_stats()
        
        # Create action record
        action = CombatAction.objects.create(
            session=session,
            actor='player',
            action_type=action_type,
            turn_number=session.turn_number,
            target=target
        )
        
        # Execute the specific action
        result = self._execute_action(session, action, player_stats, npc_stats, 'player')
        
        # Update action with results
        action.damage_dealt = result.get('damage', 0)
        action.healing_done = result.get('healing', 0)
        action.was_critical = result.get('is_critical', False)
        action.was_miss = result.get('is_miss', False)
        action.description = result.get('description', '')
        action.save()
        
        # Apply damage/effects
        if result.get('damage', 0) > 0:
            session.npc_current_hp -= result['damage']
            session.npc_current_hp = max(0, session.npc_current_hp)
            session.total_damage_to_npc += result['damage']
        
        # Check if NPC is defeated
        if session.npc_current_hp <= 0:
            return self._end_combat(session, 'player_victory')
        
        # Check for flee success
        if action_type == 'flee' and result.get('flee_success'):
            return self._end_combat(session, 'player_fled')
        
        # Switch to NPC turn
        session.status = 'npc_turn'
        session.save()
        
        # Execute NPC turn immediately
        return self._execute_npc_turn(session)
    
    def _execute_action(self, session, action, attacker_stats, defender_stats, actor):
        """Execute a specific combat action"""
        action_type = action.action_type
        result = {}
        
        if action_type in ['attack', 'heavy_attack', 'quick_attack']:
            # Calculate hit chance
            hit_chance = session.calculate_accuracy(attacker_stats, defender_stats, action_type)
            hit_roll = random.random()
            
            if hit_roll <= hit_chance:
                # Hit - calculate damage
                damage_result = session.calculate_damage(attacker_stats, defender_stats, action_type)
                result.update(damage_result)
                
                # Generate description
                attack_verb = {
                    'attack': 'attacks',
                    'heavy_attack': 'delivers a heavy blow to',
                    'quick_attack': 'strikes quickly at'
                }.get(action_type, 'attacks')
                
                actor_name = session.player.user.username if actor == 'player' else session.npc.name
                target_name = session.npc.name if actor == 'player' else session.player.user.username
                
                if damage_result['is_critical']:
                    result['description'] = f"{actor_name} {attack_verb} {target_name} for {damage_result['damage']} damage! CRITICAL HIT!"
                else:
                    result['description'] = f"{actor_name} {attack_verb} {target_name} for {damage_result['damage']} damage."
            else:
                # Miss
                result['is_miss'] = True
                actor_name = session.player.user.username if actor == 'player' else session.npc.name
                target_name = session.npc.name if actor == 'player' else session.player.user.username
                result['description'] = f"{actor_name} attacks {target_name} but misses!"
        
        elif action_type == 'defend':
            # Defending reduces incoming damage next turn and may heal slightly
            bonus_defense = attacker_stats['level'] * 2
            if actor == 'player':
                session.player_defense_bonus += bonus_defense
            else:
                session.npc_defense_bonus += bonus_defense
            
            # Small heal when defending
            heal_amount = max(1, attacker_stats['level'])
            result['healing'] = heal_amount
            
            actor_name = session.player.user.username if actor == 'player' else session.npc.name
            result['description'] = f"{actor_name} takes a defensive stance and recovers {heal_amount} HP."
        
        elif action_type == 'flee':
            # Flee chance based on player speed vs NPC speed
            player_speed = attacker_stats['speed'] if actor == 'player' else defender_stats['speed']
            npc_speed = defender_stats['speed'] if actor == 'player' else attacker_stats['speed']
            
            base_flee_chance = 0.3 + (player_speed - npc_speed) * 0.02
            flee_chance = max(0.1, min(0.8, base_flee_chance))
            
            if random.random() <= flee_chance:
                result['flee_success'] = True
                result['description'] = f"{session.player.user.username} successfully flees from combat!"
            else:
                result['flee_success'] = False
                result['description'] = f"{session.player.user.username} tries to flee but {session.npc.name} blocks the escape!"
        
        elif action_type == 'special_ability':
            # Power Strike - enhanced attack with stun chance
            if actor == 'player':
                damage_result = session.calculate_damage(attacker_stats, defender_stats, 'heavy_attack')
                damage_result['damage'] = int(damage_result['damage'] * 1.3)  # 30% bonus damage
                result.update(damage_result)
                
                # 25% chance to stun
                if random.random() <= 0.25:
                    session.apply_status_effect('npc', 'stunned', {'defense_bonus': -10}, 2)
                    result['description'] = f"{session.player.user.username} delivers a devastating Power Strike for {damage_result['damage']} damage! {session.npc.name} is stunned!"
                else:
                    result['description'] = f"{session.player.user.username} uses Power Strike for {damage_result['damage']} damage!"
        
        return result
    
    @transaction.atomic
    def _execute_npc_turn(self, session):
        """Execute NPC AI turn"""
        if not session.is_npc_turn():
            return True, "NPC turn completed"
        
        # Get combat stats
        player_stats = session.get_player_effective_stats()
        npc_stats = session.get_npc_effective_stats()
        
        # Simple AI logic
        action_type = self._choose_npc_action(session)
        
        # Create action record
        action = CombatAction.objects.create(
            session=session,
            actor='npc',
            action_type=action_type,
            turn_number=session.turn_number,
            target='player'
        )
        
        # Execute the action
        result = self._execute_action(session, action, npc_stats, player_stats, 'npc')
        
        # Update action with results
        action.damage_dealt = result.get('damage', 0)
        action.healing_done = result.get('healing', 0)
        action.was_critical = result.get('is_critical', False)
        action.was_miss = result.get('is_miss', False)
        action.description = result.get('description', '')
        action.save()
        
        # Apply damage/effects
        if result.get('damage', 0) > 0:
            session.player_current_hp -= result['damage']
            session.player_current_hp = max(0, session.player_current_hp)
            session.total_damage_to_player += result['damage']
        
        # Check if player is defeated
        if session.player_current_hp <= 0:
            return self._end_combat(session, 'npc_victory')
        
        # Process status effects at end of turn
        session.process_turn_end_effects()
        
        # Advance turn and switch to player
        session.turn_number += 1
        session.status = 'player_turn'
        
        # Reset defense bonuses (they only last one turn)
        session.player_defense_bonus = 0
        session.npc_defense_bonus = 0
        
        session.save()
        
        return True, "NPC turn completed"
    
    def _choose_npc_action(self, session):
        """Simple AI for choosing NPC actions"""
        # Basic AI logic based on NPC type and current situation
        npc = session.npc
        
        # Check HP percentage
        npc_hp_percent = session.npc_current_hp / session.npc_hp
        player_hp_percent = session.player_current_hp / session.player_hp
        
        # Aggressive NPCs attack more often
        aggression = npc.aggression
        
        # If NPC is low on health, consider defending
        if npc_hp_percent < 0.3 and random.random() < 0.3:
            return 'defend'
        
        # If player is low on health and NPC is aggressive, attack
        if player_hp_percent < 0.5 and aggression > 0.7:
            if npc.level >= 3 and random.random() < 0.4:
                return 'heavy_attack'
            return 'attack'
        
        # Default behavior based on aggression
        if random.random() < aggression:
            # Choose attack type
            if npc.level >= 3 and random.random() < 0.3:
                return random.choice(['heavy_attack', 'quick_attack'])
            return 'attack'
        else:
            # Less aggressive, might defend
            if random.random() < 0.2:
                return 'defend'
            return 'attack'
    
    @transaction.atomic
    def _end_combat(self, session, result):
        """End combat session and apply rewards/penalties"""
        session.status = result
        
        if result == 'player_victory':
            # Player wins - apply rewards
            rewards = session.npc.get_kill_rewards(session.player.level)
            
            session.experience_gained = rewards['experience']
            session.gold_gained = rewards['gold']
            session.reputation_gained = rewards['reputation']
            
            # Update player stats
            session.player.experience += rewards['experience']
            session.player.cash += rewards['gold']
            session.player.reputation += rewards['reputation']
            
            # Check for level up
            exp_for_next_level = session.player.level * 100
            if session.player.experience >= exp_for_next_level:
                session.player.level += 1
                session.player.hp += 10  # Gain HP on level up
                session.player.strength += 1
                session.player.defense += 1
                session.player.experience = 0  # Reset for next level
            
            session.player.save()
            
            # Kill the NPC
            session.npc.is_alive = False
            session.npc.last_death = timezone.now()
            session.npc.current_target = None
            session.npc.save()
            
        elif result == 'npc_victory':
            # NPC wins - apply penalties
            # Player loses some cash (10-25%)
            cash_lost = int(session.player.cash * random.uniform(0.1, 0.25))
            session.player.cash = max(0, session.player.cash - cash_lost)
            
            # Player loses some HP (but not killed)
            session.player.hp = max(1, session.player_current_hp)
            session.player.save()
            
        elif result == 'player_fled':
            # Player fled - minor penalties
            # Small reputation loss
            session.player.reputation = max(0, session.player.reputation - 1)
            session.player.save()
        
        session.save()
        
        # Create final action log
        CombatAction.objects.create(
            session=session,
            actor='system',
            action_type='attack',  # System message
            turn_number=session.turn_number,
            target='npc',
            description=self._get_combat_result_message(session, result)
        )
        
        return True, f"Combat ended: {result}"
    
    def _get_combat_result_message(self, session, result):
        """Generate combat result message"""
        if result == 'player_victory':
            return (f"{session.player.user.username} defeats {session.npc.name}! "
                   f"Gained {session.experience_gained} XP, ${session.gold_gained}, "
                   f"and {session.reputation_gained} reputation.")
        
        elif result == 'npc_victory':
            cash_lost = int(session.player.cash * 0.15)  # Estimate
            return (f"{session.npc.name} defeats {session.player.user.username}! "
                   f"Lost approximately ${cash_lost} and some health.")
        
        elif result == 'player_fled':
            return f"{session.player.user.username} fled from {session.npc.name}."
        
        return "Combat ended."
    
    def get_combat_log(self, session, limit=20):
        """Get combat action log for display"""
        actions = session.actions.order_by('turn_number', 'created_at')[:limit]
        
        log_entries = []
        for action in actions:
            entry = {
                'turn': action.turn_number,
                'actor': action.actor,
                'action': action.action_type,
                'description': action.description,
                'damage': action.damage_dealt,
                'healing': action.healing_done,
                'critical': action.was_critical,
                'miss': action.was_miss,
                'timestamp': action.created_at
            }
            log_entries.append(entry)
        
        return log_entries
    
    def cleanup_expired_sessions(self):
        """Clean up expired combat sessions"""
        expired_sessions = CombatSession.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=['player_turn', 'npc_turn', 'active']
        )
        
        count = 0
        for session in expired_sessions:
            session.status = 'expired'
            session.save()
            count += 1
        
        return count
    
    def get_combat_state(self):
        """Get current combat state for API responses"""
        if not self.session:
            return None
        
        session = self.session
        
        # Get available actions for player
        available_actions = self.get_available_actions(session)
        
        # Get recent combat log
        combat_log = self.get_combat_log(session, limit=10)
        
        return {
            'session_id': str(session.id),
            'status': session.status,
            'turn': session.turn_number,
            'player': {
                'name': session.player.user.username,
                'level': session.player.level,
                'hp': session.player_current_hp,
                'max_hp': session.player_hp,
                'stats': session.get_player_effective_stats()
            },
            'npc': {
                'name': session.npc.name,
                'level': session.npc.level,
                'hp': session.npc_current_hp,
                'max_hp': session.npc_hp,
                'stats': session.get_npc_effective_stats()
            },
            'available_actions': available_actions,
            'combat_log': combat_log,
            'is_active': session.is_active()
        }
    
    def player_attack(self, weapon=None):
        """Execute player attack action"""
        if not self.session:
            return {'success': False, 'message': 'No active combat session'}
        
        action_type = 'attack'
        if weapon:
            # Modify attack based on weapon type
            if weapon.damage > 50:
                action_type = 'heavy_attack'
            elif weapon.accuracy > 80:
                action_type = 'quick_attack'
        
        success, message = self.execute_player_action(self.session, action_type)
        return {
            'success': success,
            'message': message,
            'weapon_used': weapon.name if weapon else 'Bare hands'
        }
    
    def player_defend(self):
        """Execute player defend action"""
        if not self.session:
            return {'success': False, 'message': 'No active combat session'}
        
        success, message = self.execute_player_action(self.session, 'defend')
        return {
            'success': success,
            'message': message
        }
    
    def use_item(self, item):
        """Execute use item action (healing potion, buff, etc.)"""
        if not self.session:
            return {'success': False, 'message': 'No active combat session'}
        
        # Simple item usage - assume it's a healing item for now
        # In a full implementation, you'd check item type and apply appropriate effects
        healing = 20 + item.id % 10  # Simple healing calculation
        
        self.session.player_current_hp = min(
            self.session.player_hp, 
            self.session.player_current_hp + healing
        )
        self.session.save()
        
        # Consume the item
        item.delete()
        
        return {
            'success': True,
            'message': f'Used {item.name} and recovered {healing} HP',
            'healing': healing
        }
    
    def attempt_flee(self):
        """Execute flee attempt"""
        if not self.session:
            return {'success': False, 'message': 'No active combat session'}
        
        success, message = self.execute_player_action(self.session, 'flee')
        return {
            'success': success,
            'message': message
        }


# Global combat engine instance
combat_engine = CombatEngine()
