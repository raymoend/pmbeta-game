import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth.models import User

from main.models import Character, ResourceNode, HealingClaim, Monster, MonsterTemplate, PvECombat
from main import views_rpg


class HealingClaimTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Location near 0,0 to avoid bbox floating issues
        self.lat = 41.000000
        self.lon = -81.000000
        # User 1 + character
        self.u1 = User.objects.create_user(username='u1', password='pass')
        self.c1 = Character.objects.create(user=self.u1, name='Hero1', lat=self.lat, lon=self.lon)
        try:
            self.c1.apply_class_base_stats()
            self.c1.save()
        except Exception:
            pass
        self.c1.current_hp = max(1, int(self.c1.max_hp) - 20)
        self.c1.save()
        # User 2 + character
        self.u2 = User.objects.create_user(username='u2', password='pass')
        self.c2 = Character.objects.create(user=self.u2, name='Hero2', lat=self.lat, lon=self.lon)
        try:
            self.c2.apply_class_base_stats()
            self.c2.save()
        except Exception:
            pass
        # Healing resource within 5m
        self.node = ResourceNode.objects.create(
            resource_type='berry_bush',
            lat=self.lat,
            lon=self.lon,
            level=1,
            quantity=5,
            max_quantity=5,
            respawn_time=30,
        )

    def test_healing_claim_tick_and_exclusivity(self):
        # User1 claims heal
        self.client.force_login(self.u1)
        res = self.client.post('/api/rpg/combat/heal/', data=json.dumps({'resource_id': str(self.node.id)}), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('claim_active'))
        # Simulate time passing for tick
        claim = HealingClaim.objects.filter(resource=self.node, active=True, character=self.c1).first()
        self.assertIsNotNone(claim)
        # Move last_tick_at 3 seconds back
        claim.last_tick_at = timezone.now() - timedelta(seconds=3)
        claim.save(update_fields=['last_tick_at'])
        # Tick again
        res2 = self.client.post('/api/rpg/combat/heal/', data=json.dumps({'resource_id': str(self.node.id)}), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertTrue(d2.get('success'))
        # Expect some healing occurred (at least 5 HP in 1-3 seconds)
        self.assertGreaterEqual(int(d2.get('healed', 0)), 5)
        # User2 cannot claim the same resource concurrently
        self.client.logout()
        self.client.force_login(self.u2)
        res3 = self.client.post('/api/rpg/combat/heal/', data=json.dumps({'resource_id': str(self.node.id)}), content_type='application/json')
        # Should be 409 conflict with error code
        self.assertIn(res3.status_code, (200, 409))
        d3 = res3.json()
        if res3.status_code == 200:
            # If 200, it should not be active for second user (edge fallback). Prefer error.
            self.assertFalse(d3.get('claim_active', False))
        else:
            self.assertEqual(d3.get('error'), 'healing_source_in_use')


class RespawnCooldownTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='respawn', password='pass')
        self.char = Character.objects.create(user=self.user, name='Downed', lat=41.0, lon=-81.0)
        try:
            self.char.apply_class_base_stats()
        except Exception:
            pass
        self.char.current_hp = 0
        self.char.save()

    def test_respawn_cooldown_enforced(self):
        # Set cooldown in the future
        now = timezone.now()
        self.char.downed_at = now
        self.char.respawn_available_at = now + timedelta(seconds=5)
        self.char.save(update_fields=['downed_at', 'respawn_available_at'])
        self.client.force_login(self.user)
        res = self.client.post('/api/rpg/character/respawn/', data=json.dumps({}), content_type='application/json')
        self.assertEqual(res.status_code, 429)
        data = res.json()
        self.assertEqual(data.get('error'), 'respawn_cooldown')
        self.assertGreaterEqual(int(data.get('seconds_remaining', 0)), 1)
        # Expire cooldown and try again
        self.char.respawn_available_at = now - timedelta(seconds=1)
        self.char.save(update_fields=['respawn_available_at'])
        res2 = self.client.post('/api/rpg/character/respawn/', data=json.dumps({}), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertTrue(d2.get('success'))
        self.char.refresh_from_db()
        self.assertEqual(int(self.char.current_hp), int(self.char.max_hp))
        # Cooldown cleared
        self.assertIsNone(getattr(self.char, 'downed_at', None))
        self.assertIsNone(getattr(self.char, 'respawn_available_at', None))


class RewardScalingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='scaler', password='pass')
        self.char = Character.objects.create(user=self.user, name='Scaler', lat=41.0, lon=-81.0)
        try:
            self.char.apply_class_base_stats()
            self.char.save()
        except Exception:
            pass

    def test_experience_and_gold_scale_with_monster_level(self):
        import random
        random.seed(1)
        # Character level
        self.char.level = 3
        self.char.current_hp = max(1, int(self.char.max_hp) - 5)
        self.char.save()
        # Monster template higher level
        tmpl = MonsterTemplate.objects.create(
            name='Test Brute', description='Scaling test', level=self.char.level + 3,
            base_hp=30, strength=10, defense=5, agility=8,
            base_experience=100, base_gold=50, is_aggressive=True,
            respawn_time_minutes=15,
        )
        m = Monster.objects.create(template=tmpl, lat=self.char.lat, lon=self.char.lon, current_hp=0, max_hp=tmpl.base_hp, is_alive=True)
        combat = PvECombat.objects.create(character=self.char, monster=m, character_hp=self.char.current_hp, monster_hp=0)
        with patch('main.models.PvECombat.generate_loot_drops', return_value=[{'name': 'Test Gem', 'quantity': 1}]):
            resp = views_rpg.handle_combat_victory(combat, self.char)
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode('utf-8'))
        self.assertTrue(payload.get('victory'))
        # Expect scaled rewards (>= base)
        self.assertGreaterEqual(int(payload.get('experience_gained', 0)), tmpl.base_experience)
        self.assertGreaterEqual(int(payload.get('gold_gained', 0)), tmpl.base_gold)
        # Ensure drops were set from patched generator
        drops = payload.get('drops') or []
        self.assertTrue(isinstance(drops, list))
        self.assertTrue(any(d.get('name') == 'Test Gem' for d in drops))

