package com.pk.demo;

import jakarta.persistence.*;

@Entity
@Table(name = "game_resources")
public class GameResource {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;
    
    private String type; // "tree", "mine", "herbs", etc.
    private String name; // Display name like "Oak Tree", "Iron Mine"
    private double x;
    private double y;
    @Column(nullable = true)
    private Integer flagId; // Which flag this resource belongs to (nullable for neutral)
    private boolean isActive; // Whether the resource can be harvested
    private int quantity; // How much resource is available
    private long spawnTime; // When this resource was spawned
    
    // Default constructor for JPA
    public GameResource() {}
    
    // Constructor
    public GameResource(String type, String name, double x, double y, int flagId) {
        this.type = type;
        this.name = name;
        this.x = x;
        this.y = y;
        this.flagId = flagId;
        this.isActive = true;
        this.quantity = getDefaultQuantity();
        this.spawnTime = System.currentTimeMillis();
    }
    
    /**
     * Get default quantity based on resource type
     */
    private int getDefaultQuantity() {
        return switch (type) {
            case "tree" -> 50;
            case "mine" -> 100;
            case "herbs" -> 25;
            default -> 10;
        };
    }
    
    /**
     * Check if this resource is within a flag's influence
     */
    public boolean isInFlag(Flag flag) {
        return flag.inInfluence(this.x, this.y);
    }
    
    /**
     * Harvest some quantity from this resource
     */
    public int harvest(int amount) {
        if (!isActive || quantity <= 0) {
            return 0;
        }
        
        int harvested = Math.min(amount, quantity);
        quantity -= harvested;
        
        if (quantity <= 0) {
            isActive = false;
        }
        
        return harvested;
    }
    
    // Getters and Setters
    public int getId() {
        return id;
    }
    
    public void setId(int id) {
        this.id = id;
    }
    
    public String getType() {
        return type;
    }
    
    public void setType(String type) {
        this.type = type;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public double getX() {
        return x;
    }
    
    public void setX(double x) {
        this.x = x;
    }
    
    public double getY() {
        return y;
    }
    
    public void setY(double y) {
        this.y = y;
    }
    
    public Integer getFlagId() {
        return flagId;
    }
    
    public void setFlagId(Integer flagId) {
        this.flagId = flagId;
    }
    
    public boolean isActive() {
        return isActive;
    }
    
    public void setActive(boolean active) {
        isActive = active;
    }
    
    public int getQuantity() {
        return quantity;
    }
    
    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }
    
    public long getSpawnTime() {
        return spawnTime;
    }
    
    public void setSpawnTime(long spawnTime) {
        this.spawnTime = spawnTime;
    }
}
