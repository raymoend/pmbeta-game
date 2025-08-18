# Parallel Kingdom Flags - System Specification

## Overview

Parallel Kingdom (PK) flags were territorial control structures that formed the core of the game's location-based MMO mechanics. This document reverse-engineers how they worked based on gameplay mechanics and player experiences.

## Core Flag Mechanics

### 1. Territory Control
- **Circular Territory**: Each flag controlled a circular area around its placement point
- **Radius by Level**: 
  - Level 1: ~200 meters radius
  - Level 2: ~300 meters radius  
  - Level 3: ~400 meters radius
  - Level 4: ~500 meters radius
  - Level 5: ~600 meters radius (max level)
- **No Overlap Rule**: Players couldn't place flags within another player's territory radius
- **Ownership**: One flag per territory, clearly owned by a single player

### 2. Flag Placement
- **Distance Limit**: Could only place flags within ~1km of current location
- **Terrain Restrictions**: No placement on water, major roads, or restricted areas
- **Resource Cost**: Required gold + materials (wood, stone, food)
- **Initial Stats**: Started at Level 1 with base HP and small radius

### 3. Revenue Generation
```
Base Revenue Formula:
hourly_gold = base_rate * level_multiplier * location_bonus * random_factor

Where:
- base_rate: 10-50 gold/hour depending on location type
- level_multiplier: 1.0 to 3.0 based on flag level
- location_bonus: 0.5x (wilderness) to 2.0x (cities) 
- random_factor: 0.8 to 1.2 (±20% variance)
```

### 4. Upkeep System
- **Daily Upkeep**: Required gold payment every 24 hours
- **Upkeep Cost**: `level * 50 * location_modifier` gold per day
- **Grace Period**: 3-day grace period before decay begins
- **Decay Process**: 
  - Day 1-3: No penalty
  - Day 4+: Lose 10 HP per day
  - HP reaches 0: Flag becomes "Decayed" and capturable by anyone

### 5. Flag Levels & Upgrades
- **Max Level**: 5 levels total
- **Upgrade Costs** (exponential scaling):
  ```
  Level 2: 500 gold, 25 wood, 15 stone
  Level 3: 1,200 gold, 50 wood, 30 stone  
  Level 4: 2,500 gold, 100 wood, 60 stone
  Level 5: 5,000 gold, 200 wood, 120 stone
  ```
- **Upgrade Benefits**:
  - Increased territory radius
  - Higher revenue generation
  - More HP (harder to destroy)
  - Higher upkeep costs

### 6. Combat System
- **Attack Requirements**: Must be inside enemy territory to attack
- **Attack Damage**: Based on attacker's level and weapons
- **HP System**: Flags had HP that decreased with attacks
- **Destruction**: When HP reaches 0, flag enters "Capturable" state
- **Capture Window**: 30-minute window for capture after destruction
- **Capture Process**: Pay resources to claim destroyed flag
- **Loot**: Attacker gets portion of stored revenue and materials

### 7. Defense Mechanisms
- **Repair**: Owner could repair damage with gold/materials
- **Reinforcement**: Upgrade to higher level for more HP
- **Location Strategy**: Place in hard-to-reach areas
- **Alliance Protection**: Informal player agreements

## Flag Colors & Customization

### Basic Colors (Free)
- Red, Blue, Green, Yellow, Purple, Orange, Black, White

### Premium Colors (Special Unlock)
- Gold (high level requirement)
- Silver (moderate level requirement)
- Custom colors (rare/event rewards)

### Color Mechanics
- **Visibility**: Colors helped identify flag ownership on map
- **No Gameplay Bonus**: Colors were purely cosmetic
- **Unlock System**: Some colors required level or achievements

## Economic Balance

### Revenue vs Upkeep
```
Profitable Flag Calculation:
daily_profit = (hourly_revenue * 24) - daily_upkeep

Example Level 3 Flag in good location:
- Revenue: 35 gold/hour * 24 = 840 gold/day
- Upkeep: 3 * 50 * 1.5 = 225 gold/day  
- Profit: 840 - 225 = 615 gold/day
```

### Risk vs Reward
- Higher level flags = More revenue but higher upkeep
- Better locations = More revenue but more PvP risk
- Remote flags = Lower revenue but safer from attacks

## Strategic Gameplay

### Flag Placement Strategy
1. **Resource Nodes**: Near gathering spots for bonus income
2. **Chokepoints**: Control travel routes between cities
3. **City Outskirts**: Balance of safety and revenue
4. **Remote Corners**: Low risk, low reward income

### Territory Expansion
- **Network Effect**: Multiple flags could create influence zones
- **Supply Lines**: Flags helped secure resource gathering routes
- **Defensive Clusters**: Group flags for mutual protection

### PvP Dynamics
- **Territory Wars**: Guilds would fight for prime flag locations
- **Economic Warfare**: Destroy enemy flags to hurt their income
- **Capture Raids**: Coordinate attacks during off-hours
- **Defense Cooperation**: Alliance members would help repair/defend

## Technical Implementation Notes

### Location Services
- GPS-based positioning with ~10-50m accuracy
- Server-side validation of player location
- Anti-spoofing measures for location integrity

### Real-time Updates  
- Flag status updates every 5-15 minutes
- Push notifications for attacks/capture events
- Batch processing for revenue generation

### Data Storage
- Flag positions stored as lat/lon coordinates
- Territory boundaries calculated dynamically
- Revenue/upkeep processed via scheduled jobs

## Key Differences from Traditional MMOs

1. **Real Location**: Flags tied to actual GPS coordinates
2. **Persistent World**: Flags exist 24/7 whether player online or not
3. **Physical Movement**: Had to physically travel to interact with flags
4. **Asynchronous Combat**: Attacks could happen when player offline
5. **Location Scarcity**: Good spots were limited by real geography

## Balancing Lessons

### What Worked Well
- Simple upgrade progression (5 levels)
- Clear risk/reward tradeoffs
- Territory control created meaningful PvP
- Economic gameplay appealed to casual players

### Common Problems
- **Flag Spam**: Too many low-level flags cluttering good areas
- **Abandoned Flags**: Players quit but flags remained
- **Geographic Inequality**: Rural vs urban player advantages
- **Upkeep Burden**: High-level flags became expensive to maintain

## Implementation Recommendations

For PMBeta implementation:

1. **Start Simple**: Basic flags with 3-5 levels max
2. **Aggressive Decay**: Remove abandoned flags quickly
3. **Location Bonuses**: Vary revenue by area density/type
4. **Reasonable Upkeep**: Balance should favor active players
5. **Clear UI**: Show territory boundaries and status clearly
6. **Unrestricted Combat**: Flags can be attacked 24/7 regardless of owner status

---

This specification serves as the foundation for implementing PK-style flags in PMBeta while learning from the original game's successes and challenges.
