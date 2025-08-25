package com.pk.demo;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/game/flags")
@CrossOrigin(origins = "*")
public class FlagPlacementController {

    private final FlagRepository flagRepository;
    private final GameEventPublisher eventPublisher;

    public FlagPlacementController(FlagRepository flagRepository, GameEventPublisher eventPublisher) {
        this.flagRepository = flagRepository;
        this.eventPublisher = eventPublisher;
    }

    @PostMapping
    public ResponseEntity<?> placeFlag(@RequestBody PlaceFlagRequest req) {
        // Basic validation
        if (req.ownerId == null || req.name == null || req.name.isBlank()) {
            return ResponseEntity.badRequest().body(new Error("ownerId and name are required"));
        }
        if (req.radius == null || req.radius <= 0 || req.radius > 200) {
            return ResponseEntity.badRequest().body(new Error("radius must be between 1 and 200"));
        }

        // Simple spacing rule: reject if within 50 units of existing flag center
        List<Flag> tooClose = flagRepository.findAll().stream()
                .filter(f -> distance(f.getX(), f.getY(), req.x, req.y) < 50)
                .collect(Collectors.toList());
        if (!tooClose.isEmpty()) {
            return ResponseEntity.badRequest().body(new Error("Another flag is too close"));
        }

        Flag flag = new Flag();
        flag.setOwnerId(req.ownerId);
        flag.setName(req.name);
        flag.setX(req.x);
        flag.setY(req.y);
        flag.setRadius(req.radius);
        Flag saved = flagRepository.save(flag);

        // Publish event
        try { eventPublisher.publishFlagPlaced(saved); } catch (Exception ignored) {}

        return ResponseEntity.ok(saved);
    }

    @GetMapping("/nearby")
    public ResponseEntity<List<Flag>> nearby(@RequestParam double x,
                                             @RequestParam double y,
                                             @RequestParam double radius) {
        double minX = x - radius, maxX = x + radius;
        double minY = y - radius, maxY = y + radius;
        List<Flag> inBox = flagRepository.findAll().stream()
                .filter(f -> f.getX() >= minX && f.getX() <= maxX && f.getY() >= minY && f.getY() <= maxY)
                .filter(f -> distance(f.getX(), f.getY(), x, y) <= radius + f.getRadius())
                .collect(Collectors.toList());
        return ResponseEntity.ok(inBox);
    }

    private static double distance(double x1, double y1, double x2, double y2) {
        return Math.hypot(x2 - x1, y2 - y1);
    }

    public static class PlaceFlagRequest {
        public Integer ownerId;
        public String name;
        public Double x;
        public Double y;
        public Double radius;
    }

    public static class Error {
        public String error;
        public Error(String e) { this.error = e; }
    }
}

