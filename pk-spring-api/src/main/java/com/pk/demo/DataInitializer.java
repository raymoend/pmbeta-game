package com.pk.demo;

import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements CommandLineRunner {

    private final PlayerRepository playerRepository;
    private final FlagRepository flagRepository;
    private final GameResourceRepository gameResourceRepository;
    private final NPCRepository npcRepository;

    public DataInitializer(PlayerRepository playerRepository, 
                          FlagRepository flagRepository,
                          GameResourceRepository gameResourceRepository,
                          NPCRepository npcRepository) {
        this.playerRepository = playerRepository;
        this.flagRepository = flagRepository;
        this.gameResourceRepository = gameResourceRepository;
        this.npcRepository = npcRepository;
    }

    @Override
    public void run(String... args) throws Exception {
        
        // Clear existing data for fresh start
        System.out.println("Initializing fresh game data...");
        
        // Create test flags first
        Flag flag1 = new Flag(99, 100, 200, 50); // Enemy flag
        flag1.setName("Enemy Territory");
        
        Flag flag2 = new Flag(1, 250, 100, 75);  // Alice's flag
        flag2.setName("Alice's Kingdom");
        
        Flag flag3 = new Flag(2, 300, 300, 60);  // Bob's flag
        flag3.setName("Bob's Domain");
        
        flagRepository.save(flag1);
        flagRepository.save(flag2);
        flagRepository.save(flag3);
        
        // Create test players with flag associations
        Player player1 = new Player("Alice", 250, 100);
        player1.setFlagId(flag2.getId()); // Associate with Alice's flag
        
        Player player2 = new Player("Bob", 300, 300);
        player2.setFlagId(flag3.getId()); // Associate with Bob's flag
        
        Player player3 = new Player("Charlie", 400, 200);
        player3.setFlagId(null); // Neutral player
        
        playerRepository.save(player1);
        playerRepository.save(player2);
        playerRepository.save(player3);

        // Create game resources
        createGameResources();
        
        // Create NPCs
        createNPCs();

        System.out.println("Enhanced test data initialized:");
        System.out.println("Players: " + playerRepository.count());
        System.out.println("Flags: " + flagRepository.count());
        System.out.println("Resources: " + gameResourceRepository.count());
        System.out.println("NPCs: " + npcRepository.count());
    }
    
    private void createGameResources() {
        long currentTime = System.currentTimeMillis();
        
        // Resources in Alice's territory (flag 2)
        createResource("tree", 230, 80, 5, 2, currentTime);
        createResource("mine", 270, 90, 3, 2, currentTime);
        createResource("herb", 240, 120, 8, 2, currentTime);
        createResource("water", 260, 110, 10, 2, currentTime);
        
        // Resources in Bob's territory (flag 3)
        createResource("tree", 280, 320, 4, 3, currentTime);
        createResource("mine", 320, 280, 6, 3, currentTime);
        createResource("herb", 310, 330, 7, 3, currentTime);
        
        // Resources in enemy territory (flag 1)
        createResource("tree", 120, 180, 3, 1, currentTime);
        createResource("mine", 80, 220, 8, 1, currentTime);
        
        // Neutral resources (no flag association)
        createResource("herb", 450, 100, 3, null, currentTime);
        createResource("tree", 500, 150, 2, null, currentTime);
        createResource("water", 50, 350, 5, null, currentTime);
        
        System.out.println("Game resources created in various territories");
    }
    
    private void createNPCs() {
        long currentTime = System.currentTimeMillis();
        
        // NPCs in Alice's territory (flag 2) - mostly friendly
        createNPC("ghost", 220, 70, 50, 50, "passive", 2, currentTime);
        createNPC("troll", 280, 120, 80, 80, "neutral", 2, currentTime);
        
        // NPCs in Bob's territory (flag 3) - mixed
        createNPC("alien", 290, 310, 90, 90, "aggressive", 3, currentTime);
        createNPC("troll", 330, 290, 120, 120, "neutral", 3, currentTime);
        
        // NPCs in enemy territory (flag 1) - hostile
        createNPC("troll", 110, 190, 100, 100, "very_aggressive", 1, currentTime);
        createNPC("alien", 90, 230, 150, 150, "aggressive", 1, currentTime);
        createNPC("ghost", 130, 210, 60, 60, "aggressive", 1, currentTime);
        
        // Neutral NPCs (no flag association)
        createNPC("ghost", 470, 120, 40, 40, "passive", null, currentTime);
        createNPC("troll", 520, 180, 70, 70, "neutral", null, currentTime);
        createNPC("alien", 30, 380, 110, 110, "aggressive", null, currentTime);
        
        System.out.println("NPCs created with varying aggression levels");
    }
    
    private void createResource(String type, double x, double y, int quantity, Integer flagId, long spawnTime) {
        GameResource resource = new GameResource();
        resource.setType(type);
        resource.setX(x);
        resource.setY(y);
        resource.setQuantity(quantity);
        resource.setFlagId(flagId);
        resource.setActive(true);
        resource.setSpawnTime(spawnTime);
        gameResourceRepository.save(resource);
    }
    
    private void createNPC(String type, double x, double y, int health, int maxHealth, 
                          String aggressionLevel, Integer flagId, long spawnTime) {
        NPC npc = new NPC();
        npc.setType(type);
        npc.setX(x);
        npc.setY(y);
        npc.setHealth(health);
        npc.setMaxHealth(maxHealth);
        npc.setAggressionLevel(aggressionLevel);
        npc.setFlagId(flagId);
        npc.setAlive(true);
        npc.setSpawnTime(spawnTime);
        npcRepository.save(npc);
    }
}
