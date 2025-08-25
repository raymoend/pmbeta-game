# Server-Side Flag System Implementation

## Overview

This implementation provides a comprehensive, server-authoritative flag territory system for your PMBeta location-based RPG game, similar to Parallel Kingdom. The system ensures that all flag interactions are validated server-side to prevent cheating.

## Key Features

### 1. **Server-Authoritative Movement Validation**
- All player movement is validated against flag territories
- Players can only move within flag radii or make small local moves
- Movement API returns territory influence information

### 2. **Flag Management System**
- **Place flags**: Server validates location, costs, and conflicts
- **Upgrade flags**: Level progression with exponential costs 
- **Attack flags**: Combat system with damage calculations
- **Capture flags**: Transfer ownership after destruction
- **Revenue collection**: Automatic gold generation over time
- **Jump to flag**: PK-style instant travel between owned flags

### 3. **Overlap Conflict Resolution**
- Multiple overlapping flags handled with precedence rules
- Distance-based priority (closest flag controls area)
- Alternative resolution methods: level, age, influence strength
- Contested territory bonuses and penalties

### 4. **Territory Effects System**
- **Friendly territory**: Health/stamina regen, XP bonus, resource bonus
- **Enemy territory**: Penalties, restrictions, combat disadvantages  
- **Contested zones**: Bonus XP but instability effects
- **Building permissions**: Territory-based construction rights

## Database Schema

### TerritoryFlag Model
```sql
-- Core flag properties
id (UUID), owner_id (FK), lat, lon, radius_meters
level (1-5), status, current_hp, max_hp
flag_color, custom_name, created_at

-- Economy
base_revenue_per_hour, uncollected_revenue
daily_upkeep_cost, upkeep_due_at

-- Combat & Timing
last_attacked, capture_window_started
construction_time_minutes, upgrade_started
```

### TerritoryZone Model  
```sql
-- Spatial indexing for fast queries
flag_id (FK), center_lat, center_lon, radius_meters
north_lat, south_lat, east_lon, west_lon  -- Bounding box
```

### Supporting Models
- `FlagRevenueCollection` - Revenue tracking
- `FlagCombatLog` - Attack/capture history  
- `FlagUpkeepLog` - Maintenance tracking

## API Endpoints

### Flag Data
- `GET /api/flags/` - Get all flags in visible area
- `GET /api/flags/?radius=2.0` - Specify search radius

### Flag Management
- `POST /api/flags/place/` - Place new flag
- `POST /api/flags/{id}/upgrade/` - Upgrade flag level
- `POST /api/flags/{id}/attack/` - Attack enemy flag
- `POST /api/flags/{id}/capture/` - Capture destroyed flag

### Flag Utilities
- `POST /api/flags/{id}/collect-revenue/` - Collect gold
- `POST /api/flags/{id}/jump/` - Instant travel to flag

### Player Movement
- `POST /api/player/move/` - Move with territory validation

## Territory Influence Logic

### Conflict Resolution Rules

1. **Distance Priority** (Default)
   ```python
   influences.sort(key=lambda x: x['distance'])
   ```
   - Closest flag to location wins control
   - PK-style precedence system

2. **Level Priority**
   ```python  
   influences.sort(key=lambda x: (-x['flag_level'], x['distance']))
   ```
   - Higher level flags take precedence
   - Distance as tiebreaker

3. **Age Priority**
   ```python
   influences.sort(key=lambda x: (x['placement_time'], x['distance']))
   ```
   - First placed flag wins ("grandfather clause")

4. **Influence Strength**
   ```python
   strength = flag_level * 10 * (0.5 + 0.5 * distance_factor)
   ```
   - Calculated influence value wins

### Movement Restrictions

```python
def can_move_to_location(character, lat, lon):
    # Check if destination is within any flag radius
    for flag in active_flags:
        if distance_to_flag <= flag.radius_meters:
            return True  # Movement allowed
    
    # If in flag, allow small local moves (50m max)  
    if current_flag and distance_to_target <= 50:
        return True
        
    return False  # Movement denied
```

### Territory Effects

```python
# Owner benefits
if is_owner:
    effects['bonuses'] = ['health_regen', 'stamina_regen', 'resource_bonus']
    effects['experience_multiplier'] = 1.1  # 10% XP bonus

# Enemy territory penalties  
else:
    effects['penalties'] = ['reduced_health_regen', 'pvp_vulnerability'] 
    effects['restrictions'] = ['no_resource_gathering', 'no_building']
    effects['experience_multiplier'] = 0.9  # 10% XP penalty
```

## Security Features

### Server-Side Validation
- All coordinates validated against flag territories
- Distance calculations use Haversine formula
- Resource costs deducted before actions
- Status checks prevent invalid operations

### Anti-Cheat Measures  
- Client never decides territory control
- All flag interactions require server approval
- Movement validation prevents teleportation
- Combat damage calculated server-side

### Conflict Prevention
- Minimum flag separation distances (500m)
- Placement proximity checks (100m from player)
- Overlap detection and resolution
- Resource requirement validation

## Usage Examples

### Placing a Flag
```javascript
fetch('/api/flags/place/', {
    method: 'POST',
    body: JSON.stringify({
        lat: 40.7128, 
        lon: -74.0060,
        name: 'My Outpost'
    })
});
```

### Checking Territory Control
```javascript
// Movement automatically returns territory info
fetch('/api/player/move/', {
    method: 'POST', 
    body: JSON.stringify({lat: 40.7128, lon: -74.0060})
}).then(response => {
    const data = response.json();
    console.log(data.territory_info);
    // Shows controlling flag, bonuses, restrictions
});
```

### Attack Sequence
```javascript
// 1. Attack flag
fetch(`/api/flags/${flagId}/attack/`, {method: 'POST'});

// 2. If destroyed (HP = 0), capture it  
fetch(`/api/flags/${flagId}/capture/`, {method: 'POST'});
```

## Performance Optimizations

### Spatial Indexing
- Bounding box pre-filtering for distance queries
- Database indexes on lat/lon columns
- Radius-based candidate selection

### Caching Strategy
- Territory effects cached per location
- Flag data cached with invalidation
- Influence calculations memoized

### Query Optimization  
```sql
-- Efficient flag lookup
SELECT * FROM pk_territory_flags 
WHERE lat >= ? AND lat <= ? AND lon >= ? AND lon <= ?
AND status = 'active';

-- Distance-based filtering applied after
```

## Integration Points

### WebSocket Updates
- Real-time flag status changes
- Territory control notifications  
- Combat event broadcasting

### Resource System
- Territory ownership affects gathering
- Resource nodes linked to controlling flags
- Bonus yields in friendly territory

### Combat System  
- Territory bonuses/penalties in PvP
- Flag combat separate from player combat
- Siege mechanics for organized attacks

## Configuration Options

### Game Balance Settings
```python
# Flag costs and stats per level
FLAG_LEVELS = {
    1: {'radius': 200, 'hp': 100, 'cost': 500},
    2: {'radius': 300, 'hp': 150, 'cost': 1200},
    # ... up to level 5
}

# Territory effects
TERRITORY_BONUSES = {
    'health_regen_percent': 0.02,    # 2% per tick
    'stamina_regen_percent': 0.05,   # 5% per tick  
    'xp_bonus_friendly': 0.1,        # 10% bonus
    'xp_penalty_enemy': 0.1          # 10% penalty
}
```

This implementation provides a robust, cheat-resistant flag system that matches Parallel Kingdom's core mechanics while being adaptable to your specific game requirements.
