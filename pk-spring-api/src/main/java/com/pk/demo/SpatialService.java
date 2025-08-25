package com.pk.demo;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class SpatialService {
    
    @Autowired
    private FlagRepository flagRepository;
    
    @Autowired
    private PlayerRepository playerRepository;
    
    @Autowired
    private GameResourceRepository gameResourceRepository;
    
    @Autowired
    private NPCRepository npcRepository;
    
    /**
     * Calculate distance between two points
     */
    public double calculateDistance(double x1, double y1, double x2, double y2) {
        return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }
    
    /**
     * Check if a point is within a flag's zone
     */
    public boolean isPointInFlagZone(double x, double y, Flag flag) {
        double distance = calculateDistance(x, y, flag.getX(), flag.getY());
        return distance <= flag.getRadius();
    }
    
    /**
     * Find which flag zone a point belongs to (if any)
     */
    public Optional<Flag> findFlagForPoint(double x, double y) {
        List<Flag> allFlags = flagRepository.findAll();
        
        for (Flag flag : allFlags) {
            if (isPointInFlagZone(x, y, flag)) {
                return Optional.of(flag);
            }
        }
        
        return Optional.empty();
    }
    
    /**
     * Check if a player can move to a specific location
     * Rules: Player can only move within their flag zone, or to neutral territory if they don't have a flag
     */
    public boolean canPlayerMoveTo(int playerId, double targetX, double targetY) {
        Optional<Player> playerOpt = playerRepository.findById(playerId);
        if (!playerOpt.isPresent()) {
            return false;
        }
        
        Player player = playerOpt.get();
        
        // If player doesn't have a flag, they can move anywhere (neutral territory)
        if (player.getFlagId() == null) {
            // But check if the target location is in someone else's flag zone
            Optional<Flag> targetFlag = findFlagForPoint(targetX, targetY);
            // Allow movement only if target is neutral territory or their own flag
            return !targetFlag.isPresent() || 
                   (player.getFlagId() != null && targetFlag.get().getId() == player.getFlagId());
        }
        
        // Player has a flag - they can only move within their flag zone
        Optional<Flag> playerFlag = flagRepository.findById(player.getFlagId());
        if (!playerFlag.isPresent()) {
            return false;
        }
        
        return isPointInFlagZone(targetX, targetY, playerFlag.get());
    }
    
    /**
     * Get all entities (resources and NPCs) within a flag zone
     */
    public FlagEntities getFlagEntities(int flagId) {
        List<GameResource> resources = gameResourceRepository.findByFlagIdAndIsActive(flagId, true);
        List<NPC> npcs = npcRepository.findByFlagIdAndIsAlive(flagId, true);
        
        return new FlagEntities(resources, npcs);
    }
    
    /**
     * Get all entities within a rectangular area
     */
    public FlagEntities getEntitiesInArea(double minX, double maxX, double minY, double maxY) {
        List<GameResource> resources = gameResourceRepository.findResourcesInArea(minX, maxX, minY, maxY);
        List<NPC> npcs = npcRepository.findNPCsInArea(minX, maxX, minY, maxY);
        
        return new FlagEntities(resources, npcs);
    }
    
    /**
     * Check if a player is within range to interact with a resource
     */
    public boolean isPlayerInRangeOfResource(Player player, GameResource resource, double interactionRange) {
        double distance = calculateDistance(player.getX(), player.getY(), resource.getX(), resource.getY());
        return distance <= interactionRange;
    }
    
    /**
     * Check if a player is within range to interact with an NPC
     */
    public boolean isPlayerInRangeOfNPC(Player player, NPC npc, double interactionRange) {
        double distance = calculateDistance(player.getX(), player.getY(), npc.getX(), npc.getY());
        return distance <= interactionRange;
    }
    
    /**
     * Find the nearest resource of a specific type within a flag
     */
    public Optional<GameResource> findNearestResourceInFlag(int flagId, String resourceType, double fromX, double fromY) {
        List<GameResource> resources = gameResourceRepository.findByFlagIdAndTypeAndIsActive(flagId, resourceType, true);
        
        GameResource nearest = null;
        double nearestDistance = Double.MAX_VALUE;
        
        for (GameResource resource : resources) {
            double distance = calculateDistance(fromX, fromY, resource.getX(), resource.getY());
            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearest = resource;
            }
        }
        
        return Optional.ofNullable(nearest);
    }
    
    /**
     * Find the nearest NPC of a specific type within a flag
     */
    public Optional<NPC> findNearestNPCInFlag(int flagId, String npcType, double fromX, double fromY) {
        List<NPC> npcs = npcRepository.findByFlagIdAndTypeAndIsAlive(flagId, npcType, true);
        
        NPC nearest = null;
        double nearestDistance = Double.MAX_VALUE;
        
        for (NPC npc : npcs) {
            double distance = calculateDistance(fromX, fromY, npc.getX(), npc.getY());
            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearest = npc;
            }
        }
        
        return Optional.ofNullable(nearest);
    }
    
    /**
     * Helper class to group resources and NPCs
     */
    public static class FlagEntities {
        private List<GameResource> resources;
        private List<NPC> npcs;
        
        public FlagEntities(List<GameResource> resources, List<NPC> npcs) {
            this.resources = resources;
            this.npcs = npcs;
        }
        
        public List<GameResource> getResources() {
            return resources;
        }
        
        public List<NPC> getNpcs() {
            return npcs;
        }
    }
}
