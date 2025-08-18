/**
 * TerritoryManager - Parallel Kingdom style territory management system
 * Handles territory flags, map visualization, combat, and economy
 */
class TerritoryManager {
    constructor(options = {}) {
        this.mapInstance = options.mapInstance;
        this.character = options.character || {};
        this.apiBaseUrl = '/api/flags';
        
        // Territory data
        this.territories = new Map();
        this.territoryZones = new Map();
        this.combatLogs = [];
        this.revenueStats = {};
        
        // Map layers
        this.territoryLayer = null;
        this.flagMarkers = new Map();
        this.territoryCircles = new Map();
        
        // UI state
        this.selectedTerritory = null;
        this.placementMode = false;
        this.placementPreview = null;
        this.isPlacing = false; // Prevent rapid multiple placements
        
        // Settings
        this.autoRefreshInterval = 30000; // 30 seconds
        this.autoCollectRevenue = true;
        this.autoPayUpkeep = false;
        
        // Timers
        this.refreshTimer = null;
        this.upkeepCheckTimer = null;
        
        // Event handlers (store references for cleanup)
        this.mapClickHandler = null;
        this.mapMoveHandler = null;
        
        console.log('🏴 Territory Manager initialized with character:', this.character.name);
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing Territory Manager...');
        
        // First, completely clear the map of any leftover flags
        this.performCompleteMapCleanup();
        
        // Load territories fresh from database
        await this.loadTerritories();
        
        // Start periodic updates
        this.startPeriodicUpdates();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Setup map integration
        if (this.mapInstance) {
            this.setupMapIntegration();
        }
        
        console.log(`✅ Territory Manager initialized with ${this.territories.size} territories`);
    }
    
    async loadTerritories() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/nearby/?radius=10`);
            const data = await response.json();
            
            if (data.success) {
                // Clear existing territories
                this.territories.clear();
                this.clearMapMarkers();
                
                // Load new territories
                for (const flag of data.flags) {
                    await this.addTerritoryToMap(flag);
                    this.territories.set(flag.id, flag);
                }
                
                this.updateTerritoryUI();
                this.calculateEconomyStats();
                
                this.showNotification(`Loaded ${data.flags.length} territories`, 'success');
            }
        } catch (error) {
            console.error('Failed to load territories:', error);
            this.showNotification('Failed to load territories', 'error');
        }
    }
    
    async addTerritoryToMap(territory) {
        if (!this.mapInstance) return;
        
        // Create flag marker
        const flagElement = this.createFlagMarker(territory);
        const marker = new mapboxgl.Marker(flagElement)
            .setLngLat([territory.lon, territory.lat])
            .addTo(this.mapInstance);
        
        // Store marker reference
        this.flagMarkers.set(territory.id, marker);
        
        // Create territory circle if it's active
        if (territory.status === 'active') {
            console.log('Territory is active, adding circle for:', territory.name);
            this.addTerritoryCircle(territory);
        } else {
            console.log('Territory not active, status:', territory.status, 'for:', territory.name);
        }
        
        // Add click handler with debugging
        flagElement.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Flag clicked:', territory.name);
            this.selectTerritory(territory.id);
        });
    }
    
    createFlagMarker(territory) {
        const element = document.createElement('div');
        element.className = 'territory-flag-marker';
        
        // Determine marker style based on ownership and status
        let markerClass = 'flag-marker';
        let iconClass = 'fas fa-flag';
        let statusClass = '';
        
        if (territory.is_mine) {
            markerClass += ' flag-owned';
            statusClass = 'owned';
        } else {
            markerClass += ' flag-enemy';
            statusClass = 'enemy';
        }
        
        // Status indicators
        const statusIcons = {
            'active': 'fas fa-flag',
            'damaged': 'fas fa-flag text-warning',
            'capturable': 'fas fa-flag text-danger',
            'decayed': 'fas fa-flag-checkered',
            'upgrading': 'fas fa-hammer text-info'
        };
        
        iconClass = statusIcons[territory.status] || 'fas fa-flag';
        
        const flagColor = territory.flag_color?.hex_color || '#FF4444';
        
        element.innerHTML = `
            <div class="${markerClass} level-${territory.level}" 
                 data-territory-id="${territory.id}"
                 style="--flag-color: ${flagColor}">
                <div class="flag-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="flag-level">${territory.level}</div>
                <div class="flag-status ${statusClass}">${territory.status}</div>
            </div>
        `;
        
        // Add popup with debugging
        const popupContent = this.createTerritoryPopupContent(territory);
        const popup = new mapboxgl.Popup({ offset: 25, closeButton: false })
            .setHTML(popupContent);
        marker.setPopup(popup);
        
        console.log('Flag marker created for:', territory.name, 'at', territory.lat, territory.lon);
        
        return element;
    }
    
    createTerritoryPopupContent(territory) {
        const isOwned = territory.is_mine;
        const distanceText = territory.distance_meters ? 
            `${Math.round(territory.distance_meters)}m away` : '';
        
        let actionButtons = '';
        if (isOwned) {
            actionButtons = `
                <button onclick="territoryManager.collectRevenue('${territory.id}')" class="btn-mini btn-success">
                    💰 Collect
                </button>
                <button onclick="territoryManager.openTerritoryDetails('${territory.id}')" class="btn-mini btn-primary">
                    ⚙️ Manage
                </button>
            `;
        } else {
            if (territory.distance_meters <= territory.radius_meters) {
                actionButtons = `
                    <button onclick="territoryManager.attackTerritory('${territory.id}')" class="btn-mini btn-danger">
                        ⚔️ Attack
                    </button>
                `;
            }
        }
        
        return `
            <div class="territory-popup">
                <h4>${territory.name}</h4>
                <div class="territory-info">
                    <p><strong>Owner:</strong> ${territory.owner}</p>
                    <p><strong>Level:</strong> ${territory.level}</p>
                    <p><strong>Status:</strong> <span class="status-${territory.status}">${territory.status}</span></p>
                    <p><strong>Range:</strong> ${territory.radius_meters}m</p>
                    ${distanceText ? `<p><strong>Distance:</strong> ${distanceText}</p>` : ''}
                </div>
                <div class="territory-actions">
                    ${actionButtons}
                </div>
            </div>
        `;
    }
    
    addTerritoryCircle(territory) {
        if (!this.mapInstance) return;
        
        console.log('🔴 Adding territory circle for:', territory.name, 'at', territory.lat, territory.lon, 'radius:', territory.radius_meters);
        
        // Create GeoJSON circle
        const center = [territory.lon, territory.lat];
        const radiusKm = territory.radius_meters / 1000;
        const points = this.createCirclePoints(center, radiusKm);
        
        const circleId = `territory-circle-${territory.id}`;
        const sourceId = `territory-source-${territory.id}`;
        
        // Check if source already exists and remove it
        if (this.mapInstance.getSource(sourceId)) {
            console.log('Removing existing source:', sourceId);
            if (this.mapInstance.getLayer(circleId)) {
                this.mapInstance.removeLayer(circleId);
            }
            if (this.mapInstance.getLayer(`${circleId}-border`)) {
                this.mapInstance.removeLayer(`${circleId}-border`);
            }
            this.mapInstance.removeSource(sourceId);
        }
        
        // Add source
        this.mapInstance.addSource(sourceId, {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [points]
                }
            }
        });
        
        // Add circle layer
        this.mapInstance.addLayer({
            id: circleId,
            type: 'fill',
            source: sourceId,
            paint: {
                'fill-color': territory.is_mine ? '#4CAF50' : '#F44336',
                'fill-opacity': territory.is_mine ? 0.2 : 0.1
            }
        });
        
        // Add border
        this.mapInstance.addLayer({
            id: `${circleId}-border`,
            type: 'line',
            source: sourceId,
            paint: {
                'line-color': territory.is_mine ? '#4CAF50' : '#F44336',
                'line-width': 2,
                'line-opacity': 0.8
            }
        });
        
        this.territoryCircles.set(territory.id, {
            circleId,
            sourceId,
            borderId: `${circleId}-border`
        });
        
        console.log('✅ Territory circle added successfully');
    }
    
    createCirclePoints(center, radiusKm) {
        const points = [];
        const numPoints = 32;
        
        for (let i = 0; i < numPoints; i++) {
            const angle = (i * 2 * Math.PI) / numPoints;
            const dx = radiusKm * Math.cos(angle);
            const dy = radiusKm * Math.sin(angle);
            
            // Convert km to degrees (rough approximation)
            const lat = center[1] + (dy / 111);
            const lon = center[0] + (dx / (111 * Math.cos(center[1] * Math.PI / 180)));
            
            points.push([lon, lat]);
        }
        
        // Close the polygon
        points.push(points[0]);
        return points;
    }
    
    setupMapIntegration() {
        if (!this.mapInstance) return;
        
        // Remove existing event listeners to prevent duplicates
        this.mapInstance.off('click');
        this.mapInstance.off('mousemove');
        
        // Map click handler for placing territories
        this.mapClickHandler = (e) => {
            if (this.placementMode) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Territory placement clicked at:', e.lngLat);
                this.handleTerritoryPlacement(e.lngLat);
            }
        };
        
        this.mapInstance.on('click', this.mapClickHandler);
        
        // Map move handler for placement preview
        this.mapMoveHandler = (e) => {
            if (this.placementMode) {
                this.updatePlacementPreview(e.lngLat);
            }
        };
        
        this.mapInstance.on('mousemove', this.mapMoveHandler);
        
        console.log('🗺️ Map integration setup complete');
    }
    
    async handleTerritoryPlacement(coordinates) {
        // Prevent multiple rapid clicks
        if (this.isPlacing) {
            console.log('Already placing territory, ignoring click');
            return;
        }
        
        this.isPlacing = true;
        
        const lat = coordinates.lat;
        const lon = coordinates.lng;
        
        console.log('🏴 Attempting to place territory at:', lat, lon);
        
        try {
            // Check if placement is valid
            const canPlace = await this.validatePlacement(lat, lon);
            if (!canPlace.can_place) {
                this.showNotification(canPlace.message, 'error');
                this.isPlacing = false;
                return;
            }
            
            // Show placement confirmation modal
            this.showPlacementModal(lat, lon);
            
        } catch (error) {
            console.error('Placement validation failed:', error);
            this.showNotification('Failed to validate placement', 'error');
        } finally {
            // Reset placement flag after a short delay
            setTimeout(() => {
                this.isPlacing = false;
            }, 1000);
        }
    }
    
    async validatePlacement(lat, lon) {
        const response = await fetch(`${this.apiBaseUrl}/can-place/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ lat, lon })
        });
        
        return await response.json();
    }
    
    async placeTerritory(lat, lon, name) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/place/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    lat,
                    lon,
                    custom_name: name
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Add new territory to map
                await this.addTerritoryToMap(data.flag);
                this.territories.set(data.flag.id, data.flag);
                
                this.showNotification(data.message, 'success');
                this.updateTerritoryUI();
                
                // Exit placement mode
                this.exitPlacementMode();
                
                return true;
            } else {
                this.showNotification(data.error, 'error');
                return false;
            }
        } catch (error) {
            console.error('Territory placement failed:', error);
            this.showNotification('Failed to place territory', 'error');
            return false;
        }
    }
    
    async collectRevenue(territoryId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/${territoryId}/collect-revenue/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                
                // Update character gold
                if (this.character) {
                    this.character.gold = data.new_gold_total;
                    this.updateCharacterUI();
                }
                
                // Refresh territory data
                await this.loadTerritories();
                
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Revenue collection failed:', error);
            this.showNotification('Failed to collect revenue', 'error');
        }
    }
    
    async attackTerritory(territoryId) {
        const territory = this.territories.get(territoryId);
        if (!territory) return;
        
        // Show attack confirmation
        const confirmed = confirm(`Attack ${territory.owner}'s ${territory.name}?\n\nThis will cost stamina and may result in combat!`);
        if (!confirmed) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/${territoryId}/attack/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    damage: 25 // Default attack damage
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                
                // Update territory status
                if (data.flag) {
                    territory.current_hp = data.flag.current_hp;
                    territory.status = data.flag.status;
                    
                    // Refresh territory display
                    await this.refreshTerritoryMarker(territoryId);
                    
                    // Check if territory can be captured
                    if (data.flag.can_capture) {
                        this.showCaptureDialog(territoryId);
                    }
                }
                
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Territory attack failed:', error);
            this.showNotification('Failed to attack territory', 'error');
        }
    }
    
    enterPlacementMode() {
        this.placementMode = true;
        this.mapInstance.getCanvas().style.cursor = 'crosshair';
        this.showNotification('Click on the map to place a new territory', 'info');
        
        // Update UI
        const placementBtn = document.getElementById('place-territory-btn');
        if (placementBtn) {
            placementBtn.textContent = 'Cancel Placement';
            placementBtn.className = 'btn pk-btn btn-sm w-100 mb-2 btn-warning';
        }
    }
    
    exitPlacementMode() {
        this.placementMode = false;
        this.mapInstance.getCanvas().style.cursor = '';
        
        // Clear placement preview
        if (this.placementPreview) {
            this.placementPreview.remove();
            this.placementPreview = null;
        }
        
        // Update UI
        const placementBtn = document.getElementById('place-territory-btn');
        if (placementBtn) {
            placementBtn.textContent = '🏴 Place Territory';
            placementBtn.className = 'btn pk-btn btn-sm w-100 mb-2';
        }
    }
    
    showPlacementModal(lat, lon) {
        const modal = document.createElement('div');
        modal.className = 'territory-placement-modal';
        modal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <h3>🏴 Place New Territory</h3>
                    <form id="placement-form">
                        <div class="form-group">
                            <label>Territory Name:</label>
                            <input type="text" id="territory-name" maxlength="50" placeholder="My Territory" required>
                        </div>
                        <div class="form-group">
                            <label>Location:</label>
                            <p>${lat.toFixed(6)}, ${lon.toFixed(6)}</p>
                        </div>
                        <div class="form-group">
                            <label>Cost:</label>
                            <p>500 Gold, 20 Wood, 10 Stone</p>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="this.closest('.territory-placement-modal').remove()">Cancel</button>
                            <button type="submit" class="btn pk-btn">Place Territory</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        modal.querySelector('#placement-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = modal.querySelector('#territory-name').value.trim();
            if (name) {
                const success = await this.placeTerritory(lat, lon, name);
                if (success) {
                    modal.remove();
                }
            }
        });
        
        document.body.appendChild(modal);
        modal.querySelector('#territory-name').focus();
    }
    
    updateTerritoryUI() {
        // Update territory list in sidebar
        const territoryList = document.getElementById('territory-list');
        if (!territoryList) return;
        
        const ownedTerritories = Array.from(this.territories.values())
            .filter(t => t.is_mine)
            .sort((a, b) => b.level - a.level);
        
        if (ownedTerritories.length === 0) {
            territoryList.innerHTML = '<p class="no-territories">No territories owned</p>';
            return;
        }
        
        territoryList.innerHTML = ownedTerritories.map(territory => `
            <div class="territory-item ${territory.status}" data-territory-id="${territory.id}">
                <div class="territory-header">
                    <h4>${territory.name}</h4>
                    <span class="territory-level">Level ${territory.level}</span>
                </div>
                <div class="territory-stats">
                    <div class="hp-bar">
                        <div class="hp-fill" style="width: ${(territory.current_hp / territory.max_hp) * 100}%"></div>
                        <span class="hp-text">${territory.current_hp}/${territory.max_hp} HP</span>
                    </div>
                    <div class="territory-status status-${territory.status}">${territory.status}</div>
                </div>
                <div class="territory-actions">
                    <button onclick="territoryManager.collectRevenue('${territory.id}')" class="btn-mini btn-success">💰</button>
                    <button onclick="territoryManager.openTerritoryDetails('${territory.id}')" class="btn-mini btn-primary">⚙️</button>
                    <button onclick="territoryManager.centerOnTerritory('${territory.id}')" class="btn-mini btn-secondary">📍</button>
                </div>
            </div>
        `).join('');
    }
    
    setupEventListeners() {
        // Territory placement button
        const placementBtn = document.getElementById('place-territory-btn');
        if (placementBtn) {
            placementBtn.addEventListener('click', () => {
                if (this.placementMode) {
                    this.exitPlacementMode();
                } else {
                    this.enterPlacementMode();
                }
            });
        }
        
        // Auto-collect revenue toggle
        const autoCollectToggle = document.getElementById('auto-collect-revenue');
        if (autoCollectToggle) {
            autoCollectToggle.addEventListener('change', (e) => {
                this.autoCollectRevenue = e.target.checked;
                localStorage.setItem('territory-auto-collect', this.autoCollectRevenue);
            });
        }
        
        // Refresh territories button
        const refreshBtn = document.getElementById('refresh-territories');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadTerritories();
            });
        }
    }
    
    startPeriodicUpdates() {
        // Main refresh timer
        this.refreshTimer = setInterval(() => {
            this.loadTerritories();
        }, this.autoRefreshInterval);
        
        // Auto-collect revenue
        if (this.autoCollectRevenue) {
            setInterval(() => {
                this.autoCollectAllRevenue();
            }, 60000); // Every minute
        }
    }
    
    async autoCollectAllRevenue() {
        if (!this.autoCollectRevenue) return;
        
        const ownedTerritories = Array.from(this.territories.values())
            .filter(t => t.is_mine && t.status === 'active');
        
        for (const territory of ownedTerritories) {
            try {
                await this.collectRevenue(territory.id);
                await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay between collections
            } catch (error) {
                console.error(`Auto-collect failed for ${territory.id}:`, error);
            }
        }
    }
    
    calculateEconomyStats() {
        const owned = Array.from(this.territories.values()).filter(t => t.is_mine);
        
        this.revenueStats = {
            totalTerritories: owned.length,
            totalRevenue: owned.reduce((sum, t) => sum + (t.hourly_revenue || 0), 0),
            totalUpkeep: owned.reduce((sum, t) => sum + (t.daily_upkeep_cost || 0), 0),
            netProfit: 0
        };
        
        this.revenueStats.netProfit = (this.revenueStats.totalRevenue * 24) - this.revenueStats.totalUpkeep;
        
        this.updateEconomyUI();
    }
    
    updateEconomyUI() {
        const statsPanel = document.getElementById('economy-stats');
        if (!statsPanel) return;
        
        statsPanel.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Territories:</span>
                <span class="stat-value">${this.revenueStats.totalTerritories}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Revenue/Hour:</span>
                <span class="stat-value">${this.revenueStats.totalRevenue} gold</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Upkeep/Day:</span>
                <span class="stat-value">${this.revenueStats.totalUpkeep} gold</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Net Profit/Day:</span>
                <span class="stat-value ${this.revenueStats.netProfit >= 0 ? 'positive' : 'negative'}">
                    ${this.revenueStats.netProfit} gold
                </span>
            </div>
        `;
    }
    
    centerOnTerritory(territoryId) {
        const territory = this.territories.get(territoryId);
        if (!territory || !this.mapInstance) return;
        
        this.mapInstance.flyTo({
            center: [territory.lon, territory.lat],
            zoom: 15,
            duration: 1000
        });
    }
    
    clearMapMarkers() {
        console.log('🧹 Clearing all map markers and layers...');
        
        // Remove flag markers
        this.flagMarkers.forEach((marker, id) => {
            console.log('Removing flag marker:', id);
            marker.remove();
        });
        this.flagMarkers.clear();
        
        // Remove territory circles
        this.territoryCircles.forEach((circle, id) => {
            console.log('Removing territory circle:', id);
            if (this.mapInstance.getLayer(circle.circleId)) {
                this.mapInstance.removeLayer(circle.circleId);
            }
            if (this.mapInstance.getLayer(circle.borderId)) {
                this.mapInstance.removeLayer(circle.borderId);
            }
            if (this.mapInstance.getSource(circle.sourceId)) {
                this.mapInstance.removeSource(circle.sourceId);
            }
        });
        this.territoryCircles.clear();
        
        console.log('✅ All map markers cleared');
    }
    
    performCompleteMapCleanup() {
        console.log('🗑️ Performing complete map cleanup...');
        
        if (!this.mapInstance) return;
        
        // Clear any existing markers first
        this.clearMapMarkers();
        
        // AGGRESSIVE CLEANUP: Remove ALL markers on the map
        this.removeAllMapboxMarkers();
        
        // Get all current layers and sources
        const style = this.mapInstance.getStyle();
        if (style && style.layers) {
            // Remove any territory-related layers that might be leftover
            const territoryLayers = style.layers.filter(layer => 
                layer.id.includes('territory-') || 
                layer.id.includes('flag-') ||
                layer.id.includes('circle-')
            );
            
            console.log(`Found ${territoryLayers.length} territory layers to remove:`, territoryLayers.map(l => l.id));
            
            territoryLayers.forEach(layer => {
                console.log('Removing leftover layer:', layer.id);
                try {
                    if (this.mapInstance.getLayer(layer.id)) {
                        this.mapInstance.removeLayer(layer.id);
                    }
                } catch (e) {
                    console.warn('Error removing layer:', layer.id, e);
                }
            });
        }
        
        if (style && style.sources) {
            // Remove any territory-related sources
            const territorySources = Object.keys(style.sources).filter(sourceId =>
                sourceId.includes('territory-') || sourceId.includes('flag-')
            );
            
            console.log(`Found ${territorySources.length} territory sources to remove:`, territorySources);
            
            territorySources.forEach(sourceId => {
                console.log('Removing leftover source:', sourceId);
                try {
                    if (this.mapInstance.getSource(sourceId)) {
                        this.mapInstance.removeSource(sourceId);
                    }
                } catch (e) {
                    console.warn('Error removing source:', sourceId, e);
                }
            });
        }
        
        // Clear our internal tracking
        this.territories.clear();
        this.flagMarkers.clear();
        this.territoryCircles.clear();
        
        // Force a map refresh
        this.mapInstance.triggerRepaint();
        
        console.log('✅ Complete map cleanup finished');
    }
    
    removeAllMapboxMarkers() {
        console.log('🎯 AGGRESSIVE: Removing ALL Mapbox markers...');
        
        // Get all existing markers on the map (Mapbox doesn't provide a direct way, so we use DOM)
        const mapContainer = this.mapInstance.getContainer();
        const allMarkers = mapContainer.querySelectorAll('.mapboxgl-marker');
        
        console.log(`Found ${allMarkers.length} total markers on map`);
        
        allMarkers.forEach((markerElement, index) => {
            // Check if it's a territory marker
            const isTerritoryMarker = markerElement.querySelector('.territory-flag-marker') ||
                                    markerElement.querySelector('[data-territory-id]') ||
                                    markerElement.innerHTML.includes('territory');
            
            if (isTerritoryMarker) {
                console.log(`Removing phantom marker ${index + 1}:`, markerElement);
                markerElement.remove();
            }
        });
        
        console.log('✅ All phantom markers removed from DOM');
    }
    
    forceCleanPhantomFlags() {
        console.log('🚑 EMERGENCY: Force cleaning phantom flags...');
        
        // Complete cleanup
        this.performCompleteMapCleanup();
        
        // Wait a moment then reload territories
        setTimeout(async () => {
            await this.loadTerritories();
            this.showNotification('Phantom flags cleaned!', 'success');
        }, 1000);
    }
    
    showNotification(message, type = 'info') {
        // Use the global notification system
        if (window.gameApp && window.gameApp.showNotification) {
            window.gameApp.showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
            
            // Fallback notification
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    updateCharacterUI() {
        // Update gold display
        const goldElement = document.getElementById('character-gold');
        if (goldElement && this.character.gold !== undefined) {
            goldElement.textContent = this.character.gold.toLocaleString();
        }
    }
    
    destroy() {
        // Clear timers
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        if (this.upkeepCheckTimer) {
            clearInterval(this.upkeepCheckTimer);
        }
        
        // Clear map markers
        this.clearMapMarkers();
        
        // Exit placement mode
        this.exitPlacementMode();
        
        console.log('🏴 Territory Manager destroyed');
    }
}

// Export for use in other modules
window.TerritoryManager = TerritoryManager;
