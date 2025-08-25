package com.pk.demo;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/players")
public class PlayerController {
    
    private final PlayerRepository playerRepository;
    private final FlagRepository flagRepository;

    public PlayerController(PlayerRepository playerRepository, FlagRepository flagRepository) {
        this.playerRepository = playerRepository;
        this.flagRepository = flagRepository;
    }

    @PostMapping("/{id}/move")
    public Map<String, Object> movePlayer(@PathVariable int id,
                                          @RequestParam double x,
                                          @RequestParam double y) {
        Player player = playerRepository.findById(id).orElseThrow();
        player.setX(x);
        player.setY(y);
        playerRepository.save(player);

        // Check which flags the player is now influencing
        List<Flag> influencingFlags = new ArrayList<>();
        for (Flag flag : flagRepository.findAll()) {
            if (flag.inInfluence(x, y)) {
                influencingFlags.add(flag);
            }
        }

        // Return response
        Map<String, Object> response = new HashMap<>();
        response.put("player", player);
        response.put("influencingFlags", influencingFlags);
        return response;
    }

    @GetMapping
    public List<Player> getAllPlayers() {
        return playerRepository.findAll();
    }

    @PostMapping
    public Player createPlayer(@RequestBody Player player) {
        return playerRepository.save(player);
    }

    @GetMapping("/{id}")
    public Player getPlayer(@PathVariable int id) {
        return playerRepository.findById(id).orElseThrow();
    }
}
