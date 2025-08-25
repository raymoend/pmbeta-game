package com.pk.demo;

import jakarta.persistence.*;

@Entity
@Table(name = "flags")
public class Flag {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;

    private int ownerId;
    private String name;
    private double x;
    private double y;
    private double radius;

    // Default constructor for JPA
    public Flag() {}

    // Constructor
    public Flag(int ownerId, double x, double y, double radius) {
        this.ownerId = ownerId;
        this.x = x;
        this.y = y;
        this.radius = radius;
    }

    /**
     * Check if a point is within this flag's influence radius
     */
    public boolean inInfluence(double pointX, double pointY) {
        double distance = Math.sqrt(Math.pow(pointX - this.x, 2) + Math.pow(pointY - this.y, 2));
        return distance <= this.radius;
    }

    // Getters and Setters
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public int getOwnerId() {
        return ownerId;
    }

    public void setOwnerId(int ownerId) {
        this.ownerId = ownerId;
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

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }
}
