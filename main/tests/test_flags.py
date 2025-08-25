import math
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from main.models import Character, TerritoryFlag
from django.utils import timezone
from main.tasks import accrue_flag_income
from django.conf import settings


class FlagEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='bob', password='secret')
        self.client.login(username='bob', password='secret')
        gs = settings.GAME_SETTINGS
        self.char = Character.objects.create(
            user=self.user,
            name='Bob',
            lat=gs['DEFAULT_START_LAT'],
            lon=gs['DEFAULT_START_LON'],
            current_stamina=100,
            max_stamina=100,
            gold=1000,
        )

    def test_place_and_list_flags(self):
        # Place a flag at the character's location
        resp = self.client.post(
            reverse('api_flags_place'),
            data={'lat': self.char.lat, 'lon': self.char.lon, 'name': 'Home'},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data['success'])
        flag_id = data['flag']['id']
        self.assertEqual(data['flag']['name'], 'Home')

        # List nearby flags within 500m
        resp = self.client.get(reverse('api_flags_nearby'), {
            'lat': self.char.lat,
            'lon': self.char.lon,
            'radius_m': 500
        })
        self.assertEqual(resp.status_code, 200)
        lst = resp.json()
        self.assertTrue(lst['success'])
        self.assertTrue(any(f['id'] == flag_id for f in lst['flags']))

    def test_min_distance_enforced(self):
        # Place first flag
        resp1 = self.client.post(
            reverse('api_flags_place'),
            data={'lat': self.char.lat, 'lon': self.char.lon},
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 201)

        # Try to place another too close (within 50m)
        lon_delta_50m = 50 / (111000 * math.cos(math.radians(self.char.lat)))
        resp2 = self.client.post(
            reverse('api_flags_place'),
            data={'lat': self.char.lat, 'lon': self.char.lon + lon_delta_50m},
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 400)
        err = resp2.json()
        self.assertEqual(err.get('error'), 'too_close')

    def test_attack_to_capture_and_capture(self):
        # Place a flag owned by another user
        enemy = User.objects.create_user(username='enemy', password='secret')
        enemy_char = Character.objects.create(
            user=enemy,
            name='Enemy',
            lat=self.char.lat,
            lon=self.char.lon,
            gold=1000,
            current_stamina=100,
            max_stamina=100,
        )
        # Log back in as bob (attacker)
        self.client.login(username='bob', password='secret')

        # Place enemy flag slightly away to avoid min-distance vs none existing
        lon_delta_200m = 200 / (111000 * math.cos(math.radians(self.char.lat)))
        # enemy places (simulate via service by impersonating, or directly create)
        from main.services.flags import place_flag
        flag = place_flag(enemy, self.char.lat, self.char.lon + lon_delta_200m, 'EnemyFlag')

        # Move bob close to the flag and attack until capturable
        # Put bob at the flag position for interaction range checks
        self.char.lat = flag.lat
        self.char.lon = flag.lon
        self.char.save(update_fields=['lat', 'lon'])

        # Attack once with large damage to set hp to 0
        resp = self.client.post(
            reverse('api_flags_attack', args=[flag.id]),
            data={'lat': self.char.lat, 'lon': self.char.lon, 'damage': flag.hp_current},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['result']['hp_after'], 0)
        self.assertEqual(data['result']['status'], 'capturable')

        # Capture
        resp = self.client.post(
            reverse('api_flags_capture', args=[flag.id]),
            data={'lat': self.char.lat, 'lon': self.char.lon},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        cap = resp.json()
        self.assertTrue(cap['success'])
        self.assertTrue(cap['result']['captured'])

    def test_income_and_collect(self):
        # Place a flag
        resp = self.client.post(
            reverse('api_flags_place'),
            data={'lat': self.char.lat, 'lon': self.char.lon, 'name': 'Bank'},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 201)
        flag_id = resp.json()['flag']['id']

        # Simulate income accrual by calling task
        updated = accrue_flag_income()
        # We may or may not have accrued depending on minute boundary; ensure balance >= 0
        # Force another accrual by adjusting last_income_at back by 60 minutes
        from main.models import TerritoryFlag
        f = TerritoryFlag.objects.get(id=flag_id)
        from django.utils import timezone as tz
        f.last_income_at = tz.now() - tz.timedelta(minutes=60)
        f.save(update_fields=['last_income_at'])
        updated = accrue_flag_income()
        self.assertGreaterEqual(updated, 1)

        # Collect
        resp = self.client.post(reverse('api_flags_collect', args=[flag_id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['result']['collected'], 1)
