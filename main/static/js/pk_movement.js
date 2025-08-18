/**
 * Parallel Kingdom Style Movement System
 * Tap-to-move with speed 220, resource spawning in territories
 */

class PKMovementSystem {
    constructor(options) {
        this.character = options.character;
        this.worldMap = options.worldMap;
        this.territoryMap = options.territoryMap;
        this.onLocationUpdate = options.onLocationUpdate;
        this.playerMarker = null;
        this.isMoving = false;
        this.moveSpeed = 220; // PK movement speed in meters/second
        this.resourceMarkers = [];
        this.currentPosition = {
            lat: this.character.lat,
            lng: this.character.lon
        };
        
        // Set global reference for resource collection
        window.pkMovement = this;
        
        this.init();
    }

    init() {
        console.log('⚡ PK Movement System initialized with speed:', this.moveSpeed);
        this.setupMapClickHandlers();
        this.createPlayerMarker();
        this.startResourceSpawning();
    }

    setupMapClickHandlers() {
        // Setup click handlers for both maps
        if (this.worldMap) {
            if (this.worldMap.loaded()) {
                // Map is already loaded, setup immediately
                this.setupMovementForMap(this.worldMap);
            } else {
                // Wait for map to load
                this.worldMap.on('load', () => {
                    this.setupMovementForMap(this.worldMap);
                });
            }
        }
        
        if (this.territoryMap) {
            if (this.territoryMap.loaded()) {
                // Map is already loaded, setup immediately
                this.setupMovementForMap(this.territoryMap);
            } else {
                // Wait for map to load
                this.territoryMap.on('load', () => {
                    this.setupMovementForMap(this.territoryMap);
                });
            }
        }
    }

    setupMovementForMap(map) {
        // Add player marker
        this.createPlayerMarkerOnMap(map);

        console.log('⚡ Setting up click handler for map');
        
        // Handle tap-to-move (left click only, right click is for flags)
        map.on('click', (e) => {
            console.log('⚡ Map clicked:', e.originalEvent.button, e.lngLat);
            
            // Only move on left click, ignore right clicks (flags)
            if (!e.originalEvent.button || e.originalEvent.button === 0) {
                e.preventDefault();
                this.handleMapClick(e, map);
            }
        });

        // Show movement cursor on hover
        map.on('mousemove', (e) => {
            if (!this.isMoving) {
                map.getCanvas().style.cursor = 'crosshair';
            }
        });

        // Load territory circles and resources
        setTimeout(() => {
            if (window.flagSystem) {
                window.flagSystem.loadTerritoryCircles();
            }
            this.loadNearbyResources();
        }, 1000);
    }

    createPlayerMarker() {
        const playerIcon = document.createElement('div');
        playerIcon.innerHTML = '🚶';
        playerIcon.style.fontSize = '20px';
        playerIcon.style.textAlign = 'center';
        
        this.playerMarker = new mapboxgl.Marker({
            element: playerIcon,
            anchor: 'center'
        })
        .setLngLat([this.character.lon, this.character.lat]);
    }

    createPlayerMarkerOnMap(map) {
        if (this.playerMarker && !this.playerMarker._map) {
            this.playerMarker.addTo(map);
            
            // Add popup
            const playerName = this.character.name || this.character.username || 'Player';
            this.playerMarker.setPopup(new mapboxgl.Popup({ offset: 25 })
                .setHTML(`<div style="text-align: center;">
                    <h4>${playerName}</h4>
                    <p>Level ${this.character.level}</p>
                    <p>You are here</p>
                </div>`));
        }
    }

    async handleMapClick(e, map) {
        if (this.isMoving) {
            console.log('⚡ Already moving, ignoring click');
            return;
        }

        const targetCoords = {
            lat: e.lngLat.lat,
            lng: e.lngLat.lng
        };

        console.log(`⚡ Moving to: ${targetCoords.lat}, ${targetCoords.lng}`);
        await this.moveToCoordinates(targetCoords);
    }

    async moveToCoordinates(targetCoords) {
        if (this.isMoving) return;

        this.isMoving = true;
        const startCoords = { ...this.currentPosition };
        
        // Calculate distance and time
        const distance = this.calculateDistance(
            startCoords.lat, startCoords.lng,
            targetCoords.lat, targetCoords.lng
        );
        
        const travelTime = Math.max(1, distance / this.moveSpeed) * 1000; // Convert to milliseconds
        
        console.log(`⚡ Moving ${Math.round(distance)}m in ${(travelTime/1000).toFixed(1)}s`);

        try {
            // Update server with movement
            await this.sendMovementToServer(targetCoords);

            // Animate player marker
            this.animatePlayerMovement(startCoords, targetCoords, travelTime);

            // Update character position after movement completes
            setTimeout(() => {
                this.currentPosition = targetCoords;
                this.character.lat = targetCoords.lat;
                this.character.lon = targetCoords.lng;
                this.isMoving = false;
                
                // Update UI
                this.updateLocationDisplay();
                
                // Check for resources in new location
                this.checkResourcesAtLocation();
                
                console.log('⚡ Movement completed');
            }, travelTime);

        } catch (error) {
            console.error('⚡ Movement failed:', error);
            this.isMoving = false;
        }
    }

    animatePlayerMovement(start, end, duration) {
        if (!this.playerMarker) return;

        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Linear interpolation
            const currentLat = start.lat + (end.lat - start.lat) * progress;
            const currentLng = start.lng + (end.lng - start.lng) * progress;
            
            this.playerMarker.setLngLat([currentLng, currentLat]);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }

    async sendMovementToServer(targetCoords) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.cookie.split('; ')
                             .find(row => row.startsWith('csrftoken='))
                             ?.split('=')[1] || '';

        const response = await fetch('/api/player/move/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({
                lat: targetCoords.lat,
                lon: targetCoords.lng
            })
        });

        if (!response.ok) {
            throw new Error('Movement request failed');
        }

        return await response.json();
    }

    calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371000; // Earth radius in meters
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLng/2) * Math.sin(dLng/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    updateLocationDisplay() {
        const locationElements = document.querySelectorAll('.pk-stat-value');
        locationElements.forEach(el => {
            if (el.textContent.includes(',')) {
                el.textContent = `${this.character.lat.toFixed(3)},${this.character.lon.toFixed(3)}`;
            }
        });
    }

    // Resource spawning system for territories
    async startResourceSpawning() {
        console.log('🌲 Starting resource spawning system');
        
        // Load resources immediately
        this.loadNearbyResources();
        
        // Refresh resources every 30 seconds
        setInterval(() => {
            this.loadNearbyResources();
        }, 30000);
    }

    async loadNearbyResources() {
        try {
            const response = await fetch(`/api/resources/nearby/?lat=${this.character.lat}&lon=${this.character.lon}&radius=1000`, {
                credentials: 'include'
            });

            const data = await response.json();
            
            if (data.success) {
                console.log(`🌲 Loaded ${data.resources.length} nearby resources`);
                this.displayResources(data.resources);
            }
        } catch (error) {
            console.error('🌲 Error loading resources:', error);
        }
    }

    displayResources(resources) {
        // Remove existing resource markers
        if (this.resourceMarkers) {
            this.resourceMarkers.forEach(marker => marker.remove());
        }
        this.resourceMarkers = [];

        // Add new resource markers to both maps
        resources.forEach(resource => {
            this.addResourceMarker(resource);
        });
    }

    addResourceMarker(resource) {
        const resourceIcon = this.getResourceIcon(resource.type);
        const markerElement = document.createElement('div');
        markerElement.innerHTML = resourceIcon;
        markerElement.style.fontSize = '16px';
        markerElement.style.cursor = 'pointer';
        markerElement.title = `${resource.type} - Click to collect`;

        const marker = new mapboxgl.Marker({
            element: markerElement,
            anchor: 'center'
        })
        .setLngLat([resource.lon, resource.lat])
        .setPopup(new mapboxgl.Popup({ offset: 25 })
            .setHTML(`<div>
                <strong>${resource.type}</strong><br>
                Quantity: ${resource.quantity}<br>
                <button onclick="window.pkMovement.collectResource('${resource.id}')">Collect</button>
            </div>`));

        // Add to active map(s)
        if (this.worldMap && this.worldMap.isStyleLoaded()) {
            marker.addTo(this.worldMap);
            this.resourceMarkers.push(marker);
        }
        if (this.territoryMap && this.territoryMap.isStyleLoaded()) {
            const territoryMarker = new mapboxgl.Marker({
                element: markerElement.cloneNode(true),
                anchor: 'center'
            })
            .setLngLat([resource.lon, resource.lat])
            .setPopup(new mapboxgl.Popup({ offset: 25 })
                .setHTML(`<div>
                    <strong>${resource.type}</strong><br>
                    Quantity: ${resource.quantity}<br>
                    <button onclick="window.pkMovement.collectResource('${resource.id}')">Collect</button>
                </div>`))
            .addTo(this.territoryMap);
            
            this.resourceMarkers.push(territoryMarker);
        }
    }

    getResourceIcon(resourceType) {
        const icons = {
            'tree': '🌲',
            'stone': '🪨',
            'iron': '⛏️',
            'gold': '💰',
            'well': '🏺',
            'apple_tree': '🍎',
            'npc_trader': '🧙',
            'npc_guard': '🛡️',
            'wild_animal': '🐺'
        };
        return icons[resourceType] || '❓';
    }

    async collectResource(resourceId) {
        try {
            const response = await fetch(`/api/resources/collect/${resourceId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'include'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Collected: ${data.items_gained}`, 'success');
                this.loadNearbyResources(); // Refresh resources
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error collecting resource:', error);
            this.showNotification('Failed to collect resource', 'error');
        }
    }

    async checkResourcesAtLocation() {
        // Check if player moved into a territory and spawn resources if needed
        const response = await fetch(`/api/resources/check-spawn/?lat=${this.character.lat}&lon=${this.character.lon}`, {
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success && data.spawned.length > 0) {
            console.log(`🌲 Spawned ${data.spawned.length} new resources in territory`);
            this.loadNearbyResources();
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 30000;
            max-width: 300px;
            animation: slideInRight 0.3s ease;
            ${type === 'success' ? 'background: #38a169;' : 
              type === 'error' ? 'background: #e53e3e;' : 'background: #3182ce;'}
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ')
                   .find(row => row.startsWith('csrftoken='))
                   ?.split('=')[1] || '';
    }
}

// Initialize when DOM is ready
window.PKMovementSystem = PKMovementSystem;
