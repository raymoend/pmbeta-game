package com.pk.demo;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "strategic_flags")
public class StrategicFlag {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;

    private Integer ownerId;
    private String name;
    private String type; // outpost, shrine, etc.
    private double lon;
    private double lat;
    private String mapId;
    private Integer territoryId; // nullable
    private Instant createdAt;

    @PrePersist
    public void onCreate() { if (createdAt == null) createdAt = Instant.now(); }

    // Getters/Setters
    public int getId() { return id; }
    public void setId(int id) { this.id = id; }

    public Integer getOwnerId() { return ownerId; }
    public void setOwnerId(Integer ownerId) { this.ownerId = ownerId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getType() { return type; }
    public void setType(String type) { this.type = type; }

    public double getLon() { return lon; }
    public void setLon(double lon) { this.lon = lon; }

    public double getLat() { return lat; }
    public void setLat(double lat) { this.lat = lat; }

    public String getMapId() { return mapId; }
    public void setMapId(String mapId) { this.mapId = mapId; }

    public Integer getTerritoryId() { return territoryId; }
    public void setTerritoryId(Integer territoryId) { this.territoryId = territoryId; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}

