package com.pk.demo;

import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class GameEventPublisher {

    private final SimpMessagingTemplate messagingTemplate;

    public GameEventPublisher(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void publishAreaUpdate(String tileId, Map<String, Object> payload) {
        messagingTemplate.convertAndSend("/topic/state/area/" + tileId, payload);
    }

    public void publishPlayerEvent(int playerId, Map<String, Object> payload) {
        messagingTemplate.convertAndSend("/topic/player/" + playerId, payload);
    }

    public void publishFlagPlaced(Flag flag) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "flag_placed");
        payload.put("flag", flag);
        messagingTemplate.convertAndSend("/topic/state/flag", payload);
    }

    public void publishPlayerMoved(Player player) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "player_moved");
        payload.put("player", player);
        messagingTemplate.convertAndSend("/topic/state/player", payload);
    }

    public void publishEntitiesUpdate(String tileId, List<GameResource> resources, List<NPC> npcs) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("event", "entities_update");
        payload.put("resources", resources);
        payload.put("npcs", npcs);
        publishAreaUpdate(tileId, payload);
    }
}

