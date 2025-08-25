package com.pk.demo;

import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.scene.control.Tooltip;
import javafx.scene.input.MouseButton;
import javafx.scene.layout.Pane;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;
import javafx.scene.shape.Rectangle;
import javafx.stage.Stage;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import javafx.application.Platform;
import javafx.scene.Node;

/**
 * JavaFX Tap-to-Move Client for Parallel Kingdom Style Game
 * 
 * Features:
 * - Click anywhere on the map to move the player
 * - Server handles movement validation and flag influence checking
 * - Real-time flag visualization with influence radius
 * - Player position updates from server
 */
public class TapToMoveClient extends Application {

    // Data classes that match the Spring Boot API
    static class Flag {
        int id, ownerId;
        double x, y, radius;
        
        // Default constructor for JSON
        public Flag() {}
    }

    static class Player {
        int id;
        String name;
        double x, y;
        
        // Default constructor for JSON
        public Player() {}
    }

    static class GameResource {
        int id, flagId, quantity;
        double x, y;
        String type;
        boolean isActive;
        long spawnTime;
        
        // Default constructor for JSON
        public GameResource() {}
    }
    
    static class NPC {
        int id, flagId, health, maxHealth;
        double x, y;
        String type, aggressionLevel;
        boolean isAlive;
        long spawnTime;
        
        // Default constructor for JSON
        public NPC() {}
    }
    
    static class CanMoveResponse {
        boolean canMove;
        Integer flagId;
        String territory;
        
        // Default constructor for JSON
        public CanMoveResponse() {}
    }
    
    static class FlagDetailsResponse {
        Flag flag;
        List<GameResource> resources;
        List<NPC> npcs;
        
        // Default constructor for JSON
        public FlagDetailsResponse() {}
    }
    
    static class AreaEntitiesResponse {
        List<GameResource> resources;
        List<NPC> npcs;
        
        // Default constructor for JSON
        public AreaEntitiesResponse() {}
    }
    
    static class GameMoveResponse {
        String message;
        double x, y;
        
        // Default constructor for JSON
        public GameMoveResponse() {}
    }
    
    static class InteractionResponse {
        String message;
        String entityType;
        int remainingValue;
        
        // Default constructor for JSON
        public InteractionResponse() {}
    }

    // UI Components
    private Pane root;
    private Circle playerCircle;
    private final Gson gson = new Gson();
    private final String BASE_URL = "http://localhost:8080/api";
    private VBox infoPanel;
    private Label statusLabel;
    private ScheduledExecutorService scheduler;
    
    // Game State
    private int currentPlayerId = 1; // We'll control player 1
    private List<Flag> allFlags = new ArrayList<>();
    private List<Circle> flagCircles = new ArrayList<>();
    private List<Node> resourceNodes = new ArrayList<>();
    private List<Node> npcNodes = new ArrayList<>();
    private List<Player> allPlayers = new ArrayList<>();
    private List<Circle> playerCircles = new ArrayList<>();

    /**
     * Fetch all flags from the server
     */
    private List<Flag> fetchFlags() throws Exception {
        URL url = new URL(BASE_URL + "/game/flags");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, new TypeToken<List<Flag>>(){}.getType());
        }
    }

    /**
     * Send a movement request to the server using new Game API
     */
    private GameMoveResponse movePlayer(int playerId, double x, double y) throws Exception {
        String urlStr = BASE_URL + "/game/player/" + playerId + "/move?x=" + x + "&y=" + y;
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, GameMoveResponse.class);
        }
    }
    
    /**
     * Check if movement is allowed
     */
    private CanMoveResponse canPlayerMove(int playerId, double x, double y) throws Exception {
        String urlStr = BASE_URL + "/game/player/" + playerId + "/can-move?x=" + x + "&y=" + y;
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, CanMoveResponse.class);
        }
    }

    /**
     * Get current player info from the server
     */
    private Player getPlayer(int playerId) throws Exception {
        URL url = new URL(BASE_URL + "/game/player/" + playerId);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, Player.class);
        }
    }
    
    /**
     * Get all players from server
     */
    private List<Player> fetchAllPlayers() throws Exception {
        URL url = new URL(BASE_URL + "/game/players");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, new TypeToken<List<Player>>(){}.getType());
        }
    }
    
    /**
     * Get entities in an area
     */
    private AreaEntitiesResponse getEntitiesInArea(double minX, double maxX, double minY, double maxY) throws Exception {
        String urlStr = BASE_URL + "/game/entities?minX=" + minX + "&maxX=" + maxX + "&minY=" + minY + "&maxY=" + maxY;
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, AreaEntitiesResponse.class);
        }
    }
    
    /**
     * Interact with a resource
     */
    private InteractionResponse interactWithResource(int playerId, int resourceId) throws Exception {
        String urlStr = BASE_URL + "/game/player/" + playerId + "/interact/resource/" + resourceId;
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, InteractionResponse.class);
        }
    }
    
    /**
     * Interact with an NPC
     */
    private InteractionResponse interactWithNPC(int playerId, int npcId) throws Exception {
        String urlStr = BASE_URL + "/game/player/" + playerId + "/interact/npc/" + npcId;
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");

        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream())) {
            return gson.fromJson(reader, InteractionResponse.class);
        }
    }

    @Override
    public void start(Stage stage) {
        root = new Pane();
        root.setPrefSize(800, 600);
        
        // Create info panel
        infoPanel = new VBox();
        infoPanel.setLayoutX(610);
        infoPanel.setLayoutY(10);
        infoPanel.setPrefSize(180, 580);
        infoPanel.setStyle("-fx-background-color: rgba(0,0,0,0.8); -fx-padding: 10;");
        
        statusLabel = new Label("Loading...");
        statusLabel.setTextFill(Color.WHITE);
        infoPanel.getChildren().add(statusLabel);
        root.getChildren().add(infoPanel);
        
        try {
            // Load initial game state
            loadFlags();
            loadPlayer();
            loadAllPlayers();
            loadEntities();
            
            updateStatusLabel("Game loaded successfully!");
            
        } catch (Exception e) {
            System.err.println("Failed to load initial game state: " + e.getMessage());
            updateStatusLabel("Server connection failed!");
            // Create a default player position if server is not available
            playerCircle = new Circle(300, 300, 10, Color.BLUE);
            root.getChildren().add(playerCircle);
        }

        // Handle tap-to-move and interactions
        root.setOnMouseClicked(event -> {
            if (event.getX() > 600) return; // Don't handle clicks on info panel
            
            double targetX = event.getX();
            double targetY = event.getY();

            // Check for entity interactions first (right-click or close proximity)
            if (event.getButton() == MouseButton.SECONDARY) {
                handleEntityInteraction(targetX, targetY);
                return;
            }

            // Regular movement (left-click)
            try {
                // First check if movement is allowed
                CanMoveResponse canMoveResp = canPlayerMove(currentPlayerId, targetX, targetY);
                
                if (!canMoveResp.canMove) {
                    System.out.println("Movement blocked! Territory: " + canMoveResp.territory);
                    updateStatusLabel("Movement blocked: " + canMoveResp.territory);
                    return;
                }
                
                System.out.println("Moving player to (" + targetX + ", " + targetY + ") in " + canMoveResp.territory);
                GameMoveResponse response = movePlayer(currentPlayerId, targetX, targetY);
                
                // Update player position by fetching latest player data
                Player updatedPlayer = getPlayer(currentPlayerId);
                updatePlayerPosition(updatedPlayer);
                
                updateStatusLabel("Moved to " + canMoveResp.territory);
                
            } catch (Exception ex) {
                System.err.println("Movement failed: " + ex.getMessage());
                updateStatusLabel("Movement failed: " + ex.getMessage());
                // Fallback: move player locally if server is unavailable
                if (playerCircle != null) {
                    playerCircle.setCenterX(targetX);
                    playerCircle.setCenterY(targetY);
                }
            }
        });
        
        // Start periodic updates
        startPeriodicUpdates();

        Scene scene = new Scene(root, 800, 600);
        scene.setFill(Color.DARKGREEN); // Game map background
        
        stage.setTitle("Parallel Kingdom - Enhanced Client");
        stage.setScene(scene);
        stage.show();
        
        System.out.println("=== Enhanced Parallel Kingdom Client Started ===");
        System.out.println("Left-click: Move player");
        System.out.println("Right-click: Interact with entities");
        System.out.println("Server: " + BASE_URL);
    }

    /**
     * Load and render all flags from the server
     */
    private void loadFlags() throws Exception {
        allFlags = fetchFlags();
        
        // Clear existing flag visuals
        for (Circle flagCircle : flagCircles) {
            root.getChildren().remove(flagCircle);
        }
        flagCircles.clear();

        // Render each flag as a semi-transparent circle
        for (Flag flag : allFlags) {
            // Create influence radius circle
            Circle flagCircle = new Circle(flag.x, flag.y, flag.radius);
            
            // Color based on ownership
            if (flag.ownerId == currentPlayerId) {
                flagCircle.setFill(Color.color(0, 1, 0, 0.3)); // Green for owned
                flagCircle.setStroke(Color.GREEN);
            } else {
                flagCircle.setFill(Color.color(1, 0, 0, 0.3)); // Red for enemy
                flagCircle.setStroke(Color.RED);
            }
            
            flagCircle.setStrokeWidth(2);
            
            root.getChildren().add(flagCircle);
            flagCircles.add(flagCircle);
        }
        
        System.out.println("Loaded " + allFlags.size() + " flags from server");
    }

    /**
     * Load and render the current player
     */
    private void loadPlayer() throws Exception {
        Player player = getPlayer(currentPlayerId);
        
        if (playerCircle != null) {
            root.getChildren().remove(playerCircle);
        }
        
        // Create player circle
        playerCircle = new Circle(player.x, player.y, 8, Color.BLUE);
        playerCircle.setStroke(Color.DARKBLUE);
        playerCircle.setStrokeWidth(2);
        
        root.getChildren().add(playerCircle);
        
        System.out.println("Player '" + player.name + "' loaded at (" + player.x + ", " + player.y + ")");
    }

    /**
     * Update player position on screen
     */
    private void updatePlayerPosition(Player player) {
        if (playerCircle != null) {
            playerCircle.setCenterX(player.x);
            playerCircle.setCenterY(player.y);
        }
        
        System.out.println("Player '" + player.name + "' moved to (" + player.x + ", " + player.y + ")");
    }

    /**
     * Load and render all players
     */
    private void loadAllPlayers() throws Exception {
        allPlayers = fetchAllPlayers();
        
        // Clear existing player visuals (except current player)
        for (Circle playerCircle : playerCircles) {
            root.getChildren().remove(playerCircle);
        }
        playerCircles.clear();
        
        // Render other players
        for (Player player : allPlayers) {
            if (player.id == currentPlayerId) continue; // Skip current player
            
            Circle otherPlayerCircle = new Circle(player.x, player.y, 6, Color.YELLOW);
            otherPlayerCircle.setStroke(Color.ORANGE);
            otherPlayerCircle.setStrokeWidth(1);
            
            Tooltip.install(otherPlayerCircle, new Tooltip("Player: " + player.name));
            
            root.getChildren().add(otherPlayerCircle);
            playerCircles.add(otherPlayerCircle);
        }
        
        System.out.println("Loaded " + (allPlayers.size() - 1) + " other players");
    }
    
    /**
     * Load and render entities (resources and NPCs)
     */
    private void loadEntities() throws Exception {
        // Clear existing entity visuals
        for (Node node : resourceNodes) {
            root.getChildren().remove(node);
        }
        for (Node node : npcNodes) {
            root.getChildren().remove(node);
        }
        resourceNodes.clear();
        npcNodes.clear();
        
        // Load entities in visible area
        AreaEntitiesResponse entities = getEntitiesInArea(0, 600, 0, 600);
        
        // Render resources
        for (GameResource resource : entities.resources) {
            if (!resource.isActive) continue;
            
            Color resourceColor = getResourceColor(resource.type);
            Rectangle resourceRect = new Rectangle(resource.x - 3, resource.y - 3, 6, 6);
            resourceRect.setFill(resourceColor);
            resourceRect.setStroke(Color.BLACK);
            
            Tooltip.install(resourceRect, new Tooltip(
                resource.type + " (" + resource.quantity + ")\nRight-click to harvest"));
            
            root.getChildren().add(resourceRect);
            resourceNodes.add(resourceRect);
        }
        
        // Render NPCs
        for (NPC npc : entities.npcs) {
            if (!npc.isAlive) continue;
            
            Color npcColor = getNPCColor(npc.type, npc.aggressionLevel);
            Circle npcCircle = new Circle(npc.x, npc.y, 5, npcColor);
            npcCircle.setStroke(Color.BLACK);
            
            Tooltip.install(npcCircle, new Tooltip(
                npc.type + " (" + npc.health + "/" + npc.maxHealth + ")\n" +
                "Aggression: " + npc.aggressionLevel + "\nRight-click to attack"));
            
            root.getChildren().add(npcCircle);
            npcNodes.add(npcCircle);
        }
        
        System.out.println("Loaded " + entities.resources.size() + " resources and " + entities.npcs.size() + " NPCs");
    }
    
    /**
     * Handle entity interactions
     */
    private void handleEntityInteraction(double x, double y) {
        try {
            // Check for nearby entities
            AreaEntitiesResponse entities = getEntitiesInArea(x - 20, x + 20, y - 20, y + 20);
            
            // Find closest resource
            GameResource closestResource = null;
            double closestResourceDist = Double.MAX_VALUE;
            for (GameResource resource : entities.resources) {
                if (!resource.isActive) continue;
                double dist = Math.sqrt(Math.pow(x - resource.x, 2) + Math.pow(y - resource.y, 2));
                if (dist < closestResourceDist && dist < 20) {
                    closestResourceDist = dist;
                    closestResource = resource;
                }
            }
            
            // Find closest NPC
            NPC closestNPC = null;
            double closestNPCDist = Double.MAX_VALUE;
            for (NPC npc : entities.npcs) {
                if (!npc.isAlive) continue;
                double dist = Math.sqrt(Math.pow(x - npc.x, 2) + Math.pow(y - npc.y, 2));
                if (dist < closestNPCDist && dist < 20) {
                    closestNPCDist = dist;
                    closestNPC = npc;
                }
            }
            
            // Interact with closest entity
            if (closestResource != null && closestResourceDist < closestNPCDist) {
                InteractionResponse response = interactWithResource(currentPlayerId, closestResource.id);
                System.out.println("Resource interaction: " + response.message);
                updateStatusLabel("Harvested " + response.entityType);
                
                // Refresh entities
                Platform.runLater(() -> {
                    try {
                        loadEntities();
                    } catch (Exception e) {
                        System.err.println("Failed to refresh entities: " + e.getMessage());
                    }
                });
                
            } else if (closestNPC != null) {
                InteractionResponse response = interactWithNPC(currentPlayerId, closestNPC.id);
                System.out.println("NPC interaction: " + response.message);
                updateStatusLabel("Attacked " + response.entityType);
                
                // Refresh entities
                Platform.runLater(() -> {
                    try {
                        loadEntities();
                    } catch (Exception e) {
                        System.err.println("Failed to refresh entities: " + e.getMessage());
                    }
                });
                
            } else {
                System.out.println("No entities nearby to interact with");
                updateStatusLabel("No entities nearby");
            }
            
        } catch (Exception ex) {
            System.err.println("Interaction failed: " + ex.getMessage());
            updateStatusLabel("Interaction failed");
        }
    }
    
    /**
     * Start periodic updates
     */
    private void startPeriodicUpdates() {
        scheduler = Executors.newScheduledThreadPool(1);
        
        // Update game state every 5 seconds
        scheduler.scheduleAtFixedRate(() -> {
            Platform.runLater(() -> {
                try {
                    loadAllPlayers();
                    loadEntities();
                } catch (Exception e) {
                    System.err.println("Periodic update failed: " + e.getMessage());
                }
            });
        }, 5, 5, TimeUnit.SECONDS);
    }
    
    /**
     * Update status label
     */
    private void updateStatusLabel(String message) {
        Platform.runLater(() -> {
            statusLabel.setText("Status: " + message);
        });
    }
    
    /**
     * Get color for resource type
     */
    private Color getResourceColor(String type) {
        switch (type.toLowerCase()) {
            case "tree": return Color.BROWN;
            case "mine": return Color.GRAY;
            case "herb": return Color.LIGHTGREEN;
            case "water": return Color.LIGHTBLUE;
            default: return Color.PURPLE;
        }
    }
    
    /**
     * Get color for NPC type and aggression
     */
    private Color getNPCColor(String type, String aggression) {
        Color baseColor;
        switch (type.toLowerCase()) {
            case "troll": baseColor = Color.DARKGREEN; break;
            case "alien": baseColor = Color.PURPLE; break;
            case "ghost": baseColor = Color.LIGHTGRAY; break;
            default: baseColor = Color.RED; break;
        }
        
        // Adjust intensity based on aggression
        if (aggression == null) return baseColor;
        switch (aggression.toLowerCase()) {
            case "very_aggressive": return baseColor.darker();
            case "aggressive": return baseColor;
            case "neutral": return baseColor.brighter();
            case "passive": return baseColor.brighter().brighter();
            default: return baseColor;
        }
    }
    
    @Override
    public void stop() throws Exception {
        if (scheduler != null) {
            scheduler.shutdown();
        }
        super.stop();
    }

    public static void main(String[] args) {
        System.out.println("Starting Parallel Kingdom Tap-to-Move Client...");
        System.out.println("Make sure the Spring Boot server is running on http://localhost:8080");
        
        launch(args);
    }
}

/*
 * INSTRUCTIONS TO RUN:
 * 
 * 1. Start the Spring Boot server first:
 *    mvn -f "C:\\Users\\Truck\\pmbeta-web\\pk-spring-api\\pom.xml" spring-boot:run
 * 
 * 2. Run the JavaFX client via Maven:
 *    mvn -f "C:\\Users\\Truck\\pmbeta-web\\pk-spring-api\\pom.xml" exec:java -Dexec.mainClass=com.pk.demo.TapToMoveClient
 * 
 */
