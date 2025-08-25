package com.pk.demo;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface GameResourceRepository extends JpaRepository<GameResource, Integer> {
    
    /**
     * Find all resources within a specific flag
     */
    List<GameResource> findByFlagId(int flagId);
    
    /**
     * Find all active resources within a specific flag
     */
    List<GameResource> findByFlagIdAndIsActive(int flagId, boolean isActive);
    
    /**
     * Find all resources of a specific type
     */
    List<GameResource> findByType(String type);
    
    /**
     * Find all active resources of a specific type within a flag
     */
    List<GameResource> findByFlagIdAndTypeAndIsActive(int flagId, String type, boolean isActive);
    
    /**
     * Find resources within a rectangular area (for spatial queries)
     */
    @Query("SELECT r FROM GameResource r WHERE r.x BETWEEN :minX AND :maxX AND r.y BETWEEN :minY AND :maxY AND r.isActive = true")
    List<GameResource> findResourcesInArea(@Param("minX") double minX, @Param("maxX") double maxX, 
                                         @Param("minY") double minY, @Param("maxY") double maxY);
    
    /**
     * Find resources spawned before a certain time (for cleanup)
     */
    @Query("SELECT r FROM GameResource r WHERE r.spawnTime < :time")
    List<GameResource> findOldResources(@Param("time") long time);
    
    /**
     * Count active resources in a flag
     */
    int countByFlagIdAndIsActive(int flagId, boolean isActive);
    
    /**
     * Count resources by type in a flag
     */
    int countByFlagIdAndType(int flagId, String type);
}
