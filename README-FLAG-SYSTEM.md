# Parallel Kingdom Enhanced Flag System

A complete implementation of a Parallel Kingdom-style flag system with territorial control, resources, NPCs, and movement restrictions, built using Spring Boot backend and JavaFX client.

## 🎮 Features

### Core Flag System
- **Territorial Control**: Players can only move within their flag zones
- **Flag Visualization**: Semi-transparent circular zones showing territory boundaries  
- **Ownership-based Coloring**: Green for owned flags, red for enemy flags
- **Movement Validation**: Server-authoritative movement with zone checking

### Game Entities
- **Resources**: Trees, mines, herbs, and water sources with harvestable quantities
- **NPCs**: Trolls, aliens, and ghosts with varying aggression levels and health
- **Interactive Gameplay**: Right-click to harvest resources or attack NPCs
- **Real-time Updates**: Automatic refresh of entities every 5 seconds

### Enhanced Client Features
- **Tap-to-Move**: Left-click to move (Parallel Kingdom style)
- **Entity Interactions**: Right-click for harvesting/combat
- **Multi-player Support**: See other players as yellow circles
- **Status Panel**: Real-time game status and territory information
- **Tooltips**: Hover information for all game entities

## 🏗️ Architecture

### Backend (Spring Boot)
```
├── Entities (JPA)
│   ├── Flag.java           - Territory definitions
│   ├── Player.java         - Player data and positions
│   ├── GameResource.java   - Harvestable resources
│   └── NPC.java           - Non-player characters
├── Repositories (Spring Data)
│   ├── FlagRepository.java
│   ├── PlayerRepository.java
│   ├── GameResourceRepository.java
│   └── NPCRepository.java
├── Services
│   └── SpatialService.java - Movement & zone validation
└── Controllers
    ├── GameController.java - Main game API
    ├── FlagController.java - Flag management
    └── PlayerController.java - Player management
```

### Frontend (JavaFX)
```
└── TapToMoveClient.java - Complete game client with:
    ├── Movement System
    ├── Entity Rendering
    ├── Interaction Handling
    └── Real-time Updates
```

## 🚀 Quick Start

### 1. Start the Backend
```bash
cd pk-spring-api
mvn spring-boot:run
```

### 2. Compile the JavaFX Client
```bash
javac -cp "path/to/gson.jar;path/to/javafx/lib/*" TapToMoveClient.java
```

### 3. Run the Client
```bash
java -cp ".;path/to/gson.jar" --module-path "path/to/javafx/lib" --add-modules javafx.controls,javafx.fxml TapToMoveClient
```

## 🎯 Game Controls

| Action | Control | Description |
|--------|---------|-------------|
| **Move Player** | Left-click | Move to clicked location (if within flag zone) |
| **Harvest Resource** | Right-click on resource | Collect resources like trees, herbs, etc. |
| **Attack NPC** | Right-click on NPC | Combat with trolls, aliens, ghosts |
| **View Info** | Hover | Tooltip shows entity details |

## 📊 Game Mechanics

### Movement Rules
- Players can **only move within their assigned flag territory**
- Neutral players can move in neutral areas only
- Movement validation is **server-authoritative**
- Visual feedback shows allowed/blocked movement

### Resource System
- **Trees** (Brown) - Limited quantity, renewable
- **Mines** (Gray) - High-value, limited quantity  
- **Herbs** (Light Green) - Common, fast-respawning
- **Water** (Light Blue) - Unlimited, strategic locations

### NPC Combat
- **Trolls** (Green) - Melee fighters, high health
- **Aliens** (Purple) - Advanced AI, medium health
- **Ghosts** (Light Gray) - Stealth units, low health

#### Aggression Levels
- **Passive**: Won't attack, easy targets
- **Neutral**: Defensive, moderate threat
- **Aggressive**: Will attack nearby players
- **Very Aggressive**: High damage, territorial

## 🛠️ API Endpoints

### Game Management
- `GET /api/game/flags` - List all flags
- `GET /api/game/players` - List all players
- `GET /api/game/entities` - Get entities in area

### Player Actions
- `POST /api/game/player/{id}/move` - Move player
- `GET /api/game/player/{id}/can-move` - Check movement validity
- `POST /api/game/player/{id}/interact/resource/{resourceId}` - Harvest resource
- `POST /api/game/player/{id}/interact/npc/{npcId}` - Attack NPC

### Flag System
- `GET /api/game/flag/{id}` - Get flag details with entities
- `GET /api/flags` - Legacy flag endpoint

## 🔧 Configuration

### Database Setup
The system uses H2 database with JPA. Sample data is automatically created:

- **3 Flags**: Alice's Kingdom, Bob's Domain, Enemy Territory
- **3 Players**: Alice (flag owner), Bob (flag owner), Charlie (neutral)
- **12 Resources**: Distributed across territories
- **10 NPCs**: Various types with different aggression levels

### Spatial Configuration
- Flag zones are circular with configurable radius
- Interaction range: 50 units for resources, 30 units for NPCs
- Map size: 600x600 pixels (client), expandable

## 🎨 Visual Design

### Color Coding
- **Green Flags**: Player-owned territories
- **Red Flags**: Enemy territories  
- **Blue Circle**: Current player (larger, outlined)
- **Yellow Circles**: Other players (smaller)
- **Resource Colors**: Type-specific (brown trees, gray mines, etc.)
- **NPC Colors**: Type and aggression-based intensity

### UI Layout
- **Main Map**: 600x600 game area
- **Info Panel**: 180px right panel with status updates
- **Tooltips**: Context-sensitive entity information

## 🔮 Future Enhancements

### Planned Features
- **Flag Capturing**: Ability to conquer other territories
- **Resource Trading**: Economy system between players
- **NPC AI**: Advanced pathfinding and behavior
- **Quest System**: Missions and objectives
- **Multiplayer Chat**: Communication between players
- **Persistent World**: Save/load game state

### Technical Improvements
- **WebSocket Support**: Real-time multiplayer updates
- **Mobile Client**: React Native or Flutter version
- **Map Editor**: Create custom territories and scenarios
- **Admin Panel**: Manage players, flags, and entities

## 📝 Development Notes

### Design Patterns
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic separation
- **DTO Pattern**: API response standardization
- **Observer Pattern**: Real-time client updates

### Performance Considerations
- **Spatial Indexing**: Efficient zone queries
- **Lazy Loading**: On-demand entity loading
- **Connection Pooling**: Database optimization
- **Client Caching**: Reduced server requests

## 🤝 Contributing

This enhanced flag system provides a solid foundation for Parallel Kingdom-style gameplay. The modular architecture allows for easy extension of features like new entity types, game mechanics, and client interfaces.

### Key Extension Points
- Add new resource types in `getResourceColor()`
- Create new NPC types in `getNPCColor()`
- Extend spatial services for complex territories
- Add new interaction types in GameController

---

**Built with**: Spring Boot 2.x, JavaFX 11+, H2 Database, Maven
**Compatible with**: Java 11+, Windows/Mac/Linux
