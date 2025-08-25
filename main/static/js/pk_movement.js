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
        // this.startResourceSpawning(); // Disabled to prevent resource markers
        this.createStatusDisplay();
        this.createHelpOverlay();
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
                // Prevent default map behavior (zoom, etc)
                e.preventDefault();
                if (e.originalEvent) {
                    e.originalEvent.preventDefault();
                    e.originalEvent.stopPropagation();
                }
                
                // Disable map interactions temporarily during click processing
                map.dragPan.disable();
                map.scrollZoom.disable();
                map.doubleClickZoom.disable();
                
                setTimeout(() => {
                    map.dragPan.enable();
                    map.scrollZoom.enable();
                    map.doubleClickZoom.enable();
                }, 100);
                
                this.handleMapClick(e, map);
            }
        });

        // Show movement cursor on hover
        map.on('mousemove', (e) => {
            if (!this.isMoving) {
                map.getCanvas().style.cursor = 'crosshair';
            }
        });

        // Add keyboard shortcut for flag jump menu (F key)
        document.addEventListener('keydown', (e) => {
            if (e.key.toLowerCase() === 'f' && !this.isMoving) {
                e.preventDefault();
                this.showAllFlagsMenu();
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

        console.log(`⚡ Click detected at: ${targetCoords.lat}, ${targetCoords.lng}`);
        
        // Check if click is on a player's flag for flag jumping
        const clickedFlag = await this.checkFlagAtLocation(targetCoords);
        
        if (clickedFlag && clickedFlag.is_mine) {
            console.log(`⚡ Flag jump to: ${clickedFlag.name}`);
            await this.flagJumpToLocation(clickedFlag);
        } else {
            // PK-style: Only allow local movement within walking distance
            const distance = this.calculateDistance(
                this.currentPosition.lat, this.currentPosition.lng,
                targetCoords.lat, targetCoords.lng
            );
            
            const maxWalkingDistance = 100; // 100 meters max walking distance (PK style)
            
            if (distance > maxWalkingDistance) {
                this.showNotification(`Too far to walk! (${Math.round(distance)}m)\nMax walking distance: ${maxWalkingDistance}m\nUse flag jump or build flags closer together.`, 'error');
                console.log(`⚡ Distance ${Math.round(distance)}m exceeds max walking distance ${maxWalkingDistance}m`);
                return;
            }
            
            console.log(`⚡ Local movement: ${Math.round(distance)}m (within ${maxWalkingDistance}m limit)`);
            await this.moveToCoordinates(targetCoords);
        }
    }

    async moveToCoordinates(targetCoords) {
        if (this.isMoving) {
            console.log('⚡ Already moving, ignoring new move request');
            return;
        }

        this.isMoving = true;
        this.updateMovementStatus('Moving');
        const startCoords = { ...this.currentPosition };
        
        console.log('⚡ Movement started:');
        console.log('  - From:', startCoords);
        console.log('  - To:', targetCoords);
        
        // Calculate distance and time
        const distance = this.calculateDistance(
            startCoords.lat, startCoords.lng,
            targetCoords.lat, targetCoords.lng
        );
        
        const travelTime = Math.max(1, distance / this.moveSpeed) * 1000; // Convert to milliseconds
        
        console.log(`⚡ Distance: ${Math.round(distance)}m, Time: ${(travelTime/1000).toFixed(1)}s, Speed: ${this.moveSpeed}m/s`);

        try {
            console.log('⚡ Sending movement to server...');
            // Update server with movement
            const serverResponse = await this.sendMovementToServer(targetCoords);
            console.log('⚡ Server response:', serverResponse);

            try {
                // Update leash UI if present
                if (serverResponse && typeof serverResponse.leash_remaining_m === 'number') {
                    this.updateLeashStatus(serverResponse.leash_remaining_m);
                    // Optional: also surface leash status via dashboard notifications when low
                    if (window.gameApp && typeof window.gameApp.showNotification === 'function' && serverResponse.leash_remaining_m <= 50) {
                        try { window.gameApp.showNotification(`Leash remaining: ${Math.max(0, Math.round(serverResponse.leash_remaining_m))}m`, 'info', 2500); } catch(_) {}
                    }
                }
                // If combat ended due to leaving leash, stop any combat UI/loops
                if (serverResponse && serverResponse.combat_ended && serverResponse.fled) {
                    try { if (typeof window.stopAutoCombat === 'function') window.stopAutoCombat(); } catch (_) {}
                    try { if (typeof window.hideCombatModal === 'function') window.hideCombatModal(); } catch (_) {}
                    if (window.gameApp && typeof window.gameApp.endCombat === 'function') {
                        try { window.gameApp.endCombat({ victory: false, fled: true }); } catch (_) {}
                    }
                    this.showNotification('You left the leash radius. Combat ended (fled).', 'info');
                }
                // If auto-aggro started combat on move, notify and open dashboard combat UI
                if (serverResponse && serverResponse.combat_started) {
                    this.showNotification('An enemy engaged you nearby!', 'warning');
                    if (window.gameApp && typeof window.gameApp.startCombat === 'function') {
                        const c = serverResponse.combat || {};
                        const enemy = {
                            name: (c.enemy && c.enemy.name) || (c.monster && c.monster.name) || c.monster_name || 'Enemy',
                            health: (c.enemy_hp != null ? c.enemy_hp : (c.enemy && (c.enemy.current_hp ?? c.enemy.health))) ?? (c.monster_hp != null ? c.monster_hp : undefined),
                            max_health: (c.enemy && (c.enemy.max_hp ?? c.enemy.max_health)) ?? c.enemy_max_hp ?? (c.monster && c.monster.max_hp) ?? undefined
                        };
                        try { window.gameApp.startCombat({ enemy }); } catch (_) {}
                    }
                }
            } catch (e) {
                console.warn('⚡ Post-move UI update error:', e);
            }

            console.log('⚡ Starting player marker animation...');
            // Animate player marker
            this.animatePlayerMovement(startCoords, targetCoords, travelTime);

            console.log(`⚡ Setting completion timer for ${travelTime}ms`);
            // Update character position after movement completes
            setTimeout(() => {
                console.log('⚡ Movement timer completed, updating position');
                this.currentPosition = targetCoords;
                this.character.lat = targetCoords.lat;
                this.character.lon = targetCoords.lng;
                this.isMoving = false;
                this.updateMovementStatus('Ready');
                
                console.log('⚡ New position:', this.currentPosition);
                
                // Update UI
                this.updateLocationDisplay();
                
                // Check for resources in new location
                // this.checkResourcesAtLocation(); // Disabled to prevent resource markers
                
                console.log('⚡ Movement fully completed');
            }, travelTime);

        } catch (error) {
            console.error('⚡ Movement failed:', error);
            this.isMoving = false;
            this.updateMovementStatus('Error');
        }
    }

    animatePlayerMovement(start, end, duration) {
        console.log('⚡ animatePlayerMovement called:', {
            start,
            end,
            duration,
            hasPlayerMarker: !!this.playerMarker,
            playerMarkerMap: this.playerMarker?._map ? 'attached' : 'not attached'
        });
        
        if (!this.playerMarker) {
            console.error('⚡ No player marker found for animation!');
            return;
        }

        // Check if marker is attached to any map
        if (!this.playerMarker._map) {
            console.error('⚡ Player marker not attached to any map!');
            // Try to attach to available map
            const availableMap = this.worldMap || this.territoryMap;
            if (availableMap && availableMap.loaded()) {
                console.log('⚡ Attempting to attach player marker to map...');
                this.playerMarker.addTo(availableMap);
            } else {
                console.error('⚡ No available map to attach player marker!');
                return;
            }
        }

        const startTime = Date.now();
        let frameCount = 0;
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            frameCount++;
            
            // Linear interpolation
            const currentLat = start.lat + (end.lat - start.lat) * progress;
            const currentLng = start.lng + (end.lng - start.lng) * progress;
            
            // Debug every 10th frame or at start/end
            if (frameCount % 10 === 0 || progress === 0 || progress >= 1) {
                console.log(`⚡ Animation frame ${frameCount}: progress=${progress.toFixed(2)}, pos=[${currentLng.toFixed(6)}, ${currentLat.toFixed(6)}]`);
            }
            
            try {
                this.playerMarker.setLngLat([currentLng, currentLat]);
            } catch (error) {
                console.error('⚡ Error setting marker position:', error);
            }
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                console.log('⚡ Animation completed after', frameCount, 'frames');
            }
        };
        
        console.log('⚡ Starting animation...');
        animate();
    }

    async sendMovementToServer(targetCoords) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.cookie.split('; ')
                             .find(row => row.startsWith('csrftoken='))
                             ?.split('=')[1] || '';

        const response = await fetch('/api/rpg/character/move/', {
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

        let data = null;
        try { data = await response.json(); } catch (_) {}
        if (!response.ok) {
            const msg = (data && (data.error || data.message)) || 'Movement request failed';
            this.showNotification(msg, 'error');
            throw new Error(msg);
        }
        return data || {};
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
            // this.addResourceMarker(resource); // Disabled to prevent red markers
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

    // Clear all flags from both maps
    clearAllFlags() {
        console.log('🚩 Clearing all flags from movement system');
        if (window.flagSystem && window.flagSystem.clearAllFlags) {
            window.flagSystem.clearAllFlags();
        } else {
            console.log('🚩 Flag system not available');
        }
    }

    // Debug methods for troubleshooting
    debugInfo() {
        console.log('⚡ PKMovement Debug Info:');
        console.log('  - Character:', this.character);
        console.log('  - Current Position:', this.currentPosition);
        console.log('  - Is Moving:', this.isMoving);
        console.log('  - Player Marker:', this.playerMarker);
        console.log('  - Player Marker Attached:', this.playerMarker?._map ? 'Yes' : 'No');
        console.log('  - World Map:', this.worldMap ? 'Available' : 'Not Available');
        console.log('  - Territory Map:', this.territoryMap ? 'Available' : 'Not Available');
        console.log('  - World Map Loaded:', this.worldMap?.loaded() ? 'Yes' : 'No');
        console.log('  - Territory Map Loaded:', this.territoryMap?.loaded() ? 'Yes' : 'No');
        return {
            character: this.character,
            currentPosition: this.currentPosition,
            isMoving: this.isMoving,
            hasPlayerMarker: !!this.playerMarker,
            playerMarkerAttached: !!this.playerMarker?._map,
            hasWorldMap: !!this.worldMap,
            hasterritoryMap: !!this.territoryMap,
            worldMapLoaded: this.worldMap?.loaded(),
            territoryMapLoaded: this.territoryMap?.loaded()
        };
    }

    // Force recreate player marker
    recreatePlayerMarker() {
        console.log('⚡ Recreating player marker...');
        
        // Remove existing marker
        if (this.playerMarker && this.playerMarker._map) {
            this.playerMarker.remove();
        }
        
        // Create new marker
        this.createPlayerMarker();
        
        // Attach to available map
        const availableMap = this.worldMap || this.territoryMap;
        if (availableMap && availableMap.loaded()) {
            this.createPlayerMarkerOnMap(availableMap);
            console.log('⚡ Player marker recreated and attached');
        } else {
            console.error('⚡ No available map to attach player marker');
        }
        
        return this.debugInfo();
    }

    // PK Flag Jump System
    async checkFlagAtLocation(coords) {
        try {
            // Check if there's a flag near the clicked location (within 50m)
            const response = await fetch(`/api/flags/nearby/?radius=0.05`, {
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success && data.flags.length > 0) {
                // Find the closest flag to the click
                let closestFlag = null;
                let minDistance = Infinity;
                
                data.flags.forEach(flag => {
                    const distance = this.calculateDistance(
                        coords.lat, coords.lng,
                        flag.lat, flag.lon
                    );
                    
                    // Flag must be within 50m of click and owned by player
                    if (distance < 50 && distance < minDistance && flag.is_mine) {
                        closestFlag = flag;
                        minDistance = distance;
                    }
                });
                
                return closestFlag;
            }
        } catch (error) {
            console.error('⚡ Error checking flag at location:', error);
        }
        return null;
    }

    async flagJumpToLocation(flag) {
        console.log(`🏴 Flag jumping to ${flag.name}`);
        
        this.isMoving = true;
        this.updateMovementStatus('Teleporting');
        const startCoords = { ...this.currentPosition };
        const targetCoords = {
            lat: flag.lat,
            lng: flag.lon
        };
        
        try {
            // Send flag jump to server
            const response = await fetch('/api/rpg/character/jump/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'include',
                body: JSON.stringify({
                    flag_id: flag.id
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Instant teleport animation (no walking)
                this.showNotification(`Teleported to ${flag.name}!`, 'success');
                
                // Immediate position update
                this.currentPosition = targetCoords;
                this.character.lat = targetCoords.lat;
                this.character.lon = targetCoords.lng;
                
                // Update player marker position instantly
                if (this.playerMarker) {
                    this.playerMarker.setLngLat([targetCoords.lng, targetCoords.lat]);
                }
                
                // Update UI
                this.updateLocationDisplay();
                
                // Check for resources at new location
                // this.checkResourcesAtLocation(); // Disabled to prevent resource markers
                
                console.log(`🏴 Flag jump completed to ${flag.name}`);
            } else {
                this.showNotification(data.error || 'Flag jump failed', 'error');
            }
            
        } catch (error) {
            console.error('🏴 Flag jump failed:', error);
            this.showNotification('Flag jump failed', 'error');
        } finally {
            this.isMoving = false;
            this.updateMovementStatus('Ready');
        }
    }

    // Show flag jump menu for multiple flags
    showFlagJumpMenu(availableFlags, clickX, clickY) {
        console.log('🏴 Showing flag jump menu with flags:', availableFlags);
        
        const menu = document.createElement('div');
        menu.className = 'flag-jump-menu';
        menu.style.cssText = `
            position: fixed;
            left: ${clickX}px;
            top: ${clickY}px;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #4CAF50;
            border-radius: 8px;
            padding: 10px;
            z-index: 15000;
            min-width: 200px;
            color: white;
            font-family: Arial, sans-serif;
        `;
        
        let menuHTML = '<div style="font-weight: bold; margin-bottom: 10px; color: #4CAF50;">🏴 Jump to Flag</div>';
        
        availableFlags.forEach(flag => {
            const distance = Math.round(this.calculateDistance(
                this.currentPosition.lat, this.currentPosition.lng,
                flag.lat, flag.lon
            ));
            
            menuHTML += `
                <div class="flag-jump-item" data-flag-id="${flag.id}" 
                     style="padding: 8px; cursor: pointer; border-radius: 4px; margin-bottom: 5px; border: 1px solid transparent;">
                    <span style="color: ${flag.color}; font-weight: bold;">●</span> 
                    ${flag.name} (${distance}m)
                </div>
            `;
        });
        
        menuHTML += '<div class="flag-jump-item" data-action="cancel" style="padding: 8px; cursor: pointer; border-radius: 4px; color: #a0aec0; text-align: center; border-top: 1px solid #666; margin-top: 5px;">Cancel</div>';
        
        menu.innerHTML = menuHTML;
        
        // Add event listeners
        menu.querySelectorAll('.flag-jump-item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.style.background = '#4a5568';
            });
            
            item.addEventListener('mouseleave', () => {
                item.style.background = 'transparent';
            });
            
            item.addEventListener('click', (e) => {
                const flagId = e.target.dataset.flagId;
                const action = e.target.dataset.action;
                
                document.body.removeChild(menu);
                
                if (flagId) {
                    const flag = availableFlags.find(f => f.id == flagId);
                    if (flag) {
                        this.flagJumpToLocation(flag);
                    }
                }
            });
        });
        
        document.body.appendChild(menu);
        
        // Remove menu when clicking elsewhere
        setTimeout(() => {
            const removeOnClick = (e) => {
                if (!menu.contains(e.target)) {
                    if (menu.parentNode) {
                        document.body.removeChild(menu);
                    }
                    document.removeEventListener('click', removeOnClick);
                }
            };
            document.addEventListener('click', removeOnClick);
        }, 100);
    }

    // Show all available flags for jumping (F key)
    async showAllFlagsMenu() {
        console.log('🏴 Showing all flags menu');
        
        try {
            // Get all player's flags
            const response = await fetch('/api/flags/nearby/?radius=10.0', { // Larger radius to get all flags
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success && data.flags.length > 0) {
                const myFlags = data.flags.filter(flag => flag.is_mine);
                
                if (myFlags.length === 0) {
                    this.showNotification('No flags available for jumping!\nPlace some flags first.', 'error');
                    return;
                }
                
                // Show flag jump menu in center of screen
                const centerX = window.innerWidth / 2;
                const centerY = window.innerHeight / 2;
                
                this.showFlagJumpMenu(myFlags, centerX - 100, centerY - 100);
            } else {
                this.showNotification('No flags found!\nPlace some flags first.', 'error');
            }
            
        } catch (error) {
            console.error('🏴 Error loading flags for jump menu:', error);
            this.showNotification('Failed to load flags', 'error');
        }
    }

    // Create status display UI
    createStatusDisplay() {
        const statusDisplay = document.createElement('div');
        statusDisplay.id = 'pk-status-display';
        statusDisplay.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 25000;
            min-width: 200px;
            border: 2px solid #4CAF50;
        `;
        
        statusDisplay.innerHTML = `
            <div style="font-weight: bold; color: #4CAF50; margin-bottom: 10px;">
                ⚡ PK Movement Status
            </div>
            <div>Status: <span id="movement-status">Ready</span></div>
            <div>Position: <span id="current-coords">${this.character.lat.toFixed(3)}, ${this.character.lon.toFixed(3)}</span></div>
            <div>Flags: <span id="flag-count">Loading...</span></div>
            <div>Leash: <span id="leash-remaining">—</span></div>
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #666;">
                <button onclick="window.pkMovement.showAllFlagsMenu()" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    margin-right: 5px;
                ">🏴 Jump</button>
                <button onclick="window.pkMovement.showHelpOverlay()" style="
                    background: #2196F3;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                ">? Help</button>
            </div>
        `;
        
        document.body.appendChild(statusDisplay);
        
        // Update flag count
        this.updateFlagCount();
    }

    // Create help overlay
    createHelpOverlay() {
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key.toLowerCase() === 'h' && e.ctrlKey) {
                e.preventDefault();
                this.showHelpOverlay();
            }
            if (e.key === 'Escape') {
                this.hideHelpOverlay();
            }
        });
    }

    showHelpOverlay() {
        // Remove existing help overlay
        this.hideHelpOverlay();
        
        const helpOverlay = document.createElement('div');
        helpOverlay.id = 'pk-help-overlay';
        helpOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 50000;
        `;
        
        helpOverlay.innerHTML = `
            <div style="
                background: #2d3748;
                border-radius: 12px;
                padding: 30px;
                max-width: 600px;
                width: 90%;
                color: white;
                font-family: Arial, sans-serif;
                max-height: 80vh;
                overflow-y: auto;
            ">
                <h2 style="margin: 0 0 20px 0; color: #4CAF50; text-align: center;">
                    🏰 Parallel Kingdom Movement Guide
                </h2>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700; margin-bottom: 10px;">⚡ Movement System</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong>Walking:</strong> Click within 100 meters to walk</li>
                        <li><strong>Flag Jump:</strong> Click on your 🏴 flag markers for instant teleport</li>
                        <li><strong>Distance Limit:</strong> Cannot walk beyond 100m - use flags to expand reach</li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700; margin-bottom: 10px;">🏴 Flag System</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong>Place Flags:</strong> Right-click on map to place new flags</li>
                        <li><strong>Flag Network:</strong> Build connected flag networks for long-distance travel</li>
                        <li><strong>Territories:</strong> Flags create territories that spawn resources</li>
                        <li><strong>Strategic Placement:</strong> Place flags to expand your movement range</li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700; margin-bottom: 10px;">⌨️ Keyboard Shortcuts</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li><strong>F:</strong> Open flag jump menu</li>
                        <li><strong>Ctrl+H:</strong> Show this help</li>
                        <li><strong>Escape:</strong> Close menus/help</li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700; margin-bottom: 10px;">🎮 Game Tips</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        <li>Build flag networks to access distant areas</li>
                        <li>Each flag costs 100 gold - plan strategically</li>
                        <li>Territories around flags spawn resources</li>
                        <li>Right-click to place flags, left-click to move/jump</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="window.pkMovement.hideHelpOverlay()" style="
                        background: #4CAF50;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 16px;
                    ">Got it!</button>
                </div>
            </div>
        `;
        
        // Close on background click
        helpOverlay.addEventListener('click', (e) => {
            if (e.target === helpOverlay) {
                this.hideHelpOverlay();
            }
        });
        
        document.body.appendChild(helpOverlay);
    }

    hideHelpOverlay() {
        const helpOverlay = document.getElementById('pk-help-overlay');
        if (helpOverlay) {
            helpOverlay.remove();
        }
    }

    // Update status display
    updateMovementStatus(status) {
        const statusElement = document.getElementById('movement-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.style.color = status === 'Moving' ? '#FFD700' : status === 'Ready' ? '#4CAF50' : '#ff6b6b';
        }
    }

    updateLocationDisplay() {
        // Update original location elements
        const locationElements = document.querySelectorAll('.pk-stat-value');
        locationElements.forEach(el => {
            if (el.textContent.includes(',')) {
                el.textContent = `${this.character.lat.toFixed(3)},${this.character.lon.toFixed(3)}`;
            }
        });
        
        // Update status display coordinates
        const coordsElement = document.getElementById('current-coords');
        if (coordsElement) {
            coordsElement.textContent = `${this.character.lat.toFixed(3)}, ${this.character.lon.toFixed(3)}`;
        }
    }

    updateLeashStatus(metersRemaining) {
        try {
            const el = document.getElementById('leash-remaining');
            if (!el) return;
            if (typeof metersRemaining === 'number') {
                const val = Math.max(0, Math.round(metersRemaining));
                el.textContent = `${val} m`;
                el.style.color = val < 50 ? '#f59e0b' : '#e5e7eb';
            } else {
                el.textContent = '—';
                el.style.color = '#e5e7eb';
            }
        } catch (_) {}
    }

    async updateFlagCount() {
        try {
            const response = await fetch('/api/flags/nearby/?radius=10.0', {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.success) {
                const myFlagCount = data.flags.filter(flag => flag.is_mine).length;
                const flagCountElement = document.getElementById('flag-count');
                if (flagCountElement) {
                    flagCountElement.textContent = myFlagCount;
                    flagCountElement.style.color = myFlagCount > 0 ? '#4CAF50' : '#ff6b6b';
                }
            }
        } catch (error) {
            console.error('Error updating flag count:', error);
        }
    }
}

// Initialize when DOM is ready
window.PKMovementSystem = PKMovementSystem;
