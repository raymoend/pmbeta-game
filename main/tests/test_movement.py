import math
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from main.models import Character
from django.conf import settings


class MovementEnforcementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret')
        self.client = Client()
        self.client.login(username='alice', password='secret')
        # Spawn character at default start
        gs = settings.GAME_SETTINGS
        self.char = Character.objects.create(
            user=self.user,
            name='Alice',
            lat=gs['DEFAULT_START_LAT'],
            lon=gs['DEFAULT_START_LON'],
            current_stamina=100,
            max_stamina=100,
        )

    def move(self, lat, lon):
        url = reverse('api_player_move')
        return self.client.post(url, data={'lat': lat, 'lon': lon}, content_type='application/json')

    def test_first_move_sets_center_and_allows_inside_radius(self):
        # First move: set center and allow within radius
        target_lat = self.char.lat
        target_lon = self.char.lon  # zero move
        resp = self.move(target_lat, target_lon)
        self.assertEqual(resp.status_code, 200)
        self.char.refresh_from_db()
        self.assertIsNotNone(self.char.move_center_lat)
        self.assertIsNotNone(self.char.move_center_lon)

        # Move ~100m east (within 800m)
        approx_lon_delta = 100 / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

    def test_reject_move_beyond_radius(self):
        # Set center by first move
        _ = self.move(self.char.lat, self.char.lon)
        self.char.refresh_from_db()

        # Try to move ~1000m east (beyond 800m)
        approx_lon_delta = 1000 / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get('error'), 'out_of_bounds')

    def test_not_enough_stamina(self):
        # Set center
        _ = self.move(self.char.lat, self.char.lon)
        self.char.refresh_from_db()
        # Drain stamina
        self.char.current_stamina = 0
        self.char.save(update_fields=['current_stamina'])

        # Try small move (would normally cost 1)
        approx_lon_delta = 10 / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get('error'), 'not_enough_stamina')

    def test_allow_move_exactly_at_boundary(self):
        # First move to set center
        _ = self.move(self.char.lat, self.char.lon)
        self.char.refresh_from_db()
        # Compute ~800m east minus small epsilon to avoid rounding beyond boundary
        radius_m = settings.GAME_SETTINGS.get('MOVEMENT_RANGE_M', 800)
        epsilon = 20  # 20 meters inside the boundary to avoid geodesic approximation issues
        approx_lon_delta = (radius_m - epsilon) / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('success'))

    def test_center_set_once_and_persists(self):
        # First move sets center
        _ = self.move(self.char.lat, self.char.lon)
        self.char.refresh_from_db()
        center1 = (self.char.move_center_lat, self.char.move_center_lon)
        # Second move within radius should NOT change center
        approx_lon_delta = 50 / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 200)
        self.char.refresh_from_db()
        center2 = (self.char.move_center_lat, self.char.move_center_lon)
        self.assertEqual(center1, center2)

    def test_minimum_stamina_cost_is_one(self):
        # Set center
        _ = self.move(self.char.lat, self.char.lon)
        self.char.refresh_from_db()
        before = self.char.current_stamina
        # Move a very small distance (~1 meter)
        approx_lon_delta = 1 / (111000 * math.cos(math.radians(self.char.lat)))
        resp = self.move(self.char.lat, self.char.lon + approx_lon_delta)
        self.assertEqual(resp.status_code, 200)
        self.char.refresh_from_db()
        self.assertEqual(before - 1, self.char.current_stamina)
