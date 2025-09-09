"""
WebSocket consumers for Parallel Kingdom-style RPG game
Handles real-time geolocation, simplified combat, trading, and chat
"""
import json
import logging
import asyncio
import time
from django.utils import timezone
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


def _grid_factor() -> int:
    """Grid factor for location groups. 50000 ≈ ~20m cells; 1000 ≈ ~1km cells."""
    try:
        return int(getattr(settings, 'WS_LOCATION_GRID_FACTOR', 50000))
    except Exception:
        return 50000


class RPGGameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Parallel Kingdom-style real-time RPG updates"""

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # simple in-memory rate limiter per connection
            self._rl = {}
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
            elif message_type == 'trade_accept':
                await self.handle_trade_accept(data)
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
# Throttle rapid movement messages (anti-spam). Allow one every 100ms.
            if not self._rate_ok('player_movement', 0.10):
                return
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
            try:
                logger.info(f"[combat] WS start requested: char={self.character.id} monster={monster_id}")
            except Exception:
                pass
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

            result = await self.create_trade(self.character.id, target_character_id, items)
            if result and not result.get('error') and result.get('id'):
                trade_id = result.get('id')
                await self.channel_layer.group_send(
                    f"character_{target_character_id}",
                    {
                        'type': 'trade_offer',
                        'trade_id': str(trade_id),
                        'from_character': self.character.name,
                        'items': items
                    }
                )
                try:
                    logger.info(f"[trade] initiated: from={self.character.id} to={target_character_id} trade={trade_id} items={len(items) if isinstance(items, list) else 'n/a'}")
                except Exception:
                    pass
                await self.send(text_data=json.dumps({
                    'type': 'trade_initiated',
                    'trade_id': str(trade_id),
                    'message': f"Trade offer sent to character {target_character_id}"
                }))
            else:
                await self.send_error(result.get('error') if result else "Failed to initiate trade")

        except Exception as e:
            logger.error(f"Trade request error: {e}")
            await self.send_error("Trade failed")

    async def handle_trade_accept(self, data):
        """Handle acceptance of a pending trade by the recipient."""
        try:
            trade_id = data.get('trade_id')
            if not trade_id:
                await self.send_error('trade_id required')
                return
            res = await self._accept_trade_db(trade_id)
            if res.get('success'):
                payload = {
                    'type': 'trade_accepted',
                    'trade_id': str(trade_id),
                    'by': str(self.character.id),
                }
                initiator_id = res.get('initiator_id')
                recipient_id = res.get('recipient_id')
                if initiator_id:
                    await self.channel_layer.group_send(f"character_{initiator_id}", payload)
                if recipient_id:
                    await self.channel_layer.group_send(f"character_{recipient_id}", payload)
                try:
                    logger.info(f"[trade] accepted: by={self.character.id} trade={trade_id} initiator={initiator_id} recipient={recipient_id}")
                except Exception:
                    pass
            else:
                await self.send_error(res.get('error') or 'trade_accept_failed')
        except Exception as e:
            logger.error(f"Trade accept error: {e}")
            await self.send_error('Trade accept failed')

    async def handle_chat_message(self, data):
        """Handle PK-style chat (local or global)"""
        try:
# Rate limit chat: 1 message per 0.5s per connection
            if not self._rate_ok('chat_message', 0.5):
                await self.send_error("You're sending messages too quickly.")
                return
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
            # Strong rate limit: once per 10 seconds
            if not self._rate_ok('jump_to_flag', 10.0):
                await self.send_error('Please wait before jumping again')
                return
            flag_id = data.get('flag_id')
            if not flag_id:
                await self.send_error('flag_id required')
                return
            # Ownership and proximity (~50m) validation before attempting jump
            pre = await self._validate_flag_jump_preconditions(flag_id)
            if not pre.get('ok'):
                err = pre.get('error') or 'jump_precondition_failed'
                payload = {'type': 'jump_to_flag', 'result': {'success': False, 'error': err}}
                if 'seconds_remaining' in pre:
                    payload['result']['seconds_remaining'] = pre['seconds_remaining']
                await self.send(text_data=json.dumps(payload))
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

    async def trade_accepted(self, event):
        """Notify client that a trade was accepted."""
        await self.send(text_data=json.dumps({
            'type': 'trade_accepted',
            'trade_id': event.get('trade_id'),
            'by': event.get('by'),
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
            # Existing event (used by current HUD)
            await self.send(text_data=json.dumps({'type': 'character_update', 'data': snap}))
            # Parallel event for clients expecting 'character' with id/name/gold
            await self.send(text_data=json.dumps({'type': 'character', 'data': snap}))
        except Exception as e:
            logger.error(f"character_update send failed: {e}")

    async def nearby_update(self, event):
        """Push a combined nearby payload (players, monsters, resources)."""
        try:
            await self.send_nearby_data()
        except Exception as e:
            logger.error(f"nearby_update send failed: {e}")

    async def resource_update(self, event):
        """Forward resource updates to client (single or batch)."""
        try:
            payload = {}
            if 'resource' in event:
                payload = {'resource': event['resource']}
            elif 'resources' in event:
                payload = {'resources': event['resources']}
            await self.send(text_data=json.dumps({'type': 'resource_update', **payload}))
        except Exception:
            pass

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
        # Stamina cost for movement — 0.1 stamina per meter (min 1)
        dist_m = haversine_m(float(ch.lat), float(ch.lon), float(new_lat), float(new_lon))
        cost = max(1, int(round(dist_m * 0.1)))
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
        """Create a trade offer after validating proximity (~20m) and ownership.
        Returns {'id': <trade_id>} on success or {'error': <code>} on failure.
        """
        try:
            from django.apps import apps
            from .services.movement import haversine_m
            Character = apps.get_model('main', 'Character')
            Trade = apps.get_model('main', 'Trade')
            InventoryItem = None
            try:
                InventoryItem = apps.get_model('main', 'InventoryItem')
            except Exception:
                InventoryItem = None
            initiator = Character.objects.get(id=initiator_id)
            target = Character.objects.get(id=target_id)
            # Proximity check (~20m)
            try:
                if hasattr(initiator, 'distance_to'):
                    dist = float(initiator.distance_to(target.lat, target.lon))
                else:
                    dist = float(haversine_m(float(initiator.lat), float(initiator.lon), float(target.lat), float(target.lon)))
            except Exception:
                dist = 999999.0
            if dist > 20.0:
                return {'error': 'too_far'}
            # Item ownership validation (best-effort)
            if InventoryItem:
                # find FK to Character dynamically
                owner_field = None
                for f in InventoryItem._meta.get_fields():
                    try:
                        if getattr(f, 'is_relation', False) and getattr(f, 'related_model', None) == Character:
                            owner_field = f.name
                            break
                    except Exception:
                        continue
                for it in items:
                    item_id = None
                    if isinstance(it, dict):
                        item_id = it.get('id') or it.get('item_id') or it.get('inventory_item_id')
                    elif isinstance(it, (int, str)):
                        item_id = it
                    if not item_id:
                        return {'error': 'invalid_item'}
                    qs = InventoryItem.objects.filter(id=item_id)
                    if owner_field:
                        qs = qs.filter(**{owner_field: initiator})
                    if not qs.exists():
                        return {'error': 'not_owner'}
            trade = Trade.objects.create(
                initiator_id=initiator_id,
                recipient_id=target_id,
            )
            return {'id': str(trade.id)}
        except Exception:
            return {'error': 'server_error'}

    @database_sync_to_async
    def _accept_trade_db(self, trade_id: str) -> dict:
        from django.apps import apps
        from .services.movement import haversine_m
        try:
            Character = apps.get_model('main', 'Character')
            Trade = apps.get_model('main', 'Trade')
            trade = Trade.objects.get(id=trade_id)
            # Validate recipient matches current character
            recip_id = getattr(trade, 'recipient_id', None)
            if recip_id is None and hasattr(trade, 'recipient'):
                recip_id = getattr(trade.recipient, 'id', None)
            if str(recip_id) != str(self.character.id):
                return {'success': False, 'error': 'not_recipient'}
            # Proximity check between initiator and recipient (~20m)
            init_id = getattr(trade, 'initiator_id', None)
            if init_id is None and hasattr(trade, 'initiator'):
                init_id = getattr(trade.initiator, 'id', None)
            initiator = Character.objects.get(id=init_id)
            recipient = Character.objects.get(id=self.character.id)
            try:
                if hasattr(initiator, 'distance_to'):
                    dist = float(initiator.distance_to(recipient.lat, recipient.lon))
                else:
                    dist = float(haversine_m(float(initiator.lat), float(initiator.lon), float(recipient.lat), float(recipient.lon)))
            except Exception:
                dist = 999999.0
            if dist > 20.0:
                return {'success': False, 'error': 'too_far'}
            # Accept trade using model method if available
            if hasattr(trade, 'accept') and callable(getattr(trade, 'accept')):
                trade.accept()
            else:
                if hasattr(trade, 'status'):
                    trade.status = 'accepted'
                    trade.save(update_fields=['status'])
                else:
                    trade.save()
            return {'success': True, 'initiator_id': str(init_id), 'recipient_id': str(self.character.id)}
        except Exception:
            return {'success': False, 'error': 'server_error'}

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
                # Enrich combat_start payload for clients expecting concise fields
                try:
                    payload = {
                        'type': 'combat_start',
                        'combat': snap,
                        'combatId': snap.get('id'),
                        'playerId': snap.get('player_id'),
                        'playerHp': snap.get('player_hp'),
                        'enemyId': snap.get('enemy_id'),
                        'enemyName': (snap.get('enemy') or {}).get('name'),
                        'enemyMaxHp': (snap.get('enemy') or {}).get('max_hp'),
                        'enemyHp': snap.get('enemy_hp'),
                        'interval': snap.get('interval'),
                        'objectId': snap.get('enemy_id'),
                        'objectType': 'mob',
                        'objectName': (snap.get('enemy') or {}).get('name'),
                        'position': snap.get('enemy_position') or {},
                    }
                except Exception:
                    payload = {'type': 'combat_start', 'combat': snap}
                await self.send(text_data=json.dumps(payload))
                try:
                    logger.info(f"[combat] start: combat={combat_id} char={snap.get('player_id')} enemy={snap.get('enemy_id')}")
                except Exception:
                    pass
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
# Emit granular combat:damage events derived from HP deltas
                try:
                    dmg_enemy = int(result.get('damage_to_enemy') or 0)
                    dmg_player = int(result.get('damage_to_player') or 0)
                    enemy_id = result.get('enemy_id')
                    enemy_name = ((result.get('enemy') or {}).get('name')) if result.get('enemy') else 'Enemy'
                    enemy_pos = result.get('enemy_position') or {}
                    if dmg_enemy > 0 and enemy_id:
                        await self.send(text_data=json.dumps({
                            'type': 'combat:damage',
                            'targetId': enemy_id,
                            'targetName': enemy_name,
                            'targetType': 'mob',
                            'damage': int(dmg_enemy),
                            'isCritical': False,
                            'position': enemy_pos,
                        }))
                    if dmg_player > 0:
                        await self.send(text_data=json.dumps({
                            'type': 'combat:damage',
                            'targetId': str(getattr(self, 'character', None).id) if getattr(self, 'character', None) else None,
                            'targetName': getattr(self, 'character', None).name if getattr(self, 'character', None) else 'You',
                            'targetType': 'player',
                            'damage': int(dmg_player),
                            'isCritical': False,
                        }))
                    # Turn-by-turn combat log for UI
                    if result.get('message'):
                        await self.send(text_data=json.dumps({
                            'type': 'combat:log',
                            'message': result.get('message'),
                            'timestamp': self.get_current_timestamp(),
                        }))
                except Exception:
                    pass

                # Preserve existing aggregate update for backward compatibility
                await self.send(text_data=json.dumps({'type': 'combat_update', 'combat': result}))
                status = (result.get('status') or '').lower()
                if status in ('victory', 'defeat', 'fled'):
                    try:
                        # Enrich end event for UI convenience
                        snap = await self._character_hud_snapshot()
                    except Exception:
                        snap = {}
                    # Richer combat_end payload
                    end_payload = {
                        'type': 'combat_end',
                        'combat': result,
                        'victory': status == 'victory',
                        'defeat': status == 'defeat',
                        'message': result.get('message'),
                        'character': snap,
                        'combatId': result.get('id'),
                        'status': result.get('status'),
                        'playerHp': result.get('player_hp'),
                        'enemyHp': result.get('enemy_hp'),
                        'enemyId': result.get('enemy_id'),
                        'enemyName': ((result.get('enemy') or {}).get('name')) if result.get('enemy') else None,
                    }
                    await self.send(text_data=json.dumps(end_payload))
                    try:
                        logger.info(f"[combat] end: combat={result.get('id')} status={status} char={result.get('player_id')} enemy={result.get('enemy_id')}")
                    except Exception:
                        pass
                    try:
                        await self.channel_layer.group_send(self.character_group, {'type': 'character_update'})
                    except Exception:
                        pass
                    break
                try:
                    interval = float(result.get('interval', 0.5) or 0.5)
                except Exception:
                    interval = 0.5
                await asyncio.sleep(max(0.05, float(interval)))
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
            # No fixed minimum distance gate here. We rely on PK-style leash/territory rules
            # enforced by the HTTP move endpoint to end combat when the player wanders too far.
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
                # Standardized keys used by frontend HUD
                'player_hp': c.character_hp,
                'enemy_hp': c.monster_hp,
                # IDs and positions for richer client integrations
                'player_id': str(getattr(c, 'character_id', c.character.id)),
                'enemy_id': str(getattr(c, 'monster_id', c.monster.id)),
                'enemy_position': {
                    'lat': getattr(c.monster, 'lat', None),
                    'lon': getattr(c.monster, 'lon', None),
                },
# Backward-compat keys (legacy)
                'character_hp': c.character_hp,
                'monster_hp': c.monster_hp,
                'interval': float(getattr(c, 'turn_interval_seconds', 0.5) or 0.5),
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
        """Resolve one ultra-fast PK-style combat turn (0.5s default).
        Uses flat damage: character.strength + rand[-1,1], no defense.
        Returns a snapshot with damage deltas and a human-readable message.
        """
        try:
            from django.db import transaction
            from .models import PvECombat
            import random
            with transaction.atomic():
                c = PvECombat.objects.select_related('monster__template', 'character').select_for_update().get(id=combat_id)
                interval = float(getattr(c, 'turn_interval_seconds', 0.5) or 0.5)
                # If not active, just echo state
                if c.status != 'active':
                    return {
                        'id': str(c.id),
                        'status': c.status,
                        'character_hp': c.character_hp,
                        'monster_hp': c.monster_hp,
                        'interval': interval,
                        'player_id': str(getattr(c, 'character_id', c.character.id)),
                        'enemy_id': str(getattr(c, 'monster_id', c.monster.id)),
                        'enemy': {
                            'name': c.monster.template.name,
                            'level': c.monster.template.level,
                            'max_hp': c.monster.max_hp,
                        },
                        'enemy_position': {
                            'lat': getattr(c.monster, 'lat', None), 
                            'lon': getattr(c.monster, 'lon', None),
                        },
                    }
                # Pre-turn HPs for deltas
                prev_ch_hp, prev_m_hp = int(c.character_hp), int(c.monster_hp)
                enemy_name = getattr(getattr(c, 'monster', None), 'template', None).name if getattr(getattr(c, 'monster', None), 'template', None) else 'Enemy'
                # Flat damage model
                char_str = int(getattr(c.character, 'strength', 1))
                mon_str = int(getattr(c.monster.template, 'strength', 1))
                dmg_to_enemy = max(1, char_str + random.randint(-1, 1))
                c.monster_hp = max(0, int(c.monster_hp) - int(dmg_to_enemy))
                if int(c.monster_hp) <= 0:
                    c.end_combat('victory')
                    c.refresh_from_db()
                    d_m = max(0, prev_m_hp - int(c.monster_hp))
                    d_c = max(0, prev_ch_hp - int(c.character_hp))
                    msg = f"You hit {enemy_name} for {d_m}! {enemy_name} defeated!"
                    return {
                        'id': str(c.id),
                        'status': c.status,
                        'player_hp': c.character_hp,
                        'enemy_hp': c.monster_hp,
                        'player_id': str(getattr(c, 'character_id', c.character.id)),
                        'enemy_id': str(getattr(c, 'monster_id', c.monster.id)),
                        'enemy_position': {
                            'lat': getattr(c.monster, 'lat', None),
                            'lon': getattr(c.monster, 'lon', None),
                        },
                        'damage_to_enemy': int(max(0, d_m)),
                        'damage_to_player': int(max(0, d_c)),
                        'character_hp': c.character_hp,
                        'monster_hp': c.monster_hp,
                        'interval': interval,
                        'enemy': {
                            'name': c.monster.template.name,
                            'level': c.monster.template.level,
                            'max_hp': c.monster.max_hp,
                        },
                        'message': msg,
                    }
                # Monster retaliates only if still alive
                dmg_to_player = max(1, mon_str + random.randint(-1, 1))
                c.character_hp = max(0, int(c.character_hp) - int(dmg_to_player))
                if int(c.character_hp) <= 0:
                    c.end_combat('defeat')
                else:
                    c.save(update_fields=['monster_hp', 'character_hp'])
            # After transaction, refresh and compose payload
            from .models import PvECombat as _PvE
            c = _PvE.objects.select_related('monster__template', 'character').get(id=combat_id)
            interval = float(getattr(c, 'turn_interval_seconds', 0.5) or 0.5)
            d_m = max(0, prev_m_hp - int(c.monster_hp))
            d_c = max(0, prev_ch_hp - int(c.character_hp))
            enemy_name = getattr(getattr(c, 'monster', None), 'template', None).name if getattr(getattr(c, 'monster', None), 'template', None) else 'Enemy'
            if c.status == 'active':
                parts = []
                if d_m > 0:
                    parts.append(f"You hit {enemy_name} for {d_m}!")
                if d_c > 0:
                    parts.append(f"{enemy_name} hit you for {d_c}!")
                msg = " ".join(parts) if parts else None
            elif c.status == 'victory':
                msg = f"You hit {enemy_name} for {d_m}! {enemy_name} defeated!"
            elif c.status == 'defeat':
                msg = f"{enemy_name} hit you for {d_c}! You are downed."
            else:
                msg = None
            return {
                'id': str(c.id),
                'status': c.status,
                'player_hp': c.character_hp,
                'enemy_hp': c.monster_hp,
                'player_id': str(getattr(c, 'character_id', c.character.id)),
                'enemy_id': str(getattr(c, 'monster_id', c.monster.id)),
                'enemy_position': {
                    'lat': getattr(c.monster, 'lat', None),
                    'lon': getattr(c.monster, 'lon', None),
                },
                'damage_to_enemy': int(max(0, d_m)),
                'damage_to_player': int(max(0, d_c)),
                'character_hp': c.character_hp,
                'monster_hp': c.monster_hp,
                'interval': interval,
                'enemy': {
                    'name': c.monster.template.name,
                    'level': c.monster.template.level,
                    'max_hp': c.monster.max_hp,
                },
                'message': msg,
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
        """Get nearby entities (~20m for players, monsters, resources) and flags."""
        try:
            from django.apps import apps
            Character = apps.get_model('main', 'Character')
            Monster = apps.get_model('main', 'Monster')
            ResourceNode = apps.get_model('main', 'ResourceNode')
            Flag = None
            try:
                Flag = apps.get_model('main', 'Flag')
            except Exception:
                Flag = None
            character = Character.objects.get(id=character_id)

            # Nearby ranges (~20m)
            lat_r = 0.00018
            lon_r = 0.00018

            nearby_players = Character.objects.filter(
                lat__gte=character.lat - lat_r,
                lat__lte=character.lat + lat_r,
                lon__gte=character.lon - lon_r,
                lon__lte=character.lon + lon_r,
                is_online=True
            ).exclude(id=character.id)[:20]

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

            flags_payload = {'owned': [], 'nearby': []}
            if Flag:
                # Determine owner field on Flag pointing to Character
                owner_field = None
                for f in Flag._meta.get_fields():
                    try:
                        if getattr(f, 'is_relation', False) and getattr(f, 'related_model', None) == Character:
                            owner_field = f.name
                            break
                    except Exception:
                        continue
                if owner_field:
                    try:
                        owned_flags = Flag.objects.filter(**{owner_field: character})[:20]
                    except Exception:
                        owned_flags = []
                else:
                    owned_flags = []
                try:
                    nearby_flags = Flag.objects.filter(
                        lat__gte=character.lat - lat_r,
                        lat__lte=character.lat + lat_r,
                        lon__gte=character.lon - lon_r,
                        lon__lte=character.lon + lon_r,
                    )[:20]
                except Exception:
                    nearby_flags = []
                flags_payload = {
                    'owned': [
                        {
                            'id': str(f.id),
                            'lat': getattr(f, 'lat', None),
                            'lon': getattr(f, 'lon', None),
                            'level': int(getattr(f, 'level', 1) or 1),
                        } for f in owned_flags
                    ],
                    'nearby': [
                        {
                            'id': str(f.id),
                            'lat': getattr(f, 'lat', None),
                            'lon': getattr(f, 'lon', None),
                            'level': int(getattr(f, 'level', 1) or 1),
                        } for f in nearby_flags
                    ]
                }

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
                ],
                'flags': flags_payload,
            }
        except Exception:
            return {'players': [], 'monsters': [], 'resources': [], 'flags': {'owned': [], 'nearby': []}}

    def get_current_timestamp(self):
        """Get current timestamp"""
        return timezone.now().isoformat()

    def _rate_ok(self, key: str, interval_s: float) -> bool:
        """Simple per-connection rate limiter. Returns True if allowed."""
        try:
            now = time.monotonic()
            last = self._rl.get(key)
            if last is not None and (now - last) < float(interval_s):
                return False
            self._rl[key] = now
            return True
        except Exception:
            return True

    @database_sync_to_async
    def _character_hud_snapshot(self) -> dict:
        """Return a concise HUD snapshot of the current character.
        Includes gold, HP/mana/stamina, XP progress, position, jump cooldown, owned flags, and trade status.
        """
        try:
            from django.apps import apps
            from django.utils import timezone as _tz
            Character = apps.get_model('main', 'Character')
            Flag = None
            Trade = None
            try:
                Flag = apps.get_model('main', 'Flag')
            except Exception:
                Flag = None
            try:
                Trade = apps.get_model('main', 'Trade')
            except Exception:
                Trade = None
            ch = Character.objects.get(id=self.character.id)
            xp_needed = int(ch.experience_needed_for_next_level())
            xp_to_next = max(0, xp_needed - int(ch.experience))
            # Jump cooldown remaining (honor 10s minimum if GAME_SETTINGS longer)
            try:
                cooldown_s = max(10, int(getattr(settings, 'GAME_SETTINGS', {}).get('JUMP_COOLDOWN_S', 60)))
            except Exception:
                cooldown_s = 10
            remaining = 0
            if getattr(ch, 'last_jump_at', None):
                elapsed = (_tz.now() - ch.last_jump_at).total_seconds()
                if elapsed < cooldown_s:
                    remaining = max(0, int(cooldown_s - elapsed))
            # Owned flags summary (best-effort)
            owned_flags = []
            if Flag:
                owner_field = None
                for f in Flag._meta.get_fields():
                    try:
                        if getattr(f, 'is_relation', False) and getattr(f, 'related_model', None) == Character:
                            owner_field = f.name
                            break
                    except Exception:
                        continue
                if owner_field:
                    try:
                        for fl in Flag.objects.filter(**{owner_field: ch})[:20]:
                            owned_flags.append({
                                'id': str(fl.id),
                                'lat': getattr(fl, 'lat', None),
                                'lon': getattr(fl, 'lon', None),
                                'level': int(getattr(fl, 'level', 1) or 1),
                            })
                    except Exception:
                        pass
            # Trade status summary (best-effort)
            trade_status = {'outbound_pending': 0, 'inbound_pending': 0}
            if Trade:
                try:
                    fields = {f.name for f in Trade._meta.get_fields()}
                    qs_out = Trade.objects.filter(initiator_id=ch.id)
                    qs_in = Trade.objects.filter(recipient_id=ch.id)
                    if 'status' in fields:
                        qs_out = qs_out.filter(status__in=['pending', 'open'])
                        qs_in = qs_in.filter(status__in=['pending', 'open'])
                    elif 'accepted_at' in fields:
                        qs_out = qs_out.filter(accepted_at__isnull=True)
                        qs_in = qs_in.filter(accepted_at__isnull=True)
                    trade_status['outbound_pending'] = qs_out.count()
                    trade_status['inbound_pending'] = qs_in.count()
                except Exception:
                    pass
            return {
                'id': str(ch.id),
                'name': ch.name,
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
                'flags_owned': owned_flags,
                'trade_status': trade_status,
            }
        except Exception:
            return {}

    @database_sync_to_async
    def _validate_flag_jump_preconditions(self, flag_id: str) -> dict:
        from django.apps import apps
        from django.utils import timezone as _tz
        try:
            Character = apps.get_model('main', 'Character')
            Flag = apps.get_model('main', 'Flag')
            ch = Character.objects.get(id=self.character.id)
            flag = Flag.objects.get(id=flag_id)
            # Ownership check (FK to Character)
            owner_field = None
            for f in Flag._meta.get_fields():
                try:
                    if getattr(f, 'is_relation', False) and getattr(f, 'related_model', None) == Character:
                        owner_field = f.name
                        break
                except Exception:
                    continue
            if not owner_field:
                return {'ok': False, 'error': 'flag_owner_missing'}
            owner = getattr(flag, owner_field, None)
            if not owner or str(owner.id) != str(ch.id):
                return {'ok': False, 'error': 'not_owner'}
            # Proximity check (~50m)
            try:
                if hasattr(ch, 'distance_to'):
                    dist = float(ch.distance_to(flag.lat, flag.lon))
                else:
                    from .services.movement import haversine_m
                    dist = float(haversine_m(float(ch.lat), float(ch.lon), float(getattr(flag, 'lat', 0)), float(getattr(flag, 'lon', 0))))
            except Exception:
                dist = 999999.0
            if dist > 50.0:
                return {'ok': False, 'error': 'too_far'}
            # Cooldown pre-check (10s)
            try:
                last = getattr(ch, 'last_jump_at', None)
                if last:
                    elapsed = (_tz.now() - last).total_seconds()
                    if elapsed < 10.0:
                        return {'ok': False, 'error': 'cooldown', 'seconds_remaining': max(0, int(10 - elapsed))}
            except Exception:
                pass
            return {'ok': True}
        except Exception:
            return {'ok': False, 'error': 'server_error'}

    @database_sync_to_async
    def _jump_to_flag_db(self, flag_id: str):
        """Perform jump using travel service; returns a serializable dict.
        Enforces a strict 10s cooldown and formats TravelError into
        {success: False, error, seconds_remaining?}.
        """
        from .services.travel import jump_to_flag, TravelError
        from django.utils import timezone as _tz
        from django.apps import apps
        try:
            # Enforce 10s cooldown before delegating to service
            Character = apps.get_model('main', 'Character')
            ch = Character.objects.get(id=self.character.id)
            last = getattr(ch, 'last_jump_at', None)
            if last:
                elapsed = (_tz.now() - last).total_seconds()
                if elapsed < 10.0:
                    return {'success': False, 'error': 'cooldown', 'seconds_remaining': max(0, int(10 - elapsed))}
            res = jump_to_flag(self.scope.get('user'), flag_id)
            return {'success': True, 'location': res.get('location')}
        except TravelError as te:
            # If cooldown, compute remaining seconds (fixed 10s window)
            seconds_remaining = None
            try:
                ch = self.character
                if getattr(ch, 'last_jump_at', None):
                    elapsed = (_tz.now() - ch.last_jump_at).total_seconds()
                    if elapsed < 10.0:
                        seconds_remaining = max(0, int(10 - elapsed))
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
        from django.apps import apps
        try:
            user = self.scope.get('user')
            base = collect_revenue(user, flag_id)  # assumes it credits base gold
            # Apply multiplier: Flag.level * base_revenue (crediting extra gold if needed)
            try:
                Flag = apps.get_model('main', 'Flag')
                Character = apps.get_model('main', 'Character')
                ch = Character.objects.get(id=self.character.id)
                flag = Flag.objects.get(id=flag_id)
                level = int(getattr(flag, 'level', 1) or 1)
                base_gold = int(base.get('gold', base.get('amount', 0)) or 0)
                if base_gold > 0 and level > 1:
                    # credit the additional gold (level-1) * base_gold
                    extra = (level - 1) * base_gold
                    try:
                        ch.gold = int(getattr(ch, 'gold', 0)) + int(extra)
                        ch.save(update_fields=['gold'])
                    except Exception:
                        pass
                return {'success': True, 'gold_base': base_gold, 'gold_multiplier': level, 'gold_awarded': base_gold * max(1, level)}
            except Exception:
                return {'success': True, **base}
        except FlagError as fe:
            return {'success': False, 'error': fe.code}
        except Exception:
            return {'success': False, 'error': 'server_error'}
