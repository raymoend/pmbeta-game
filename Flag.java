import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.input.MouseEvent;
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import javafx.stage.Stage;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Clean Flag System - Simple transparent circles like the request example
 * No visual clutter, just clean transparent circles with stroke
 * Equivalent to the JavaScript implementation
 */
public class FlagSystem extends Application {
    
    // Flag class - Simple object with position and radius
    public static class Flag {
        private int id;
        private double x, y;  // Position coordinates
        private double radius; // Radius in pixels
        private int ownerId;
        private boolean isOwned;
        
        public Flag(int id, double x, double y, double radius, int ownerId, boolean isOwned) {
            this.id = id;
            this.x = x;
            this.y = y;
            this.radius = radius;
            this.ownerId = ownerId;
            this.isOwned = isOwned;
        }
        
        /**
         * Check if a player's position is inside the flag's radius
         * @param playerX Player's X coordinate
         * @param playerY Player's Y coordinate
         * @return True if player is inside the flag radius
         */
        public boolean isPlayerInside(double playerX, double playerY) {
            double distance = Math.sqrt(Math.pow(playerX - this.x, 2) + Math.pow(playerY - this.y, 2));
            return distance <= this.radius;
        }
        
        /**
         * Render the flag as a transparent circle with stroke
         * @param gc GraphicsContext to draw on
         */
        public void render(GraphicsContext gc) {
            // Set colors based on ownership
            if (isOwned) {
                gc.setStroke(Color.rgb(76, 175, 80));        // Green stroke for owned
                gc.setFill(Color.rgb(76, 175, 80, 0.2));     // Semi-transparent green fill
            } else {
                gc.setStroke(Color.rgb(244, 67, 54));        // Red stroke for enemy
                gc.setFill(Color.rgb(244, 67, 54, 0.2));     // Semi-transparent red fill
            }
            
            gc.setLineWidth(2);
            
            // Draw the transparent circle
            gc.fillOval(x - radius, y - radius, radius * 2, radius * 2);
            gc.strokeOval(x - radius, y - radius, radius * 2, radius * 2);
        }
        
        // Getters
        public int getId() { return id; }
        public double getX() { return x; }
        public double getY() { return y; }
        public double getRadius() { return radius; }
        public int getOwnerId() { return ownerId; }
        public boolean isOwned() { return isOwned; }
    }
    
    // Database manager for flags
    public static class FlagDatabase {
        private Connection connection;
        
        public FlagDatabase() {
            try {
                // Initialize database connection (SQLite example)
                connection = DriverManager.getConnection("jdbc:sqlite:flags.db");
                createTable();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }
        
        private void createTable() throws SQLException {
            String sql = """
                CREATE TABLE IF NOT EXISTS flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    radius REAL NOT NULL,
                    owner_id INTEGER NOT NULL
                )
            """;
            connection.createStatement().execute(sql);
        }
        
        /**
         * Load all flags from database into Java objects
         * @return List of Flag objects
         */
        public List<Flag> loadFlags(int currentPlayerId) {
            List<Flag> flags = new ArrayList<>();
            String sql = "SELECT id, x, y, radius, owner_id FROM flags";
            
            try (Statement stmt = connection.createStatement();
                 ResultSet rs = stmt.executeQuery(sql)) {
                
                while (rs.next()) {
                    Flag flag = new Flag(
                        rs.getInt("id"),
                        rs.getDouble("x"),
                        rs.getDouble("y"),
                        rs.getDouble("radius"),
                        rs.getInt("owner_id"),
                        rs.getInt("owner_id") == currentPlayerId  // Check ownership
                    );
                    flags.add(flag);
                }
                
            } catch (SQLException e) {
                e.printStackTrace();
            }
            
            return flags;
        }
        
        /**
         * Save a new flag to the database
         * @param x X coordinate
         * @param y Y coordinate
         * @param radius Flag radius
         * @param ownerId Owner player ID
         * @return Generated flag ID, or -1 if failed
         */
        public int saveFlag(double x, double y, double radius, int ownerId) {
            String sql = "INSERT INTO flags (x, y, radius, owner_id) VALUES (?, ?, ?, ?)";
            
            try (PreparedStatement stmt = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
                stmt.setDouble(1, x);
                stmt.setDouble(2, y);
                stmt.setDouble(3, radius);
                stmt.setInt(4, ownerId);
                
                int rowsAffected = stmt.executeUpdate();
                if (rowsAffected > 0) {
                    ResultSet rs = stmt.getGeneratedKeys();
                    if (rs.next()) {
                        return rs.getInt(1);
                    }
                }
            } catch (SQLException e) {
                e.printStackTrace();
            }
            
            return -1;
        }
    }
    
    // Main game class
    private Canvas canvas;
    private GraphicsContext gc;
    private List<Flag> flags;
    private FlagDatabase database;
    private double playerX = 400, playerY = 300; // Player position
    private int currentPlayerId = 1; // Current player ID
    
    @Override
    public void start(Stage primaryStage) {
        // Initialize database and load flags
        database = new FlagDatabase();
        flags = database.loadFlags(currentPlayerId);
        
        // Create canvas
        canvas = new Canvas(800, 600);
        gc = canvas.getGraphicsContext2D();
        
        // Setup mouse click handler for flag placement
        canvas.setOnMouseClicked(this::handleMouseClick);
        
        // Create scene
        Pane root = new Pane();
        root.getChildren().add(canvas);
        Scene scene = new Scene(root, 800, 600);
        
        primaryStage.setTitle("Clean Flag System");
        primaryStage.setScene(scene);
        primaryStage.show();
        
        // Start render loop
        render();
    }
    
    private void handleMouseClick(MouseEvent event) {
        double clickX = event.getX();
        double clickY = event.getY();
        
        // Check if clicking on existing flag
        for (Flag flag : flags) {
            if (flag.isPlayerInside(clickX, clickY)) {
                handleFlagClick(flag);
                return;
            }
        }
        
        // Right-click to place new flag
        if (event.isSecondaryButtonDown()) {
            placeNewFlag(clickX, clickY);
        }
    }
    
    private void handleFlagClick(Flag flag) {
        // Check if player is within interaction range
        if (flag.isPlayerInside(playerX, playerY)) {
            if (flag.isOwned()) {
                System.out.println("Collecting revenue from flag " + flag.getId());
                // Implement collect revenue logic
            } else {
                System.out.println("Attacking flag " + flag.getId());
                // Implement attack logic
            }
        } else {
            System.out.println("You must be within " + flag.getRadius() + " units to interact with this flag");
        }
    }
    
    private void placeNewFlag(double x, double y) {
        // Check minimum distance from other flags (200 units)
        for (Flag existingFlag : flags) {
            double distance = Math.sqrt(Math.pow(x - existingFlag.getX(), 2) + Math.pow(y - existingFlag.getY(), 2));
            if (distance < 200) {
                System.out.println("Flags must be at least 200 units apart");
                return;
            }
        }
        
        // Save new flag to database
        int newFlagId = database.saveFlag(x, y, 100, currentPlayerId); // Default radius 100
        
        if (newFlagId != -1) {
            // Add to local list
            Flag newFlag = new Flag(newFlagId, x, y, 100, currentPlayerId, true);
            flags.add(newFlag);
            System.out.println("Flag placed at (" + x + ", " + y + ")");
            render(); // Re-render
        }
    }
    
    private void render() {
        // Clear canvas
        gc.clearRect(0, 0, canvas.getWidth(), canvas.getHeight());
        
        // Set background
        gc.setFill(Color.BLACK);
        gc.fillRect(0, 0, canvas.getWidth(), canvas.getHeight());
        
        // Render all flags
        for (Flag flag : flags) {
            flag.render(gc);
        }
        
        // Render player
        gc.setFill(Color.BLUE);
        gc.fillOval(playerX - 8, playerY - 8, 16, 16);
        
        // Draw simple UI info
        gc.setFill(Color.WHITE);
        gc.fillText("Player: (" + (int)playerX + ", " + (int)playerY + ")", 10, 20);
        gc.fillText("Flags: " + flags.size(), 10, 40);
        gc.fillText("Right-click to place flag, Left-click flag to interact", 10, canvas.getHeight() - 20);
    }
    
    public static void main(String[] args) {
        launch(args);
    }
}

/**
 * This Java implementation demonstrates the clean flag system approach:
 * 
 * 1. Flag objects with (x, y) position and radius
 * 2. Transparent circle rendering (semi-transparent fill + stroke)
 * 3. Player position checking logic (isPlayerInside method)
 * 4. SQL database storage (flags table with id, x, y, radius, owner_id)
 * 5. Loading flags from database into Java objects
 * 6. Simple interaction system
 * 
 * The JavaScript implementation mirrors this approach exactly:
 * - Clean transparent circles instead of complex visual elements
 * - Simple position-based interaction logic
 * - Database-backed flag storage
 * - Minimal UI clutter
 */
