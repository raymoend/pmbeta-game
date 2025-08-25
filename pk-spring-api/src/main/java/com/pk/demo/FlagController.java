package com.pk.demo;

import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/flags")
public class FlagController {

    private final FlagRepository flagRepository;

    public FlagController(FlagRepository flagRepository) {
        this.flagRepository = flagRepository;
    }

    @GetMapping
    public List<Flag> getAllFlags() {
        return flagRepository.findAll();
    }

    @PostMapping
    public Flag createFlag(@RequestBody Flag flag) {
        return flagRepository.save(flag);
    }

    @GetMapping("/{id}")
    public Flag getFlag(@PathVariable int id) {
        return flagRepository.findById(id).orElseThrow();
    }
}
