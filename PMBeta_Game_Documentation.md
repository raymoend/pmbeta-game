# PMBeta - P2K-Style Location-Based Mafia Game

## Overview

PMBeta is a location-based multiplayer mafia game inspired by Parallel Kingdom (P2K) architecture. Players use real-world GPS coordinates to move around a virtual world, build criminal empires, fight NPCs, capture territory through flags, and engage in mafia-style activities.

## Key Features

### 🎯 **Core Game Mechanics**
- **Location-Based Gameplay**: Real GPS coordinates using Mapbox
- **Movement System**: 800m radius movement range from base location
- **Chunk-Based World**: Efficient loading using 0.01-degree chunks (~1km squares)
- **Real-Time Multiplayer**: WebSocket-based updates like P2K
- **Smooth Motion**: Interpolated movement animation

### 🏴 **Territory Control (Flag System)**
- **Flag Placement**: $50,000 cost, 200m minimum distance
- **Flag Types**: Territory, Family, Outpost, Stronghold, Watchtower
- **Attack System**: Attack flags to capture territory
- **Income Generation**: Flags provide hourly passive income
- **Protection Period**: 24h invulnerability after placement/capture

### 👥 **Family System**
- **Create Families**: $100,000 cost to establish a crime family
- **Hierarchy**: Boss → Underboss → Capo → Soldier → Associate
- **Family Benefits**: Shared treasury, coordinated attacks, bonuses
- **Territory Control**: Families can control multiple territories

### ⚔️ **Combat System**
- **PvE Combat**: Fight NPCs for experience, money, and reputation
- **NPC Types**: Bandits, Thugs, Enforcers, Dealers, Cops
- **Combat Stats**: Strength, Defense, Speed, Accuracy
- **Rewards**: Experience, cash, reputation based on NPC level

### 🌍 **Resource System**
- **Resource Types**: Trees, Mines, Quarries, Herbs, Ruins, Caves, Wells
- **Harvesting**: Gather resources for money and experience
- **Respawn System**: Resources regenerate after depletion
- **Level-Based Rewards**: Higher level resources give better rewards

### 🚨 **Criminal Activities**
- **Job Types**: Heists, Robberies, Drug Deals, Protection, Assassinations
- **Risk/Reward**: Higher difficulty = higher payout + more heat
- **Heat System**: Police attention that affects success chances
- **Location-Based**: Must travel to activity locations

### 🏢 **Business System**
- **Business Types**: Restaurants, Clubs, Casinos, Warehouses
- **Income Sources**: Legitimate + illegal income streams
- **Territory Bonuses**: Businesses in controlled territories get bonuses
- **Upkeep Costs**: Operating expenses reduce net profits

## Technical Architecture

### 🏗️ **Backend (Django)**
```python
# Key Models
- Player: User stats, location, mafia progression
- Flag: Territory control points with combat system  
- NPC: AI enemies with respawn mechanics
- ResourceNode: Harvestable world objects
- Family: Player organizations with hierarchy
- CriminalActivity: Location-based missions
```

### 🌐 **Frontend (Mapbox + WebSockets)**
```javascript
// Real-time features
- Chunk-based entity loading
- Smooth movement animation  
- Real-time player updates
- Interactive map controls
- Context menu system (right-click)
```

### 📡 **WebSocket System**
```python
# P2K-Style Architecture
- Chunk-based subscriptions
- Entity motion caching
- Real-time multiplayer updates
- Efficient bandwidth usage
```

## Game Progression

### 👤 **Player Advancement**
1. **Level System**: Gain XP from combat, harvesting, activities
2. **Reputation**: Street credibility affecting job availability  
3. **Heat Level**: Police attention (0-100%) affecting success
4. **Stats Growth**: Strength, Defense, Speed, Accuracy improvements

### 🏆 **Territory Expansion**
1. **Flag Placement**: Establish territory control points
2. **Defense Building**: Upgrade flags for better defense
3. **NPC Spawning**: Flags spawn guardian NPCs automatically
4. **Income Growth**: Higher level flags = more hourly income

### 👑 **Family Building**
1. **Create Family**: Establish crime organization
2. **Recruit Members**: Build up family membership
3. **Territory Wars**: Coordinate family attacks on rival flags
4. **Economic Empire**: Control multiple income sources

## Installation & Setup

### 📋 **Requirements**
```bash
# Core dependencies
Django==4.2+
channels==4.0+
redis>=4.0
django-cors-headers
channels-redis
```

### 🚀 **Quick Start**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Generate world data
python manage.py generate_world --clear-existing --num-flags 50 --num-npcs 200

# 4. Start server
python manage.py runserver

# 5. Start Celery (for background tasks)
celery -A pmbeta worker -l info
```

### ⚙️ **Configuration**
```python
# settings.py
GAME_SETTINGS = {
    'DEFAULT_START_LAT': 41.0646633,
    'DEFAULT_START_LON': -80.6391736,
    'MOVEMENT_RANGE': 800,  # meters
    'CHUNK_GRANULARITY': 100,  # 0.01 degree chunks
    'ZOOM_LEVEL': 16,
}

MAPBOX_ACCESS_TOKEN = 'your_mapbox_token_here'
```

## API Endpoints

### 🎮 **Game Actions**
```
POST /api/move/           # Move player
POST /api/flags/place/    # Place territory flag  
POST /api/flags/attack/   # Attack enemy flag
POST /api/npcs/attack/    # Fight NPC
POST /api/resources/harvest/  # Harvest resource
POST /api/activities/start/   # Start criminal activity
```

### 📊 **Data Retrieval**
```
GET /api/world/           # Get nearby entities
GET /api/flags/           # Get nearby flags
GET /api/npcs/            # Get nearby NPCs  
GET /api/resources/       # Get nearby resources
GET /api/player/stats/    # Get player statistics
```

## WebSocket Events

### 📨 **Client → Server**
```javascript
// Movement
{tag: 'move', data: {target: {lat: x, lon: y}}}

// Chat
{tag: 'chat', data: {message: 'text'}}

// Combat
{tag: 'attack_npc', data: {npc_id: 'uuid'}}
```

### 📩 **Server → Client**
```javascript
// World loading
{tag: 'load', data: {centre: {lat, lon}, entities: {...}}}

// Player movement
{tag: 'move', data: {player_id, start, end}}

// World updates
{tag: 'update', data: {entities: {...}}}
```

## Game Commands

### 🛠️ **Management Commands**
```bash
# Generate complete world
python manage.py generate_world --center-lat 41.064 --center-lon -80.639 --radius 0.05

# Clear existing data
python manage.py generate_world --clear-existing

# Custom generation
python manage.py generate_world --num-flags 30 --num-npcs 150 --num-resources 300
```

### 📈 **World Statistics**
- **Flags**: Territory control points with income generation
- **NPCs**: AI enemies with level-based rewards  
- **Resources**: Harvestable nodes with respawn timers
- **Territories**: Chunk-based control zones
- **Activities**: Location-based criminal missions

## Unique Features

### 🎯 **P2K-Inspired Elements**
- **Chunk System**: Efficient world loading using geographic chunks
- **Motion Caching**: Smooth movement with server-side interpolation  
- **Entity Spawning**: Dynamic world generation based on flags
- **Real-Time Updates**: WebSocket-based multiplayer like original P2K

### 🏴‍☠️ **Mafia Theme Innovation**
- **Heat System**: Police attention affects all activities
- **Family Hierarchies**: Complex organizational structures
- **Criminal Businesses**: Multiple income streams with risk/reward
- **Territory Wars**: Strategic flag placement and defense

## Performance Optimization

### ⚡ **Efficiency Features**
- **Chunk Loading**: Only load entities in nearby chunks
- **Motion Caching**: Redis-based movement state storage
- **Database Indexing**: Optimized queries for location-based lookups
- **WebSocket Groups**: Efficient broadcasting using chunk-based channels

### 📊 **Monitoring**
- Combat success rates and balance
- Flag placement density and income
- Player progression and retention
- Resource spawn/harvest ratios

---

## Getting Started

1. **Register Account**: Create user and spawn as new player
2. **Explore World**: Move within 800m radius, discover entities  
3. **Fight NPCs**: Gain XP, money, and reputation
4. **Harvest Resources**: Gather materials and gold
5. **Place First Flag**: Establish territory for $50,000
6. **Join/Create Family**: Build criminal organization
7. **Expand Empire**: Capture rival flags, build businesses

**PMBeta combines the strategic depth of P2K's territory control with the criminal empire building of mafia-themed games, creating a unique location-based multiplayer experience.**
