import json
import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from main.models import Character, TerritoryFlag


@pytest.mark.django_db
class TestFlagsAPI:
    def setup_user(self, client, lat=41.0, lon=-81.0, gold=1000):
        user = User.objects.create_user(username='tester', password='pass')
        Character.objects.create(user=user, name='Tester', lat=lat, lon=lon, gold=gold)
        assert client.login(username='tester', password='pass')
        return user

    def test_flags_near_requires_auth(self, client):
        resp = client.get('/api/flags/near/?lat=41&lon=-81&radius_m=2000')
        assert resp.status_code in (302, 403)  # redirected to login or forbidden

    def test_place_and_list_flag(self, client):
        self.setup_user(client)
        # Initially empty
        resp = client.get('/api/flags/near/?lat=41&lon=-81&radius_m=2000')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['data']['flags'] == []

        # Place a flag
        body = {"lat": 41.0005, "lon": -81.0005, "name": "My Flag"}
        resp = client.post('/api/flags/place/', data=json.dumps(body), content_type='application/json')
        assert resp.status_code in (200, 201)
        placed = resp.json()
        assert placed['ok'] is True
        fid = placed['data']['id']

        # Now list should include it
        resp = client.get('/api/flags/near/?lat=41&lon=-81&radius_m=2000')
        assert resp.status_code == 200
        flags = resp.json()['data']['flags']
        assert any(f['id'] == fid for f in flags)

    def test_cannot_place_too_close(self, client):
        self.setup_user(client)
        TerritoryFlag.objects.create(owner=User.objects.get(username='tester'), name='A', lat=41.0, lon=-81.0, level=1, hp_current=100, hp_max=100)
        body = {"lat": 41.0001, "lon": -81.0001}
        resp = client.post('/api/flags/place/', data=json.dumps(body), content_type='application/json')
        assert resp.status_code == 400
        err = resp.json()['error']
        assert 'min' in err.lower()

    def test_attack_and_capture_flow(self, client):
        self.setup_user(client)
        # Create enemy user and flag
        enemy = User.objects.create_user(username='enemy', password='pass')
        Character.objects.create(user=enemy, name='Enemy', lat=41.001, lon=-81.001, gold=1000)
        f = TerritoryFlag.objects.create(owner=enemy, name='EnemyFlag', lat=41.001, lon=-81.001, level=1, hp_current=100, hp_max=100)

        # Move our character near enemy flag
        c = Character.objects.get(user__username='tester')
        c.lat, c.lon = 41.001, -81.001
        c.save(update_fields=['lat', 'lon'])

        # Attack
        resp = client.post(f'/api/flags/{f.id}/attack/', data={'lat': c.lat, 'lon': c.lon})
        assert resp.status_code == 200
        res = resp.json()
        assert res['ok'] is True

        # Simulate hp to zero and capturable
        f.refresh_from_db()
        f.hp_current = 0
        f.status = 'capturable'
        f.capture_window_ends_at = timezone.now() + timezone.timedelta(minutes=5)
        f.save(update_fields=['hp_current', 'status', 'capture_window_ends_at'])

        # Capture
        resp = client.post(f'/api/flags/{f.id}/capture/', data={'lat': c.lat, 'lon': c.lon})
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        f.refresh_from_db()
        assert f.owner.username == 'tester'

    def test_collect_revenue_owner_only(self, client):
        self.setup_user(client)
        owner = User.objects.get(username='tester')
        f = TerritoryFlag.objects.create(owner=owner, name='Cash', lat=41.0, lon=-81.0, level=1, hp_current=100, hp_max=100, uncollected_balance=50)
        resp = client.post(f'/api/flags/{f.id}/collect/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        f.refresh_from_db()
        assert f.uncollected_balance == 0
