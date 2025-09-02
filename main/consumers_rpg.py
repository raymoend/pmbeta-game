"""
WebSocket consumers for Parallel Kingdom-style RPG game
Handles real-time geolocation, simplified combat, trading, and chat
"""
import json
import logging
import asyncio
from django.utils import timezone
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


def _grid_factor() -> int:
    """Grid factor for location groups. 20000 ≈ ~50m cells; 1000 ≈ ~1km cells."""
    try:
        return int(getattr(settings, 'WS_LOCATION_GRID_FACTOR', 20000))
    except Exception:
        return 20000


class RPGGameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Parallel Kingdom-style real-time RPG updates"""

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            user = self.scope["user"]
            if not user.is_authenticated:
                await self.close(code=4001)
                return

            self.character = await self.get_character(user)
            if not self.character:
                await self.close(code=4002)
                return

            await self.accept()

            # Character group for targeted updates
            self.character_group = f"character_{self.character.id}"
            await self.channel_layer.group_add(self.character_group, self.channel_name)

            # Fine-grained location group
            lat_key = int(self.character.lat * _grid_factor())
            lon_key = int(self.character.lon * _grid_factor())
            self.location_group = f"location_{lat_key}_{lon_key}"
            await self.channel_layer.group_add(self.location_group, self.channel_name)

            # Optional global groups
            await self.channel_layer.group_add("global_trade", self.channel_name)
            await self.channel_layer.group_add("global_chat", self.channel_name)

            await self.send(text_data=json.dumps({
                'type': 'connection_test',
                'message': f'Connected as {self.character.name} at ({self.character.lat}, {self.character.lon})'
            }))
            logger.info(f"WebSocket connected for user: {user.username}")

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'character_group'):
                await self.channel_layer.group_discard(self.character_group, self.channel_name)
            if hasattr(self, 'location_group'):
                await self.channel_layer.group_discard(self.location_group, self.channel_name)
            await self.channel_layer.group_discard("global_trade", self.channel_name)
            await self.channel_layer.group_discard("global_chat", self.channel_name)
            if hasattr(self, 'character'):
                await self.update_character_online_status(self.character.id, False)
                logger.info(f"WebSocket disconnected for character: {self.character.name}")
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'player_movement':
                await self.handle_player_movement(data)
            elif message_type == 'start_combat':
                await self.handle_start_combat(data)
            elif message_type == 'stop_combat':
                await self.stop_combat_loop()
            elif message_type == 'trade_request':
                await self.handle_trade_request(data)
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'request_nearby_data':
                await self.send_nearby_data()
            elif message_type == 'ping':
                await self.send_pong()
            elif message_type == 'jump_to_flag':
                await self.handle_jump_to_flag(data)
            elif message_type == 'collect_flag_revenue':
                await self.handle_collect_flag_revenue(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_player_movement(self, data):
        """Handle real-time player movement with fine-grained geolocation"""
        try:
            new_lat = float(data.get('lat'))
            new_lon = float(data.get('lon'))

            if not (-90 <= new_lat <= 90) or not (-180 <= new_lon <= 180):
                await self.send_error("Invalid coordinates")
                return

            # Validate territory + stamina and persist move (atomic on DB thread)
            try:
                old_lat, old_lon = await self._validate_and_move(self.character.id, new_lat, new_lon)
            except Exception as e:
                await self.send_error(str(e))
                return

            new_location_group = f"location_{int(new_lat * _grid_factor())}_{int(new_lon * _grid_factor())}"
            if new_location_group != self.location_group:
                await self.channel_layer.group_discard(self.location_group, self.channel_name)
                await self.channel_layer.group_add(new_location_group, self.channel_name)
                self.location_group = new_location_group

            await self.channel_layer.group_send(
                self.location_group,
                {
                    'type': 'player_moved',
                    'character_id': str(self.character.id),
                    'character_name': self.character.name,
                    'lat': new_lat,
                    'lon': new_lon,
                }
            )

        except (ValueError, TypeError) as e:
            await self.send_error(f"Invalid movement data: {e}")

    async def handle_start_combat(self, data):
        """Initiate simplified PK-style combat"""
        try:
            monster_id = data.get('monster_id')
            if not monster_id:
                await self.send_error('monster_id required')
                return
            combat_id = await self._ensure_pve_combat(monster_id)
            if not combat_id:
                await self.send_error('Failed to start combat')
                return
            await self.start_combat_loop({'combat_id': combat_id})
        except Exception as e:
            logger.error(f"Combat start error: {e}")
            await self.send_error('Combat start failed')

    async def handle_trade_request(self, data):
        """Handle trade initiation with nearby player"""
        try:
            target_character_id = data.get('target_character_id')
            items = data.get('items', [])

            if not target_character_id or not items:
                await self.send_error("Missing trade data")
                return

            trade_id = await self.create_trade(self.character.id, target_character_id, items)
            if trade_id:
                await self.channel_layer.group_send(
                    f"character_{target_character_id}",
                    {
                        'type': 'trade_offer',
                        'trade_id': str(trade_id),
                        'from_character': self.character.name,
                        'items': items
                    }
                )
                await self.send(text_data=json.dumps({
                    'type': 'trade_initiated',
                    'trade_id': str(trade_id),
                    'message': f"Trade offer sent to character {target_character_id}"
                }))
            else:
                await self.send_error("Failed to initiate trade")

        except Exception as e:
            logger.error(f"Trade request error: {e}")
            await self.send_error("Trade failed")

    async def handle_chat_message(self, data):
        """Handle PK-style chat (local or global)"""
        try:
            message = data.get('message', '').strip()
            chat_type = data.get('chat_type', 'local')

            if not message or len(message) > 200:
                await self.send_error("Invalid message")
                return

            chat_data = {
                'type': 'chat_message',
                'message': message,
                'character_name': self.character.name,
                'character_id': str(self.character.id),
                'chat_type': chat_type,
                'timestamp': self.get_current_timestamp()
            }

            if chat_type == 'local':
                await self.channel_layer.group_send(self.location_group, chat_data)
            elif chat_type == 'global':
                await self.channel_layer.group_send("global_chat", chat_data)

        except Exception as e:
            logger.error(f"Chat message error: {e}")
            await self.send_error("Chat failed")

    async def send_pong(self):
        """Respond to ping"""
        try:
            await self._regen_stamina()
        except Exception:
            pass
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': self.get_current_timestamp()
        }))

    @database_sync_to_async
    def _regen_stamina(self):
        from .services import stamina as stam
        try:
            stam.regen_stamina(self.character)
        except Exception:
            pass

    async def handle_jump_to_flag(self, data):
        """Handle Jump to Flag travel request"""
        try:
            flag_id = data.get('flag_id')
            if not flag_id:
                await self.send_error('flag_id required')
                return
            result = await self._jump_to_flag_db(flag_id)
            await self.send(text_data=json.dumps({
                'type': 'jump_to_flag',
                'result': result
            }))
            # Push HUD/character update
            try:
                await self.channel_layer.group_send(self.character_group, {'type': 'character_update'})
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Jump to flag error: {e}")
            await self.send_error('Jump failed')

    async def send_error(self, message):
        """Send error to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    # WebSocket event handlers
    async def player_moved(self, event):
        """Send player movement update"""
        if str(self.character.id) != event['character_id']:
            await self.send(text_data=json.dumps({
                'type': 'player_movement',
                'character_id': event['character_id'],
                'character_name': event['character_name'],
                'lat': event['lat'],
                'lon': event['lon'],
            }))

    async def trade_offer(self, event):
        """Forward trade offer to client"""
        await self.send(text_data=json.dumps({
            'type': 'trade_offer',
            'trade_id': event['trade_id'],
            'from_character': event['from_character'],
            'items': event['items']
        }))

    async def chat_message(self, event):
        """Send chat message to client"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'character_name': event['character_name'],
            'character_id': event['character_id'],
            'chat_type': event['chat_type'],
            'timestamp': event['timestamp']
        }))

    async def notification(self, event):
        """Send notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event.get('title', 'Notification'),
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info')
        }))

    async def character_update(self, event):
        """Push a fresh HUD snapshot to the connected client.
        Triggered by group_send(..., {'type': 'character_update'})
        """
        try:
            snap = await self._character_hud_snapshot()
            await self.send(text_data=json.dumps({'type': 'character_update', 'data': snap}))
        except Exception as e:
            logger.error(f"character_update send failed: {e}")

    # Database helper methods
    @database_sync_to_async
    def get_character(self, user):
        """Get character for user"""
        try:
            from .models import Character
            return Character.objects.get(user=user)
        except Exception:
            return None

    @database_sync_to_async
    def _validate_and_move(self, character_id, new_lat, new_lon):
        """Validate territory rules, consume stamina, and update position."""
        from .models import Character
        from .services.movement import ensure_in_territory, haversine_m
        from .services import stamina as stam
        from .services.movement import MovementError
        ch = Character.objects.get(id=character_id)
        # Territory check
        ensure_in_territory(ch, float(new_lat), float(new_lon))
        # Stamina cost for movement
        dist_m = haversine_m(float(ch.lat), float(ch.lon), float(new_lat), float(new_lon))
        cost = stam.movement_stamina_cost(dist_m)
        if not stam.consume_stamina(ch, cost):
            raise MovementError('exhausted', 'Insufficient stamina for movement')
        old_lat, old_lon = ch.lat, ch.lon
        ch.lat = float(new_lat)
        ch.lon = float(new_lon)
        ch.save(update_fields=['lat', 'lon'])
        return old_lat, old_lon

    @database_sync_to_async
    def update_character_online_status(self, character_id, is_online):
        """Update character online status"""
        try:
            from .models import Character
            character = Character.objects.get(id=character_id)
            character.is_online = is_online
            character.save(update_fields=['is_online', 'last_activity'])
            return True
        except Exception:
            return False

    @database_sync_to_async
    def create_trade(self, initiator_id, target_id, items):
        """Create a trade offer (minimal row using existing Trade model)."""
        try:
            from .models import Trade, Character
            # ensure recipient exists
            Character.objects.get(id=target_id)
            trade = Trade.objects.create(
                initiator_id=initiator_id,
                recipient_id=target_id,
            )
            return trade.id
        except Exception:
            return None

    async def start_combat_loop(self, event):
        """Start PK-style simplified combat loop using model turn interval."""
        try:
            combat_id = event.get('combat_id')
            if not combat_id:
                return
            await self.stop_combat_loop()
            self._combat_id = combat_id
            snap = await self._get_combat_snapshot(combat_id)
            if snap:
                await self.send(text_data=json.dumps({'type': 'combat_start', 'combat': snap}))
            self._combat_task = asyncio.create_task(self._run_pve_loop(combat_id))
        except Exception as e:
            logger.error(f"Start combat loop error: {e}")

    async def stop_combat_loop(self, *args, **kwargs):
        """Stop combat loop"""
        try:
            task = getattr(self, '_combat_task', None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._combat_task = None
            self._combat_id = None

    async def _run_pve_loop(self, combat_id: str):
        """Run combat loop at the session interval (fallback 2s)."""
        try:
            while True:
                result = await self._resolve_turn_and_snapshot(combat_id)
                if not result:
                    break
                await self.send(text_data=json.dumps({'type': 'combat_update', 'combat': result}))
                status = (result.get('status') or '').lower()
                if status in ('victory', 'defeat', 'fled'):
                    await self.send(text_data=json.dumps({'type': 'combat_end', 'combat': result}))
                    try:
                        await self.channel_layer.group_send(self.character_group, {'type': 'character_update'})
                    except Exception:
                        pass
                    break
                try:
                    interval = int(result.get('interval', 2) or 2)
                except Exception:
                    interval = 2
                await asyncio.sleep(max(0.1, float(interval)))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Combat loop error: {e}")

    @database_sync_to_async
    def _ensure_pve_combat(self, monster_id: str):
        """Start combat if within configured range (default 50m)."""
        try:
            from .models import Character, Monster, PvECombat
            ch = Character.objects.get(id=self.character.id)
            m = Monster.objects.get(id=monster_id, is_alive=True)
            if ch.in_combat or m.in_combat:
                return None
            dist = ch.distance_to(m.lat, m.lon)
            max_range_m = int(getattr(settings, 'PVE_COMBAT_RANGE_M', 50))
            if dist > max_range_m:
                return None
            combat = PvECombat.objects.create(
                character=ch,
                monster=m,
                character_hp=ch.current_hp,
                monster_hp=m.current_hp,
            )
            ch.in_combat = True
            ch.save(update_fields=['in_combat'])
            m.in_combat = True
            m.current_target = ch
            m.save(update_fields=['in_combat', 'current_target'])
            return str(combat.id)
        except Exception:
            return None

    @database_sync_to_async
    def _get_combat_snapshot(self, combat_id: str):
        """Get combat snapshot using model interval."""
        try:
            from .models import PvECombat
            c = PvECombat.objects.select_related('monster__template', 'character').get(id=combat_id)
            return {
                'id': str(c.id),
                'status': c.status,
                'character_hp': c.character_hp,
                'monster_hp': c.monster_hp,
                'interval': getattr(c, 'turn_interval_seconds', 2) or 2,
                'enemy': {
                    'name': c.monster.template.name,
                    'level': c.monster.template.level,
                    'max_hp': c.monster.max_hp,
                }
            }
        except Exception:
            return None

    @database_sync_to_async
    def _resolve_turn_and_snapshot(self, combat_id: str):
        """Resolve one combat turn via PvECombat.resolve_turn with fallback."""
        try:
            from .models import PvECombat
            c = PvECombat.objects.select_related('monster__template', 'character').get(id=combat_id)
            if c.status != 'active':
                return {
                    'id': str(c.id),
                    'status': c.status,
                    'character_hp': c.character_hp,
                    'monster_hp': c.monster_hp,
                    'interval': getattr(c, 'turn_interval_seconds', 2) or 2,
                    'enemy': {
                        'name': c.monster.template.name,
                        'level': c.monster.template.level,
                        'max_hp': c.monster.max_hp,
                    }
                }
            try:
                c.resolve_turn()
            except Exception:
                # Fallback simple resolution
                import random
                dmg = max(1, c.character.strength - c.monster.template.defense + random.randint(-3, 3))
                c.monster_hp = max(0, c.monster_hp - dmg)
                if c.monster_hp <= 0:
                    c.end_combat('victory')
                else:
                    dmg2 = max(1, c.monster.template.strength - c.character.defense + random.randint(-3, 3))
                    c.character_hp = max(0, c.character_hp - dmg2)
                    if c.character_hp <= 0:
                        c.end_combat('defeat')
                    else:
                        c.save()
            c.refresh_from_db()
            return {
                'id': str(c.id),
                'status': c.status,
                'character_hp': c.character_hp,
                'monster_hp': c.monster_hp,
                'interval': getattr(c, 'turn_interval_seconds', 2) or 2,
                'enemy': {
                    'name': c.monster.template.name,
                    'level': c.monster.template.level,
                    'max_hp': c.monster.max_hp,
                }
            }
        except Exception:
            return None

    async def send_nearby_data(self):
        """Send nearby players, monsters, and resources"""
        nearby_data = await self.get_nearby_data(self.character.id)
        if nearby_data:
            await self.send(text_data=json.dumps({
                'type': 'nearby_data',
                'data': nearby_data
            }))

    @database_sync_to_async
    def get_nearby_data(self, character_id):
        """Get nearby entities (≈50m for players, ≈20m for monsters/resources)."""
        try:
            from .models import Character, Monster, ResourceNode
            character = Character.objects.get(id=character_id)

            # Nearby players (~50m)
            lat_range = 0.00045
            lon_range = 0.00045
            nearby_players = Character.objects.filter(
                lat__gte=character.lat - lat_range,
                lat__lte=character.lat + lat_range,
                lon__gte=character.lon - lon_range,
                lon__lte=character.lon + lon_range,
                is_online=True
            ).exclude(id=character.id)[:20]

            # Nearby monsters/resources (~20m)
            lat_r = 0.00018
            lon_r = 0.00018
            nearby_monsters = Monster.objects.filter(
                lat__gte=character.lat - lat_r,
                lat__lte=character.lat + lat_r,
                lon__gte=character.lon - lon_r,
                lon__lte=character.lon + lon_r,
                is_alive=True
            ).select_related('template')[:10]

            nearby_resources = ResourceNode.objects.filter(
                lat__gte=character.lat - lat_r,
                lat__lte=character.lat + lat_r,
                lon__gte=character.lon - lon_r,
                lon__lte=character.lon + lon_r,
                is_depleted=False
            )[:10]

            return {
                'players': [
                    {
                        'id': str(p.id),
                        'name': p.name,
                        'level': p.level,
                        'lat': p.lat,
                        'lon': p.lon
                    } for p in nearby_players
                ],
                'monsters': [
                    {
                        'id': str(m.id),
                        'name': m.template.name,
                        'level': m.template.level,
                        'lat': m.lat,
                        'lon': m.lon,
                        'current_hp': m.current_hp,
                        'max_hp': m.max_hp
                    } for m in nearby_monsters
                ],
                'resources': [
                    {
                        'id': str(r.id),
                        'type': r.resource_type,
                        'lat': r.lat,
                        'lon': r.lon,
                        'quantity': r.quantity
                    } for r in nearby_resources
                ]
            }
        except Exception:
            return {'players': [], 'monsters': [], 'resources': []}

    def get_current_timestamp(self):
        """Get current timestamp"""
        return timezone.now().isoformat()

    @database_sync_to_async
    def _character_hud_snapshot(self) -> dict:
        """Return a concise HUD snapshot of the current character.
        Includes gold, HP/mana/stamina, XP progress, position, and jump cooldown remaining.
        """
        try:
            from .models import Character
            from django.utils import timezone as _tz
            ch = Character.objects.get(id=self.character.id)
            xp_needed = int(ch.experience_needed_for_next_level())
            xp_to_next = max(0, xp_needed - int(ch.experience))
            # Jump cooldown remaining
            try:
                cooldown_s = int(getattr(settings, 'GAME_SETTINGS', {}).get('JUMP_COOLDOWN_S', 60))
            except Exception:
                cooldown_s = 60
            remaining = 0
            if getattr(ch, 'last_jump_at', None):
                elapsed = (_tz.now() - ch.last_jump_at).total_seconds()
                if elapsed < cooldown_s:
                    remaining = max(0, int(cooldown_s - elapsed))
            return {
                'level': int(ch.level),
                'experience': int(ch.experience),
                'experience_to_next': int(xp_to_next),
                'health': int(ch.current_hp),
                'max_health': int(ch.max_hp),
                'mana': int(ch.current_mana),
                'max_mana': int(ch.max_mana),
                'stamina': int(ch.current_stamina),
                'max_stamina': int(ch.max_stamina),
                'gold': int(ch.gold),
                'lat': float(ch.lat),
                'lon': float(ch.lon),
                'can_jump': remaining == 0,
                'jump_cooldown_remaining_s': int(remaining),
                'downed_at': ch.downed_at.isoformat() if ch.downed_at else None,
                'respawn_available_at': ch.respawn_available_at.isoformat() if ch.respawn_available_at else None,
            }
        except Exception:
            return {}

    @database_sync_to_async
    def _jump_to_flag_db(self, flag_id: str):
        """Perform jump using travel service; returns a serializable dict.
        Formats TravelError into {success: False, error, seconds_remaining?}.
        """
        from .services.travel import jump_to_flag, TravelError
        try:
            res = jump_to_flag(self.scope.get('user'), flag_id)
            return {'success': True, 'location': res.get('location')}
        except TravelError as te:
            # If cooldown, compute remaining seconds
            seconds_remaining = None
            try:
                from django.utils import timezone as _tz
                from django.conf import settings as _st
                cooldown_s = int(getattr(_st, 'GAME_SETTINGS', {}).get('JUMP_COOLDOWN_S', 60))
                ch = self.character
                if getattr(ch, 'last_jump_at', None):
                    elapsed = (_tz.now() - ch.last_jump_at).total_seconds()
                    if elapsed < cooldown_s:
                        seconds_remaining = max(0, int(cooldown_s - elapsed))
            except Exception:
                seconds_remaining = None
            out = {'success': False, 'error': te.code}
            if seconds_remaining is not None:
                out['seconds_remaining'] = seconds_remaining
            return out

    async def handle_collect_flag_revenue(self, data):
        """Collect uncollected revenue from a flag owned by the player."""
        try:
            flag_id = data.get('flag_id')
            if not flag_id:
                await self.send_error('flag_id required')
                return
            res = await self._collect_flag_revenue_db(flag_id)
            await self.send(text_data=json.dumps({'type': 'collect_flag_revenue', 'result': res}))
            try:
                await self.channel_layer.group_send(self.character_group, {'type': 'character_update'})
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Collect revenue error: {e}")
            await self.send_error('Collect failed')

    @database_sync_to_async
    def _collect_flag_revenue_db(self, flag_id: str):
        from .services.flags import collect_revenue, FlagError
        try:
            user = self.scope.get('user')
            out = collect_revenue(user, flag_id)
            return {'success': True, **out}
        except FlagError as fe:
            return {'success': False, 'error': fe.code}
        except Exception:
            return {'success': False, 'error': 'server_error'}
