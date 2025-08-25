package com.pk.demo;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/game/territories")
@CrossOrigin(origins = "*")
public class TerritoryController {

    private final TerritoryRepository territoryRepository;

    public TerritoryController(TerritoryRepository territoryRepository) {
        this.territoryRepository = territoryRepository;
    }

    @PostMapping
    public ResponseEntity<?> create(@RequestBody CreateTerritoryRequest req) {
        if (req.name == null || req.name.isBlank()) {
            return ResponseEntity.badRequest().body(new Error("name required"));
        }
        if (req.radiusMeters == null || req.radiusMeters <= 0 || req.radiusMeters > 5000) {
            return ResponseEntity.badRequest().body(new Error("radiusMeters must be 1..5000"));
        }
        Territory t = new Territory();
        t.setName(req.name);
        t.setOwnerId(req.ownerId);
        t.setCenterLon(req.centerLon);
        t.setCenterLat(req.centerLat);
        t.setRadiusMeters(req.radiusMeters);
        return ResponseEntity.ok(territoryRepository.save(t));
    }

    @GetMapping("/nearby")
    public ResponseEntity<List<Territory>> nearby(@RequestParam double lon,
                                                  @RequestParam double lat,
                                                  @RequestParam double radiusMeters) {
        // Simple filter in memory (H2); replace with geo index if needed
        List<Territory> list = territoryRepository.findAll().stream()
                .filter(t -> haversineMeters(t.getCenterLat(), t.getCenterLon(), lat, lon) <= (radiusMeters + t.getRadiusMeters()))
                .collect(Collectors.toList());
        return ResponseEntity.ok(list);
    }

    private static double haversineMeters(double lat1, double lon1, double lat2, double lon2) {
        double R = 6371000.0; // meters
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat/2)*Math.sin(dLat/2) + Math.cos(Math.toRadians(lat1))*Math.cos(Math.toRadians(lat2))*Math.sin(dLon/2)*Math.sin(dLon/2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    public static class CreateTerritoryRequest {
        public String name;
        public Integer ownerId;
        public Double centerLon;
        public Double centerLat;
        public Double radiusMeters;
    }

    public static class Error {
        public String error;
        public Error(String e) { this.error = e; }
    }
}

