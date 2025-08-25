/**
 * Professional NPC Management System for PMBeta
 * Handles loading, rendering, and interaction with NPCs
 */

import { calculateDistance } from './map-utils.js';

// Global NPC state management
let npcMarkers = {};
let npcCache = {};
let currentPlayer = null;
let map = null;

// SVG data-URI generator for glyph placeholders
function svgDataUri(bgColor, glyph) {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'>
  <rect x='0' y='0' width='100%' height='100%' rx='6' ry='6' fill='${bgColor}' />
  <text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='18'>${glyph}</text>
</svg>`;
    return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
}

// Determine NPC placeholder icon from type/name
function getNPCPlaceholderIcon(npc) {
    const name = String(npc?.name || '').toLowerCase();
    const type = String(npc?.npc_type || '').toLowerCase();
    const alive = !!npc?.is_alive;
    let glyph = '👤';
    let color = alive ? '#FF5722' : '#757575';
    if (/wolf/.test(name) || /wolf/.test(type)) glyph = '🐺';
    else if (/bear/.test(name) || /bear/.test(type)) glyph = '🐻';
    else if (/goblin|troll|orc/.test(name) || /goblin|troll|orc/.test(type)) glyph = '👹';
    else if (/skeleton/.test(name) || /skeleton/.test(type)) glyph = '💀';
    else if (/zombie|undead/.test(name) || /zombie|undead/.test(type)) glyph = '🧟';
    else if (/dragon/.test(name) || /dragon/.test(type)) glyph = '🐲';
    else if (/merchant|trader/.test(name) || /merchant|trader/.test(type)) glyph = '🧑‍🌾';
    return svgDataUri(color, glyph);
}

/**
 * Initialize NPC system
 * @param {mapboxgl.Map} mapInstance - Mapbox map instance
 * @param {Object} playerData - Current player data
 */
export function initNPCSystem(mapInstance, playerData) {
    map = mapInstance;
    currentPlayer = playerData;
    console.log('NPC system initialized');
}

/**
 * Fetch NPCs from server API with professional error handling
 * @returns {Promise<Array>} Array of NPC data
 */
export async function fetchNPCs() {
    try {
        const response = await fetch('/api/npcs/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'API returned success=false');
        }
        
        const npcs = data.data?.npcs || [];
        console.log(`✓ Loaded ${npcs.length} NPCs from API`);
        return npcs;
        
    } catch (error) {
        console.error('Failed to fetch NPCs:', error);
        throw error;
    }
}

/**
 * Clear all NPC markers from map
 */
export function clearNPCMarkers() {
    Object.values(npcMarkers).forEach(marker => marker.remove());
    npcMarkers = {};
    npcCache = {};
    console.log('Cleared all NPC markers');
}

/**
 * Create professional NPC marker with Perblue-style UX
 * @param {Object} npc - NPC data object
 * @returns {mapboxgl.Marker} Mapbox marker instance
 */
export function createNPCMarker(npc) {
    // Fix field mapping issue: API sends current_hp but frontend expects current_hp
    const npcData = {
        ...npc,
        current_hp: npc.current_hp || npc.hp || npc.max_hp, // Handle different field names
        attack_power: npc.attack_power || npc.strength, // Map strength to attack_power
        defense_rating: npc.defense_rating || npc.defense, // Map defense to defense_rating  
        money_reward: npc.money_reward || npc.base_gold_reward // Map reward fields
    };
    
    const isAlive = npcData.is_alive;
    const color = isAlive ? '#FF5722' : '#757575';
    const nameInitials = npcData.name ? npcData.name.substring(0, 2).toUpperCase() : 'NP';
    const iconUrl = getNPCPlaceholderIcon(npcData);
    
    // Create marker element with professional styling
    const el = document.createElement('div');
    el.className = 'npc-marker';
    el.style.cssText = `
        position: relative;
        z-index: 1100;
        pointer-events: auto;
        cursor: pointer;
        transform-origin: center;
        transition: transform 0.2s ease, opacity 0.3s ease;
    `;
    
    el.innerHTML = `
        <div class="npc-marker-inner" style="
            width: 44px;
            height: 44px;
            background: linear-gradient(145deg, ${color}, ${adjustColor(color, -20)});
            border: 3px solid #FFFFFF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            user-select: none;
            ${!isAlive ? 'opacity: 0.5; filter: grayscale(50%);' : ''}
        ">
            <img src="${iconUrl}" alt="${npcData.name || 'NPC'}" style="width:24px;height:24px;" />
        </div>
    `;
    
    // Add professional hover effects
    el.addEventListener('mouseenter', () => {
        if (isAlive) {
            el.style.transform = 'scale(1.15)';
            el.querySelector('.npc-marker-inner').style.boxShadow = '0 6px 20px rgba(255, 87, 34, 0.6)';
        }
    });
    
    el.addEventListener('mouseleave', () => {
        el.style.transform = 'scale(1)';
        el.querySelector('.npc-marker-inner').style.boxShadow = '0 4px 12px rgba(0,0,0,0.4)';
    });
    
    // Professional click handling with event capture
    el.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        e.preventDefault();
    }, true);
    
    el.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        console.log('NPC clicked:', npcData.name, npcData.id);
        
        const distance = calculateDistance(
            currentPlayer.lat, currentPlayer.lon,
            npcData.lat, npcData.lon
        );
        
        if (distance <= 50 && npcData.is_alive) {
            attackNPC(npcData.id);
        } else {
            showNPCInfo(npcData);
        }
        
        return false;
    }, true);
    
    // Add accessibility
    el.setAttribute('title', `${npcData.name} - Level ${npcData.level} ${npcData.npc_type}`);
    el.setAttribute('aria-label', `NPC: ${npcData.name}, Level ${npcData.level}, ${isAlive ? 'Alive' : 'Dead'}`);
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    
    // Create Mapbox marker
    const marker = new mapboxgl.Marker({
        element: el,
        anchor: 'center'
    })
    .setLngLat([npcData.lon, npcData.lat]);
    
    // Add popup with corrected field names
    const popup = new mapboxgl.Popup({ 
        offset: 30, 
        closeButton: false,
        className: 'npc-popup'
    }).setHTML(`
        <div style="text-align: center; min-width: 140px;">
            <strong style="color: ${color};">${npcData.name}</strong><br>
            <small>Level ${npcData.level} ${npcData.npc_type}</small><br>
            <small>HP: ${npcData.current_hp}/${npcData.max_hp}</small><br>
            ${isAlive ? '<em style="color: #4CAF50">Alive</em>' : '<em style="color: #757575">Dead</em>'}
        </div>
    `);
    
    marker.setPopup(popup);
    
    return marker;
}

/**
 * Refresh all NPC markers on the map
 * @param {mapboxgl.Map} mapInstance - Mapbox map instance
 * @param {Array} npcs - Array of NPC data
 */
export async function refreshNPCMarkers(mapInstance, npcs) {
    if (!mapInstance || !mapInstance.isStyleLoaded()) {
        console.warn('Map not ready for NPC markers');
        return;
    }
    
    // Clear existing markers
    clearNPCMarkers();
    
    if (!npcs || npcs.length === 0) {
        console.warn('No NPCs to display');
        return;
    }
    
    console.log(`Rendering ${npcs.length} NPC markers...`);
    
    let renderedCount = 0;
    
    // Create markers with staggered animation
    npcs.forEach((npc, index) => {
        try {
            // Validate NPC data
            if (!npc.id || !npc.lat || !npc.lon || !npc.name) {
                console.warn('Invalid NPC data:', npc);
                return;
            }
            
            const marker = createNPCMarker(npc);
            marker.addTo(mapInstance);
            
            // Store references
            npcMarkers[npc.id] = marker;
            npcCache[npc.id] = npc;
            
            // Animate entrance with staggered timing
            setTimeout(() => {
                const element = marker.getElement();
                if (element) {
                    element.style.transform = 'scale(0)';
                    element.style.opacity = '0';
                    setTimeout(() => {
                        element.style.transform = 'scale(1)';
                        element.style.opacity = '1';
                    }, 50);
                }
            }, index * 20); // Stagger by 20ms per NPC
            
            renderedCount++;
            
        } catch (error) {
            console.error(`Failed to create marker for NPC ${npc.id}:`, error);
        }
    });
    
    console.log(`✓ Successfully rendered ${renderedCount}/${npcs.length} NPC markers`);
}

/**
 * Update NPC marker after combat/changes
 * @param {string} npcId - NPC ID  
 * @param {Object} updatedData - Updated NPC data
 */
export function updateNPCMarker(npcId, updatedData) {
    const marker = npcMarkers[npcId];
    if (!marker) {
        console.warn(`NPC marker ${npcId} not found for update`);
        return;
    }
    
    // Update cache
    npcCache[npcId] = { ...npcCache[npcId], ...updatedData };
    
    // If NPC died, animate removal
    if (updatedData.is_alive === false) {
        const element = marker.getElement();
        if (element) {
            element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            element.style.opacity = '0';
            element.style.transform = 'scale(0.5)';
            
            setTimeout(() => {
                marker.remove();
                delete npcMarkers[npcId];
                delete npcCache[npcId];
            }, 500);
        }
    }
}

/**
 * Get CSRF token for API requests
 * @returns {string|null} CSRF token
 */
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Adjust color brightness
 * @param {string} color - Hex color
 * @param {number} percent - Brightness adjustment (-100 to 100)
 * @returns {string} Adjusted hex color
 */
function adjustColor(color, percent) {
    const num = parseInt(color.replace("#", ""), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
        (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
        (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
}

// Export marker state for external access
export { npcMarkers, npcCache };
