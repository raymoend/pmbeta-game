package com.pk.demo;

import jakarta.persistence.*;

@Entity
@Table(name = "players")
public class Player {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;

    private String name;
    // Legacy x/y retained temporarily; prefer lon/lat/mapId going forward
    private double x;
    private double y;
    @Column(nullable = true)
    private Integer flagId; // Nullable; players may be neutral

    // New fields for browser map compatibility
    private String characterId; // UUID-like string used by the client
    private Double lon;
    private Double lat;
    private String mapId; // e.g., "world"

    // Default constructor for JPA
    public Player() {}

    // Constructor
    public Player(String name, double x, double y) {
        this.name = name;
        this.x = x;
        this.y = y;
    }

    // Getters and Setters
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
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

    public String getCharacterId() { return characterId; }
    public void setCharacterId(String characterId) { this.characterId = characterId; }

    public Double getLon() { return lon; }
    public void setLon(Double lon) { this.lon = lon; }

    public Double getLat() { return lat; }
    public void setLat(Double lat) { this.lat = lat; }

    public String getMapId() { return mapId; }
    public void setMapId(String mapId) { this.mapId = mapId; }
}
