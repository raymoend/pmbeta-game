package com.pk.demo;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface NPCRepository extends JpaRepository<NPC, Integer> {
    
    /**
     * Find all NPCs within a specific flag
     */
    List<NPC> findByFlagId(int flagId);
    
    /**
     * Find all alive NPCs within a specific flag
     */
    List<NPC> findByFlagIdAndIsAlive(int flagId, boolean isAlive);
    
    /**
     * Find all NPCs of a specific type
     */
    List<NPC> findByType(String type);
    
    /**
     * Find all alive NPCs of a specific type within a flag
     */
    List<NPC> findByFlagIdAndTypeAndIsAlive(int flagId, String type, boolean isAlive);
    
    /**
     * Find NPCs within a rectangular area (for spatial queries)
     */
    @Query("SELECT n FROM NPC n WHERE n.x BETWEEN :minX AND :maxX AND n.y BETWEEN :minY AND :maxY AND n.isAlive = true")
    List<NPC> findNPCsInArea(@Param("minX") double minX, @Param("maxX") double maxX, 
                             @Param("minY") double minY, @Param("maxY") double maxY);
    
    /**
     * Find NPCs by aggression level
     */
    List<NPC> findByAggressionLevel(String aggressionLevel);
    
    /**
     * Find aggressive NPCs within a flag
     */
    @Query("SELECT n FROM NPC n WHERE n.flagId = :flagId AND n.aggressionLevel IN ('aggressive', 'very_aggressive') AND n.isAlive = true")
    List<NPC> findAggressiveNPCsInFlag(@Param("flagId") int flagId);
    
    /**
     * Find NPCs with health below a threshold
     */
    @Query("SELECT n FROM NPC n WHERE n.health < :healthThreshold AND n.isAlive = true")
    List<NPC> findNPCsWithLowHealth(@Param("healthThreshold") int healthThreshold);
    
    /**
     * Find NPCs spawned before a certain time (for cleanup)
     */
    @Query("SELECT n FROM NPC n WHERE n.spawnTime < :time")
    List<NPC> findOldNPCs(@Param("time") long time);
    
    /**
     * Count alive NPCs in a flag
     */
    int countByFlagIdAndIsAlive(int flagId, boolean isAlive);
    
    /**
     * Count NPCs by type in a flag
     */
    int countByFlagIdAndType(int flagId, String type);
}
