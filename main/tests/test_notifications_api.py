from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from main.models import Character, GameEvent

class NotificationsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw12345')
        self.char = Character.objects.create(
            user=self.user,
            name='Alice',
            lat=41.0,
            lon=-81.0,
        )
        self.char.apply_class_base_stats()
        self.char.save()

    def test_list_and_mark_read(self):
        # Create some events
        ev1 = GameEvent.objects.create(character=self.char, event_type='combat', title='Hit', message='You hit a wolf', data={})
        ev2 = GameEvent.objects.create(character=self.char, event_type='loot_dropped', title='Loot', message='You found gold', data={})
        ev3 = GameEvent.objects.create(character=self.char, event_type='trade', title='Trade', message='Trade completed', data={})

        self.assertTrue(self.client.login(username='alice', password='pw12345'))

        # List
        res = self.client.get('/api/rpg/events/?page=1&page_size=50')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data.get('events', [])), 3)
        self.assertEqual(data.get('unread'), 3)

        # Mark one as read
        res2 = self.client.post('/api/rpg/events/mark-read/', data={'ids': [str(ev1.id)]}, content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertTrue(d2.get('success'))
        self.assertEqual(d2.get('unread'), 2)

        # Mark all
        res3 = self.client.post('/api/rpg/events/mark-all-read/', data={}, content_type='application/json')
        self.assertEqual(res3.status_code, 200)
        d3 = res3.json()
        self.assertTrue(d3.get('success'))
        self.assertEqual(d3.get('unread'), 0)

