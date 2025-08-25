package com.pk.demo;

import jakarta.persistence.*;

@Entity
@Table(name = "npcs")
public class NPC {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;
    
    private String type; // "troll", "alien", "ghost", etc.
    private String name; // Display name like "Forest Troll", "Gray Alien"
    private double x;
    private double y;
    @Column(nullable = true)
    private Integer flagId; // Which flag this NPC belongs to (nullable for neutral)
    private boolean isAlive; // Whether the NPC is alive
    private int health; // Current health
    private int maxHealth; // Maximum health
    private int level; // NPC level for combat
    private long spawnTime; // When this NPC was spawned
    private boolean isAggressive; // Whether NPC attacks players
    private String aggressionLevel; // descriptive aggression level
    
    // Default constructor for JPA
    public NPC() {}
    
    // Constructor
    public NPC(String type, String name, double x, double y, Integer flagId, int level) {
        this.type = type;
        this.name = name;
        this.x = x;
        this.y = y;
        this.flagId = flagId;
        this.level = level;
        this.maxHealth = getDefaultHealth();
        this.health = this.maxHealth;
        this.isAlive = true;
        this.spawnTime = System.currentTimeMillis();
        this.isAggressive = getDefaultAggression();
        this.aggressionLevel = this.isAggressive ? "aggressive" : "neutral";
    }
    
    /**
     * Get default health based on NPC type and level
     */
    private int getDefaultHealth() {
        int baseHealth = switch (type) {
            case "troll" -> 100;
            case "alien" -> 80;
            case "ghost" -> 60;
            case "dragon" -> 200;
            default -> 50;
        };
        return baseHealth + (level * 20);
    }
    
    /**
     * Get default aggression based on NPC type
     */
    private boolean getDefaultAggression() {
        return switch (type) {
            case "troll", "dragon" -> true;
            case "alien" -> true;
            case "ghost" -> false; // Ghosts are passive
            default -> false;
        };
    }
    
    /**
     * Check if this NPC is within a flag's influence
     */
    public boolean isInFlag(Flag flag) {
        return flag.inInfluence(this.x, this.y);
    }
    
    /**
     * Deal damage to this NPC
     */
    public boolean takeDamage(int damage) {
        if (!isAlive) return false;
        
        health -= damage;
        if (health <= 0) {
            health = 0;
            isAlive = false;
            return true; // NPC died
        }
        return false; // NPC still alive
    }
    
    /**
     * Calculate distance to a point
     */
    public double distanceTo(double targetX, double targetY) {
        return Math.sqrt(Math.pow(targetX - this.x, 2) + Math.pow(targetY - this.y, 2));
    }
    
    /**
     * Move the NPC (for AI movement)
     */
    public void moveTo(double newX, double newY) {
        this.x = newX;
        this.y = newY;
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
    
    public boolean isAlive() {
        return isAlive;
    }
    
    public void setAlive(boolean alive) {
        isAlive = alive;
    }
    
    public int getHealth() {
        return health;
    }
    
    public void setHealth(int health) {
        this.health = health;
    }
    
    public int getMaxHealth() {
        return maxHealth;
    }
    
    public void setMaxHealth(int maxHealth) {
        this.maxHealth = maxHealth;
    }
    
    public int getLevel() {
        return level;
    }
    
    public void setLevel(int level) {
        this.level = level;
    }
    
    public long getSpawnTime() {
        return spawnTime;
    }
    
    public void setSpawnTime(long spawnTime) {
        this.spawnTime = spawnTime;
    }
    
    public boolean isAggressive() {
        return isAggressive;
    }
    
    public void setAggressive(boolean aggressive) {
        isAggressive = aggressive;
    }

    public String getAggressionLevel() {
        return aggressionLevel;
    }

    public void setAggressionLevel(String aggressionLevel) {
        this.aggressionLevel = aggressionLevel;
    }
}
