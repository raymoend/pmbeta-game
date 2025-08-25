package com.pk.demo;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/game")
@CrossOrigin(origins = "*")
public class GameController {
    
    @Autowired
    private SpatialService spatialService;
    
    @Autowired
    private PlayerRepository playerRepository;
    
    @Autowired
    private FlagRepository flagRepository;
    
    @Autowired
    private GameResourceRepository gameResourceRepository;
    
@Autowired
    private NPCRepository npcRepository;

    @Autowired
    private GameEventPublisher gameEventPublisher;
    
    /**
     * Move a player to a new position
     */
    @PostMapping("/player/{playerId}/move")
    public ResponseEntity<?> movePlayer(@PathVariable int playerId, 
                                      @RequestParam double x, 
                                      @RequestParam double y) {
        
        // Check if player exists
        Optional<Player> playerOpt = playerRepository.findById(playerId);
        if (!playerOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        
        Player player = playerOpt.get();
        
        // Check if movement is allowed
        if (!spatialService.canPlayerMoveTo(playerId, x, y)) {
            return ResponseEntity.badRequest()
                .body(new ErrorResponse("Movement not allowed - outside flag zone"));
        }
        
        // Update player position
        player.setX(x);
        player.setY(y);
        playerRepository.save(player);
        
        // Publish WS event
        try {
            gameEventPublisher.publishPlayerMoved(player);
        } catch (Exception ignored) {}
        
        return ResponseEntity.ok(new MoveResponse("Movement successful", x, y));
    }
    
    /**
     * Get all flags
     */
    @GetMapping("/flags")
    public ResponseEntity<List<Flag>> getAllFlags() {
        return ResponseEntity.ok(flagRepository.findAll());
    }
    
    /**
     * Get a specific flag with its entities
     */
    @GetMapping("/flag/{flagId}")
    public ResponseEntity<FlagDetailsResponse> getFlagDetails(@PathVariable int flagId) {
        Optional<Flag> flagOpt = flagRepository.findById(flagId);
        if (!flagOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        
        Flag flag = flagOpt.get();
        SpatialService.FlagEntities entities = spatialService.getFlagEntities(flagId);
        
        return ResponseEntity.ok(new FlagDetailsResponse(flag, entities.getResources(), entities.getNpcs()));
    }
    
    /**
     * Consolidated state in a rectangular area (flags, players, entities)
     */
    @GetMapping("/state")
    public ResponseEntity<StateResponse> getState(
            @RequestParam double minX,
            @RequestParam double maxX,
            @RequestParam double minY,
            @RequestParam double maxY) {
        
        SpatialService.FlagEntities entities = spatialService.getEntitiesInArea(minX, maxX, minY, maxY);
        List<Flag> flags = flagRepository.findAll();
        List<Player> players = playerRepository.findAll();
        
        return ResponseEntity.ok(new StateResponse(System.currentTimeMillis(), flags, players, entities.getResources(), entities.getNpcs()));
    }

    /**
     * Get all entities in a rectangular area
     */
    @GetMapping("/entities")
    public ResponseEntity<AreaEntitiesResponse> getEntitiesInArea(
            @RequestParam double minX,
            @RequestParam double maxX,
            @RequestParam double minY,
            @RequestParam double maxY) {
        
        SpatialService.FlagEntities entities = spatialService.getEntitiesInArea(minX, maxX, minY, maxY);
        
        return ResponseEntity.ok(new AreaEntitiesResponse(entities.getResources(), entities.getNpcs()));
    }
    
    /**
     * Get all players
     */
    @GetMapping("/players")
    public ResponseEntity<List<Player>> getAllPlayers() {
        return ResponseEntity.ok(playerRepository.findAll());
    }
    
    /**
     * Get a specific player
     */
    @GetMapping("/player/{playerId}")
    public ResponseEntity<Player> getPlayer(@PathVariable int playerId) {
        Optional<Player> playerOpt = playerRepository.findById(playerId);
        if (!playerOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        
        return ResponseEntity.ok(playerOpt.get());
    }
    
    /**
     * Check if a position is within a player's movement range
     */
    @GetMapping("/player/{playerId}/can-move")
    public ResponseEntity<CanMoveResponse> canPlayerMove(@PathVariable int playerId,
                                                       @RequestParam double x,
                                                       @RequestParam double y) {
        boolean canMove = spatialService.canPlayerMoveTo(playerId, x, y);
        Optional<Flag> flagAtPosition = spatialService.findFlagForPoint(x, y);
        
        return ResponseEntity.ok(new CanMoveResponse(canMove, 
                flagAtPosition.map(Flag::getId).orElse(null),
                flagAtPosition.map(Flag::getName).orElse("Neutral Territory")));
    }
    
    /**
     * Interact with a resource
     */
    @PostMapping("/player/{playerId}/interact/resource/{resourceId}")
    public ResponseEntity<?> interactWithResource(@PathVariable int playerId, 
                                                @PathVariable int resourceId) {
        
        Optional<Player> playerOpt = playerRepository.findById(playerId);
        Optional<GameResource> resourceOpt = gameResourceRepository.findById(resourceId);
        
        if (!playerOpt.isPresent() || !resourceOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        
        Player player = playerOpt.get();
        GameResource resource = resourceOpt.get();
        
        // Check if player is in range (interaction range = 50 units)
        if (!spatialService.isPlayerInRangeOfResource(player, resource, 50.0)) {
            return ResponseEntity.badRequest()
                .body(new ErrorResponse("Not in range of resource"));
        }
        
        // Check if resource is active
        if (!resource.isActive()) {
            return ResponseEntity.badRequest()
                .body(new ErrorResponse("Resource is not active"));
        }
        
        // Reduce resource quantity
        resource.setQuantity(resource.getQuantity() - 1);
        if (resource.getQuantity() <= 0) {
            resource.setActive(false);
        }
        gameResourceRepository.save(resource);
        
        return ResponseEntity.ok(new InteractionResponse("Resource harvested successfully", 
                resource.getType(), resource.getQuantity()));
    }
    
    /**
     * Interact with an NPC
     */
    @PostMapping("/player/{playerId}/interact/npc/{npcId}")
    public ResponseEntity<?> interactWithNPC(@PathVariable int playerId, 
                                           @PathVariable int npcId) {
        
        Optional<Player> playerOpt = playerRepository.findById(playerId);
        Optional<NPC> npcOpt = npcRepository.findById(npcId);
        
        if (!playerOpt.isPresent() || !npcOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }
        
        Player player = playerOpt.get();
        NPC npc = npcOpt.get();
        
        // Check if player is in range (interaction range = 30 units)
        if (!spatialService.isPlayerInRangeOfNPC(player, npc, 30.0)) {
            return ResponseEntity.badRequest()
                .body(new ErrorResponse("Not in range of NPC"));
        }
        
        // Check if NPC is alive
        if (!npc.isAlive()) {
            return ResponseEntity.badRequest()
                .body(new ErrorResponse("NPC is not alive"));
        }
        
        // Simple combat - reduce NPC health
        npc.setHealth(npc.getHealth() - 20); // Player does 20 damage
        if (npc.getHealth() <= 0) {
            npc.setAlive(false);
        }
        npcRepository.save(npc);
        
        String result = npc.isAlive() ? "NPC damaged" : "NPC defeated";
        return ResponseEntity.ok(new InteractionResponse(result, 
                npc.getType(), npc.getHealth()));
    }
    
    // Response classes
    public static class MoveResponse {
        private String message;
        private double x;
        private double y;
        
        public MoveResponse(String message, double x, double y) {
            this.message = message;
            this.x = x;
            this.y = y;
        }
        
        // Getters
        public String getMessage() { return message; }
        public double getX() { return x; }
        public double getY() { return y; }
    }
    
    public static class ErrorResponse {
        private String error;
        
        public ErrorResponse(String error) {
            this.error = error;
        }
        
        public String getError() { return error; }
    }
    
    public static class FlagDetailsResponse {
        private Flag flag;
        private List<GameResource> resources;
        private List<NPC> npcs;
        
        public FlagDetailsResponse(Flag flag, List<GameResource> resources, List<NPC> npcs) {
            this.flag = flag;
            this.resources = resources;
            this.npcs = npcs;
        }
        
        // Getters
        public Flag getFlag() { return flag; }
        public List<GameResource> getResources() { return resources; }
        public List<NPC> getNpcs() { return npcs; }
    }
    
    public static class StateResponse {
        private long serverTime;
        private List<Flag> flags;
        private List<Player> players;
        private List<GameResource> resources;
        private List<NPC> npcs;

        public StateResponse(long serverTime, List<Flag> flags, List<Player> players,
                             List<GameResource> resources, List<NPC> npcs) {
            this.serverTime = serverTime;
            this.flags = flags;
            this.players = players;
            this.resources = resources;
            this.npcs = npcs;
        }
        public long getServerTime() { return serverTime; }
        public List<Flag> getFlags() { return flags; }
        public List<Player> getPlayers() { return players; }
        public List<GameResource> getResources() { return resources; }
        public List<NPC> getNpcs() { return npcs; }
    }

    public static class AreaEntitiesResponse {
        private List<GameResource> resources;
        private List<NPC> npcs;
        
        public AreaEntitiesResponse(List<GameResource> resources, List<NPC> npcs) {
            this.resources = resources;
            this.npcs = npcs;
        }
        
        // Getters
        public List<GameResource> getResources() { return resources; }
        public List<NPC> getNpcs() { return npcs; }
    }
    
    public static class CanMoveResponse {
        private boolean canMove;
        private Integer flagId;
        private String territory;
        
        public CanMoveResponse(boolean canMove, Integer flagId, String territory) {
            this.canMove = canMove;
            this.flagId = flagId;
            this.territory = territory;
        }
        
        // Getters
        public boolean isCanMove() { return canMove; }
        public Integer getFlagId() { return flagId; }
        public String getTerritory() { return territory; }
    }
    
    public static class InteractionResponse {
        private String message;
        private String entityType;
        private int remainingValue;
        
        public InteractionResponse(String message, String entityType, int remainingValue) {
            this.message = message;
            this.entityType = entityType;
            this.remainingValue = remainingValue;
        }
        
        // Getters
        public String getMessage() { return message; }
        public String getEntityType() { return entityType; }
        public int getRemainingValue() { return remainingValue; }
    }
}
