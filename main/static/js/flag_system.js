/**
 * Simple Flag Placement System
 * Integrates with existing right-click detection for flag placement and upgrades
 */

class SimpleFlagSystem {
    constructor() {
        this.flags = new Map();
        this.flagMarkers = new Map();
        this.init();
    }

    init() {
        console.log('🚩 Simple Flag System initialized');
        console.log('🚩 Flag Placement: Right-click on map to place flags (PK-style)');
        this.loadNearbyFlags();
        
        // Hook into existing right-click detection
        this.setupRightClickHandler();
        
        // Show instruction notification
        setTimeout(() => {
            this.showNotification('Flag System Active: Right-click on map to place flags', 'info');
        }, 2000);
        
        // Refresh flags periodically
        setInterval(() => {
            this.loadNearbyFlags();
        }, 30000); // Every 30 seconds
    }

    setupRightClickHandler() {
        // Listen for right-click events from the PK game grid
        document.addEventListener('contextmenu', (e) => {
            // Check if we're on the PK game view or game grid
            const gameContainer = e.target.closest('#pk-map, #territory-map, .pk-content-area, .pk-game-container');
            if (gameContainer) {
                console.log('🚩 Right-click detected on PK game grid');
                // Prevent the default browser context menu
                e.preventDefault();
                e.stopPropagation();
                
                // Show our flag placement menu immediately
                this.handleGameGridRightClick(e);
                return false;
            }
        });
        
        // Also setup for mobile
        this.setupMobileTouchHandler();
    }
    
    setupMobileTouchHandler() {
        let touchCount = 0;
        let touchTimer = null;
        let lastTouchEnd = 0;
        
        document.addEventListener('touchend', (e) => {
            // Check if we're on the PK game grid
            const gameContainer = e.target.closest('#pk-map, #territory-map, .pk-content-area, .pk-game-container');
            if (gameContainer) {
                const now = Date.now();
                
                // Prevent accidental triggers
                if (now - lastTouchEnd < 100) {
                    return;
                }
                lastTouchEnd = now;
                
                touchCount++;
                
                if (touchCount === 1) {
                    touchTimer = setTimeout(() => {
                        // Single tap - do nothing for flags
                        touchCount = 0;
                    }, 400);
                } else if (touchCount === 2) {
                    // Double tap detected
                    clearTimeout(touchTimer);
                    touchCount = 0;
                    
                    // Create a synthetic event for double tap
                    const touch = e.changedTouches[0];
                    const syntheticEvent = {
                        clientX: touch.clientX,
                        clientY: touch.clientY,
                        target: e.target
                    };
                    
                    this.handleGameGridRightClick(syntheticEvent);
                }
            }
        });
    }

    handleGameGridRightClick(event) {
        console.log('🚩 Right-click detected on PK game grid');
        
        // Get the MapBox map instance
        const map = window.worldMap || window.territoryMap;
        
        if (map) {
            // Use MapBox's unproject method to get proper geographic coordinates
            const rect = (document.getElementById('pk-map') || document.getElementById('territory-map')).getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Convert pixel coordinates to geographic coordinates using MapBox
            const lngLat = map.unproject([x, y]);
            console.log(`🚩 Converted click to coordinates: ${lngLat.lat}, ${lngLat.lng}`);
            
            // Show flag placement menu
            this.showFlagPlacementMenu(event.clientX, event.clientY, lngLat.lat, lngLat.lng);
        } else {
            console.warn('🚩 No map instance available for coordinate conversion');
            // Fallback to simulated coordinates
            const gameView = document.getElementById('pk-map') || document.getElementById('territory-map') || document.querySelector('.pk-content-area');
            const gameRect = gameView.getBoundingClientRect();
            const relativeX = (event.clientX - gameRect.left) / gameRect.width;
            const relativeY = (event.clientY - gameRect.top) / gameRect.height;
            
            // Convert to coordinates based on player's actual position
            let simulatedLat, simulatedLng;
            if (window.character) {
                // Use actual player's position as base and add small offset based on click position
                // Convert click offset to a more reasonable distance (max ~200m in any direction)
                const offsetLat = (relativeY - 0.5) * 0.002; // ~200m max offset
                const offsetLng = (relativeX - 0.5) * 0.002; // ~200m max offset
                simulatedLat = window.character.lat + offsetLat;
                simulatedLng = window.character.lon + offsetLng;
                console.log(`🚩 Using player position: ${window.character.lat}, ${window.character.lon}`);
                console.log(`🚩 Click offset: ${offsetLat}, ${offsetLng}`);
                console.log(`🚩 Final coordinates: ${simulatedLat}, ${simulatedLng}`);
            } else {
                // Fallback coordinates if character data not available
                simulatedLat = 40.7589 + (relativeY - 0.5) * 0.001;
                simulatedLng = -73.9851 + (relativeX - 0.5) * 0.001;
                console.log('🚩 No character data available, using fallback coordinates');
            }
            
            // Show flag placement menu
            this.showFlagPlacementMenu(event.clientX, event.clientY, simulatedLat, simulatedLng);
        }
    }
    
    addFlagOptionToExistingMenu(existingMenu, event) {
        console.log('🚩 Adding flag option to existing context menu');
        
        // Get coordinates
        const rect = event.target.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const lngLat = window.map.unproject([x, y]);
        
        // Create flag menu item
        const flagItem = document.createElement('div');
        flagItem.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            border-top: 1px solid #4a5568;
            color: white;
            background: rgba(0,0,0,0.8);
            font-size: 14px;
        `;
        flagItem.innerHTML = '🚩 Place Flag';
        
        flagItem.addEventListener('click', (e) => {
            e.stopPropagation();
            // Remove the existing menu
            existingMenu.remove();
            // Show flag placement dialog
            this.showFlagPlacementDialog(lngLat.lat, lngLat.lng);
        });
        
        flagItem.addEventListener('mouseenter', () => {
            flagItem.style.background = 'rgba(74, 85, 104, 0.8)';
        });
        
        flagItem.addEventListener('mouseleave', () => {
            flagItem.style.background = 'rgba(0,0,0,0.8)';
        });
        
        // Add to existing menu
        existingMenu.appendChild(flagItem);
    }
    
    createPKStyleContextMenu(event) {
        console.log('🚩 Creating PK-style context menu');
        
        // Get coordinates
        const rect = event.target.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const lngLat = window.map.unproject([x, y]);
        
        // Create PK-style context menu
        this.showFlagPlacementMenu(event.clientX, event.clientY, lngLat.lat, lngLat.lng);
    }
    
    // Method no longer needed for PK game - remove it
    // handleDoubleRightClick is replaced by handleGameGridRightClick
    
    showDoubleClickFeedback(x, y) {
        // Create a visual indicator for the double right-click
        const indicator = document.createElement('div');
        indicator.style.cssText = `
            position: fixed;
            left: ${x - 15}px;
            top: ${y - 15}px;
            width: 30px;
            height: 30px;
            background: rgba(255, 68, 68, 0.8);
            border: 2px solid #ff4444;
            border-radius: 50%;
            z-index: 15000;
            pointer-events: none;
            animation: flagPulse 0.6s ease-out;
        `;
        
        document.body.appendChild(indicator);
        
        // Remove after animation
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 600);
    }

    showFlagPlacementMenu(x, y, lat, lon) {
        // Remove any existing menu
        this.removeFlagMenu();
        
        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'flag-context-menu';
        menu.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #4a5568;
            border-radius: 8px;
            padding: 10px;
            z-index: 10000;
            min-width: 200px;
            color: white;
            font-family: Arial, sans-serif;
        `;
        
        menu.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px; color: #f7fafc;">🚩 Flag Actions</div>
            <div class="flag-menu-item" data-action="place" style="padding: 8px; cursor: pointer; border-radius: 4px; margin-bottom: 5px;">
                📍 Place Flag (100 gold)
            </div>
            <div class="flag-menu-item" data-action="cancel" style="padding: 8px; cursor: pointer; border-radius: 4px; color: #a0aec0;">
                ❌ Cancel
            </div>
        `;
        
        // Style menu items
        const menuItems = menu.querySelectorAll('.flag-menu-item');
        menuItems.forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.style.background = '#4a5568';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = 'transparent';
            });
            
            item.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.removeFlagMenu();
                
                if (action === 'place') {
                    // Check if location is valid before showing dialog
                    this.checkCanPlaceFlag(lat, lon).then(canPlace => {
                        if (canPlace.can_place) {
                            this.showFlagPlacementDialog(lat, lon);
                        } else {
                            this.showNotification(canPlace.message, 'error');
                        }
                    });
                }
            });
        });
        
        document.body.appendChild(menu);
        
        // Remove menu when clicking elsewhere
        setTimeout(() => {
            const removeOnClick = (e) => {
                if (!menu.contains(e.target)) {
                    this.removeFlagMenu();
                    document.removeEventListener('click', removeOnClick);
                }
            };
            document.addEventListener('click', removeOnClick);
        }, 100);
    }

    showFlagPlacementDialog(lat, lon) {
        // Create modal dialog
        const modal = document.createElement('div');
        modal.className = 'flag-placement-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 20000;
        `;
        
        modal.innerHTML = `
            <div style="background: #2d3748; border-radius: 12px; padding: 20px; max-width: 400px; width: 90%; color: white;">
                <h3 style="margin: 0 0 20px 0; color: #f7fafc;">🚩 Place New Flag</h3>
                
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; color: #a0aec0;">Flag Name:</label>
                    <input type="text" id="flag-name" value="My Flag" maxlength="20" 
                           style="width: 100%; padding: 8px; border: none; border-radius: 4px; background: #4a5568; color: white;">
                </div>
                
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; color: #a0aec0;">Flag Color:</label>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <div class="color-option" data-color="#ff4444" style="width: 30px; height: 30px; background: #ff4444; border-radius: 4px; cursor: pointer; border: 2px solid transparent;"></div>
                        <div class="color-option" data-color="#ff8844" style="width: 30px; height: 30px; background: #ff8844; border-radius: 4px; cursor: pointer; border: 2px solid transparent;"></div>
                        <div class="color-option" data-color="#ffdd44" style="width: 30px; height: 30px; background: #ffdd44; border-radius: 4px; cursor: pointer; border: 2px solid transparent;"></div>
                        <div class="color-option" data-color="#44ff44" style="width: 30px; height: 30px; background: #44ff44; border-radius: 4px; cursor: pointer; border: 2px solid transparent;"></div>
                        <div class="color-option" data-color="#4444ff" style="width: 30px; height: 30px; background: #4444ff; border-radius: 4px; cursor: pointer; border: 2px solid transparent;"></div>
                    </div>
                </div>
                
                <div style="margin-bottom: 20px; padding: 10px; background: #4a5568; border-radius: 4px; font-size: 14px;">
                    <strong>Cost:</strong> 100 gold<br>
                    <strong>Location:</strong> ${lat.toFixed(6)}, ${lon.toFixed(6)}
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="flag-cancel" style="padding: 10px 20px; background: #718096; border: none; border-radius: 4px; color: white; cursor: pointer;">
                        Cancel
                    </button>
                    <button id="flag-place" style="padding: 10px 20px; background: #38a169; border: none; border-radius: 4px; color: white; cursor: pointer;">
                        Place Flag
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Handle color selection
        let selectedColor = '#ff4444'; // Default red
        modal.querySelectorAll('.color-option').forEach(option => {
            option.addEventListener('click', () => {
                // Remove previous selection
                modal.querySelectorAll('.color-option').forEach(opt => opt.style.border = '2px solid transparent');
                // Select new color
                option.style.border = '2px solid white';
                selectedColor = option.dataset.color;
            });
        });
        
        // Select first color by default
        modal.querySelector('.color-option').style.border = '2px solid white';
        
        // Handle buttons
        modal.querySelector('#flag-cancel').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.querySelector('#flag-place').addEventListener('click', () => {
            const name = modal.querySelector('#flag-name').value.trim() || 'My Flag';
            document.body.removeChild(modal);
            this.placeFlag(lat, lon, name, selectedColor);
        });
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    async placeFlag(lat, lon, name, color) {
        try {
            console.log(`🚩 Placing flag "${name}" at ${lat}, ${lon} with color ${color}`);
            
            const response = await fetch('/api/flags/place/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'include',
                body: JSON.stringify({
                    lat: lat,
                    lon: lon,
                    name: name,
                    color: color
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('🚩 Flag placed successfully:', data);
                this.showNotification(data.message, 'success');
                
                // Add flag to our local cache
                this.addFlag(data.flag);
                
                // Reload nearby flags to get updated data
                setTimeout(() => this.loadNearbyFlags(), 1000);
            } else {
                console.error('❌ Failed to place flag:', data.error);
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error placing flag:', error);
            this.showNotification('Failed to place flag. Please try again.', 'error');
        }
    }

    async loadNearbyFlags() {
        try {
            // Load flag data
            const response = await fetch('/api/flags/nearby/?radius=1.0', {
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`🚩 Loaded ${data.flags.length} nearby flags`);
                
                // Clear existing flags
                this.clearFlagMarkers();
                this.flags.clear();
                
                // Add new flags
                data.flags.forEach(flag => {
                    this.addFlag(flag);
                });
            }
            
            // Also load territory visualization if we have a map
            this.loadTerritoryCircles();
            
        } catch (error) {
            console.error('❌ Error loading flags:', error);
        }
    }

    addFlag(flagData) {
        this.flags.set(flagData.id, flagData);
        this.createFlagMarker(flagData);
    }

    createFlagMarker(flag) {
        console.log('🚩 Creating flag marker for PK game grid:', flag);
        
        // For PK game, we'll display flags in a simplified way since there's no real map
        // We'll add them to the nearby info or create a flag list
        this.updateFlagDisplay(flag);
    }
    
    updateFlagDisplay(flag) {
        // Update the nearby flags counter if it exists
        const nearbyFlagsElement = document.getElementById('nearby-flags');
        if (nearbyFlagsElement) {
            nearbyFlagsElement.textContent = this.flags.size;
        }
        
        // Add flag to nearby info display
        const nearbyInfo = document.getElementById('nearby-info');
        if (nearbyInfo) {
            const existingFlagInfo = nearbyInfo.querySelector('.flag-info-section');
            if (existingFlagInfo) {
                existingFlagInfo.remove();
            }
            
            if (this.flags.size > 0) {
                const flagInfo = document.createElement('div');
                flagInfo.className = 'flag-info-section';
                flagInfo.style.cssText = `
                    margin-top: 10px;
                    padding: 10px;
                    background: rgba(255, 68, 68, 0.1);
                    border: 1px solid #ff4444;
                    border-radius: 4px;
                `;
                
                let flagHTML = `<strong style="color: #ff4444;">🚩 Nearby Flags (${this.flags.size})</strong><br>`;
                
                Array.from(this.flags.values()).forEach(f => {
                    const ownerText = f.is_mine ? '<span style="color: #4CAF50;">(Yours)</span>' : '';
                    flagHTML += `<div style="margin: 5px 0; padding: 5px; background: rgba(0,0,0,0.2); border-radius: 3px; cursor: pointer;" 
                                      onclick="window.flagSystem.showFlagInfo({id: ${f.id}, name: '${f.name}', owner: '${f.owner}', level: ${f.level}, is_mine: ${f.is_mine}, hp: ${f.hp || 100}, max_hp: ${f.max_hp || 100}, status: '${f.status || 'Active'}', distance: '${f.distance || 0}', can_upgrade: ${f.can_upgrade || false}, upgrade_cost: ${f.upgrade_cost ? JSON.stringify(f.upgrade_cost) : '{}'}})">
                        <span style="color: ${f.color}; font-weight: bold;">●</span> 
                        ${f.name} (L${f.level}) - ${f.owner} ${ownerText}
                    </div>`;
                });
                
                flagInfo.innerHTML = flagHTML;
                nearbyInfo.appendChild(flagInfo);
            }
        }
    }

    showFlagInfo(flag) {
        console.log('🚩 Showing info for flag:', flag);
        
        const modal = document.createElement('div');
        modal.className = 'flag-info-modal';
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #4a5568;
            border-radius: 12px;
            padding: 20px;
            z-index: 20000;
            min-width: 300px;
            color: white;
        `;
        
        const canUpgrade = flag.is_mine && flag.can_upgrade;
        const upgradeInfo = canUpgrade ? 
            `<div style="margin-top: 10px; padding: 10px; background: #2d5016; border-radius: 4px;">
                <strong>Upgrade Available!</strong><br>
                Cost: ${flag.upgrade_cost ? flag.upgrade_cost.gold : 'N/A'} gold<br>
                <button id="upgrade-flag" style="margin-top: 5px; padding: 5px 10px; background: #38a169; border: none; border-radius: 4px; color: white; cursor: pointer;">
                    Upgrade to Level ${flag.level + 1}
                </button>
            </div>` : '';
        
        modal.innerHTML = `
            <h3 style="margin: 0 0 15px 0; color: #f7fafc;">🚩 ${flag.name}</h3>
            <div><strong>Owner:</strong> ${flag.owner} ${flag.is_mine ? '(You)' : ''}</div>
            <div><strong>Level:</strong> ${flag.level}/5</div>
            <div><strong>HP:</strong> ${flag.hp}/${flag.max_hp}</div>
            <div><strong>Status:</strong> ${flag.status}</div>
            <div><strong>Distance:</strong> ${flag.distance}m</div>
            ${upgradeInfo}
            <div style="margin-top: 15px; text-align: right;">
                <button id="close-flag-info" style="padding: 8px 16px; background: #718096; border: none; border-radius: 4px; color: white; cursor: pointer;">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Handle upgrade button
        const upgradeButton = modal.querySelector('#upgrade-flag');
        if (upgradeButton) {
            upgradeButton.addEventListener('click', () => {
                document.body.removeChild(modal);
                this.upgradeFlag(flag.id);
            });
        }
        
        // Handle close button
        modal.querySelector('#close-flag-info').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    }

    async upgradeFlag(flagId) {
        try {
            const response = await fetch(`/api/flags/upgrade/${flagId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.loadNearbyFlags(); // Reload to get updated flag data
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Error upgrading flag:', error);
            this.showNotification('Failed to upgrade flag', 'error');
        }
    }

    clearFlagMarkers() {
        // For PK game, just clear the flag display info
        const nearbyInfo = document.getElementById('nearby-info');
        if (nearbyInfo) {
            const existingFlagInfo = nearbyInfo.querySelector('.flag-info-section');
            if (existingFlagInfo) {
                existingFlagInfo.remove();
            }
        }
        this.flagMarkers.clear();
    }

    removeFlagMenu() {
        const existingMenu = document.querySelector('.flag-context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
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
    
    async checkCanPlaceFlag(lat, lon) {
        try {
            const response = await fetch('/api/flags/can-place/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'include',
                body: JSON.stringify({
                    lat: lat,
                    lon: lon
                })
            });
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('❌ Error checking flag placement:', error);
            return { can_place: false, message: 'Error checking placement validity' };
        }
    }
    
    async loadTerritoryCircles() {
        try {
            // Check if we have access to a MapBox map instance
            const map = window.worldMap || window.territoryMap;
            if (!map) {
                console.log('🚩 No map instance available for territory visualization');
                return;
            }
            
            // Get territory GeoJSON data
            const response = await fetch('/api/flags/territories/geojson/?radius=2.0', {
                credentials: 'include'
            });
            
            const data = await response.json();
            console.log('🚩 Territory GeoJSON response:', data);
            
            if (data.success && data.geojson) {
                console.log(`🚩 Processing ${data.geojson.features.length} territory features`);
                // Remove existing territory layers
                if (map.getLayer('flag-territories-fill')) {
                    map.removeLayer('flag-territories-fill');
                }
                if (map.getLayer('flag-territories-border')) {
                    map.removeLayer('flag-territories-border');
                }
                if (map.getSource('flag-territories')) {
                    map.removeSource('flag-territories');
                }
                
                // Add territory source
                map.addSource('flag-territories', {
                    type: 'geojson',
                    data: data.geojson
                });
                
                // Add territory fill layer (transparent colored circles)
                map.addLayer({
                    id: 'flag-territories-fill',
                    type: 'fill',
                    source: 'flag-territories',
                    paint: {
                        'fill-color': [
                            'case',
                            ['get', 'is_own'],
                            '#4CAF50',  // Green for own territories
                            ['get', 'flag_color']  // Use flag color for others
                        ],
                        'fill-opacity': [
                            'case',
                            ['get', 'is_own'],
                            0.2,  // Less transparent for own territories
                            0.1   // More transparent for others
                        ]
                    }
                });
                
                // Add territory border layer
                map.addLayer({
                    id: 'flag-territories-border',
                    type: 'line',
                    source: 'flag-territories',
                    paint: {
                        'line-color': [
                            'case',
                            ['get', 'is_own'],
                            '#4CAF50',  // Green border for own territories
                            ['get', 'flag_color']  // Use flag color for others
                        ],
                        'line-width': [
                            'case',
                            ['get', 'is_own'],
                            2,  // Thicker border for own territories
                            1   // Thin border for others
                        ],
                        'line-opacity': 0.6
                    }
                });
                
                // Add click handler for territories
                map.on('click', 'flag-territories-fill', (e) => {
                    const properties = e.features[0].properties;
                    this.showTerritoryPopup(e.lngLat, properties);
                });
                
                // Change cursor on hover
                map.on('mouseenter', 'flag-territories-fill', () => {
                    map.getCanvas().style.cursor = 'pointer';
                });
                
                map.on('mouseleave', 'flag-territories-fill', () => {
                    map.getCanvas().style.cursor = '';
                });
                
                console.log(`🚩 Loaded ${data.geojson.features.length} territory circles`);
            }
        } catch (error) {
            console.error('❌ Error loading territory circles:', error);
        }
    }
    
    showTerritoryPopup(lngLat, properties) {
        const popup = new mapboxgl.Popup()
            .setLngLat(lngLat)
            .setHTML(`
                <div style="padding: 10px;">
                    <h4 style="margin: 0 0 10px 0; color: ${properties.flag_color};">
                        🚩 ${properties.name}
                    </h4>
                    <p style="margin: 5px 0;"><strong>Owner:</strong> ${properties.owner} ${properties.is_own ? '(You)' : ''}</p>
                    <p style="margin: 5px 0;"><strong>Level:</strong> ${properties.level}/5</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> ${properties.status}</p>
                    <p style="margin: 5px 0;"><strong>Radius:</strong> ${properties.radius_meters}m</p>
                </div>
            `)
            .addTo(window.worldMap || window.territoryMap);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    @keyframes flagPulse {
        0% {
            transform: scale(0.5);
            opacity: 1;
        }
        50% {
            transform: scale(1.2);
            opacity: 0.7;
        }
        100% {
            transform: scale(1.5);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize flag system when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.flagSystem = new SimpleFlagSystem();
    });
} else {
    window.flagSystem = new SimpleFlagSystem();
}
