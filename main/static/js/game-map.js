/**
 * GameMap - MapBox integration for The Shattered Realm
 * Handles interactive map, character movement, monsters, and real-time updates
 */
class GameMap {
    constructor(options = {}) {
        this.mapboxToken = options.mapboxToken;
        this.container = options.container || 'map';
        this.character = options.character || {};
        this.api = options.api;
        this.websocket = options.websocket;
        
        this.map = null;
        this.characterMarker = null;
        this.monsterMarkers = new Map();
        this.playerMarkers = new Map();
        this.isMoving = false;
        this.lastMoveTime = 0;
        this.moveThrottle = 1000; // 1 second between moves
        
        this.init();
    }
    
    async init() {
        if (!this.mapboxToken) {
            console.error('MapBox access token is required');
            return;
        }
        
        mapboxgl.accessToken = this.mapboxToken;
        
        // Initialize map
        this.map = new mapboxgl.Map({
            container: this.container,
            style: 'mapbox://styles/mapbox/dark-v11', // Dark fantasy theme
            center: [this.character.lon || -74.5, this.character.lat || 40],
            zoom: 15,
            pitch: 45,
            bearing: -17.6,
            antialias: true
        });
        
        // Wait for map to load
        this.map.on('load', () => {
            this.setupMapFeatures();
            this.setupEventListeners();
            this.addCharacterMarker();
            this.loadNearbyEntities();
        });
        
        // Add navigation controls
        this.map.addControl(new mapboxgl.NavigationControl());
        
        // Add fullscreen control
        this.map.addControl(new mapboxgl.FullscreenControl());
    }
    
    setupMapFeatures() {
        // Add 3D buildings layer for atmosphere
        this.map.on('style.load', () => {
            // Add a sky layer for better atmosphere
            this.map.addLayer({
                'id': 'sky',
                'type': 'sky',
                'paint': {
                    'sky-type': 'atmosphere',
                    'sky-atmosphere-sun': [0.0, 0.0],
                    'sky-atmosphere-sun-intensity': 15
                }
            });
            
            // Add building extrusion layer
            const layers = this.map.getStyle().layers;
            const labelLayerId = layers.find(
                (layer) => layer.type === 'symbol' && layer.layout['text-field']
            ).id;
            
            this.map.addLayer({
                'id': 'add-3d-buildings',
                'source': 'composite',
                'source-layer': 'building',
                'filter': ['==', 'extrude', 'true'],
                'type': 'fill-extrusion',
                'minzoom': 15,
                'paint': {
                    'fill-extrusion-color': '#aaa',
                    'fill-extrusion-height': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        15, 0,
                        15.05, ['get', 'height']
                    ],
                    'fill-extrusion-base': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        15, 0,
                        15.05, ['get', 'min_height']
                    ],
                    'fill-extrusion-opacity': 0.6
                }
            }, labelLayerId);
        });
    }
    
    setupEventListeners() {
        // Handle map clicks for movement
        this.map.on('click', (e) => {
            this.handleMapClick(e);
        });
        
        // Handle map movements
        this.map.on('moveend', () => {
            this.updateVisibleArea();
        });
        
        // WebSocket event listeners
        if (this.websocket) {
            this.websocket.addEventListener('player_moved', (data) => {
                this.handlePlayerMoved(data);
            });
            
            this.websocket.addEventListener('monster_spawned', (data) => {
                this.addMonsterMarker(data);
            });
            
            this.websocket.addEventListener('monster_moved', (data) => {
                this.updateMonsterPosition(data);
            });
            
            this.websocket.addEventListener('monster_died', (data) => {
                this.removeMonsterMarker(data.monster_id);
            });
            
            this.websocket.addEventListener('player_joined', (data) => {
                this.addPlayerMarker(data);
            });
            
            this.websocket.addEventListener('player_left', (data) => {
                this.removePlayerMarker(data.player_id);
            });
        }
    }
    
    addCharacterMarker() {
        if (!this.character.lat || !this.character.lon) return;
        
        // Create character marker element
        const el = document.createElement('div');
        el.className = 'character-marker';
        el.innerHTML = `
            <div class="marker-icon character-icon">
                <i class="fas fa-user-shield"></i>
            </div>
            <div class="marker-label">${this.character.name}</div>
        `;
        
        this.characterMarker = new mapboxgl.Marker(el)
            .setLngLat([this.character.lon, this.character.lat])
            .addTo(this.map);
    }
    
    async handleMapClick(e) {
        if (this.isMoving) return;
        
        const now = Date.now();
        if (now - this.lastMoveTime < this.moveThrottle) {
            this.showNotification('Please wait before moving again', 'warning');
            return;
        }
        
        const { lng, lat } = e.lngLat;
        
        try {
            this.isMoving = true;
            this.lastMoveTime = now;
            
            // Show movement indicator
            this.showMovementIndicator(lng, lat);
            
            // Send movement request
            const response = await this.api.moveCharacter(lat, lng);
            
            if (response.success) {
                this.updateCharacterPosition(lat, lng);
                this.character.lat = lat;
                this.character.lon = lng;
                
                // Update location info
                this.updateLocationInfo(response.location);
                
                // Load new nearby entities
                this.loadNearbyEntities();
            } else {
                this.showNotification(response.message || 'Movement failed', 'error');
            }
        } catch (error) {
            console.error('Movement error:', error);
            this.showNotification('Movement failed', 'error');
        } finally {
            this.isMoving = false;
            this.hideMovementIndicator();
        }
    }
    
    updateCharacterPosition(lat, lon) {
        if (this.characterMarker) {
            this.characterMarker.setLngLat([lon, lat]);
        }
    }
    
    addMonsterMarker(monster) {
        if (this.monsterMarkers.has(monster.id)) return;
        
        const el = document.createElement('div');
        el.className = 'monster-marker';
        el.innerHTML = `
            <div class="marker-icon monster-icon" data-level="${monster.level}">
                <i class="fas fa-dragon"></i>
            </div>
            <div class="marker-label">${monster.name} (Lvl ${monster.level})</div>
        `;
        
        // Add click handler for monster interaction
        el.addEventListener('click', () => {
            this.handleMonsterClick(monster);
        });
        
        const marker = new mapboxgl.Marker(el)
            .setLngLat([monster.lon, monster.lat])
            .addTo(this.map);
        
        this.monsterMarkers.set(monster.id, marker);
    }
    
    addPlayerMarker(player) {
        if (this.playerMarkers.has(player.id) || player.id === this.character.id) return;
        
        const el = document.createElement('div');
        el.className = 'player-marker';
        el.innerHTML = `
            <div class="marker-icon player-icon">
                <i class="fas fa-user"></i>
            </div>
            <div class="marker-label">${player.name} (Lvl ${player.level})</div>
        `;
        
        const marker = new mapboxgl.Marker(el)
            .setLngLat([player.lon, player.lat])
            .addTo(this.map);
        
        this.playerMarkers.set(player.id, marker);
    }
    
    updateMonsterPosition(data) {
        const marker = this.monsterMarkers.get(data.monster_id);
        if (marker) {
            marker.setLngLat([data.lon, data.lat]);
        }
    }
    
    removeMonsterMarker(monsterId) {
        const marker = this.monsterMarkers.get(monsterId);
        if (marker) {
            marker.remove();
            this.monsterMarkers.delete(monsterId);
        }
    }
    
    removePlayerMarker(playerId) {
        const marker = this.playerMarkers.get(playerId);
        if (marker) {
            marker.remove();
            this.playerMarkers.delete(playerId);
        }
    }
    
    async handleMonsterClick(monster) {
        try {
            const distance = this.calculateDistance(
                this.character.lat, this.character.lon,
                monster.lat, monster.lon
            );
            
            if (distance > 0.001) { // ~100 meters
                this.showNotification('Monster is too far away to attack', 'warning');
                return;
            }
            
            // Start combat
            const response = await this.api.attackMonster(monster.id);
            if (response.success) {
                this.showNotification(`Attacking ${monster.name}!`, 'success');
            } else {
                this.showNotification(response.message || 'Attack failed', 'error');
            }
        } catch (error) {
            console.error('Monster attack error:', error);
            this.showNotification('Attack failed', 'error');
        }
    }
    
    async loadNearbyEntities() {
        try {
            const response = await this.api.getMapData(
                this.character.lat, 
                this.character.lon, 
                1000 // 1km radius
            );
            
            if (response.success) {
                // Clear existing markers
                this.clearMonsterMarkers();
                this.clearPlayerMarkers();
                
                // Add monsters
                response.monsters?.forEach(monster => {
                    this.addMonsterMarker(monster);
                });
                
                // Add other players
                response.players?.forEach(player => {
                    this.addPlayerMarker(player);
                });
                
                // Update monster count display
                this.updateMonsterCount(response.monsters?.length || 0);
            }
        } catch (error) {
            console.error('Failed to load nearby entities:', error);
        }
    }
    
    clearMonsterMarkers() {
        this.monsterMarkers.forEach(marker => marker.remove());
        this.monsterMarkers.clear();
    }
    
    clearPlayerMarkers() {
        this.playerMarkers.forEach(marker => marker.remove());
        this.playerMarkers.clear();
    }
    
    centerOnCharacter() {
        if (this.character.lat && this.character.lon) {
            this.map.flyTo({
                center: [this.character.lon, this.character.lat],
                zoom: 15,
                duration: 1000
            });
        }
    }
    
    showMovementIndicator(lng, lat) {
        // Add temporary marker at destination
        const el = document.createElement('div');
        el.className = 'movement-indicator';
        el.innerHTML = '<i class="fas fa-crosshairs"></i>';
        
        this.movementIndicator = new mapboxgl.Marker(el)
            .setLngLat([lng, lat])
            .addTo(this.map);
    }
    
    hideMovementIndicator() {
        if (this.movementIndicator) {
            this.movementIndicator.remove();
            this.movementIndicator = null;
        }
    }
    
    updateLocationInfo(location) {
        // Update location display in UI
        const locationName = document.getElementById('current-location-name');
        const coordinates = document.getElementById('current-coordinates');
        const region = document.getElementById('current-region');
        
        if (locationName) {
            locationName.textContent = location.name || 'Unknown Location';
        }
        
        if (coordinates) {
            coordinates.textContent = `${location.lat?.toFixed(4)}, ${location.lon?.toFixed(4)}`;
        }
        
        if (region) {
            region.textContent = location.region || 'No region';
        }
    }
    
    updateMonsterCount(count) {
        const monsterList = document.getElementById('monster-list');
        if (monsterList) {
            if (count === 0) {
                monsterList.innerHTML = '<div class="no-monsters">No monsters nearby</div>';
            } else {
                monsterList.innerHTML = `<div class="monster-count">${count} monsters nearby</div>`;
            }
        }
    }
    
    updateVisibleArea() {
        // Debounce the update
        clearTimeout(this.visibilityTimeout);
        this.visibilityTimeout = setTimeout(() => {
            this.loadNearbyEntities();
        }, 1000);
    }
    
    handlePlayerMoved(data) {
        if (data.player_id === this.character.id) return;
        
        const marker = this.playerMarkers.get(data.player_id);
        if (marker) {
            marker.setLngLat([data.lon, data.lat]);
        }
    }
    
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Earth radius in meters
        const φ1 = lat1 * Math.PI/180;
        const φ2 = lat2 * Math.PI/180;
        const Δφ = (lat2-lat1) * Math.PI/180;
        const Δλ = (lon2-lon1) * Math.PI/180;
        
        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        
        return R * c / 1000; // Return distance in km
    }
    
    showNotification(message, type = 'info') {
        // Use the global notification system
        if (window.gameApp && window.gameApp.showNotification) {
            window.gameApp.showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// Export for use in other modules
window.GameMap = GameMap;
