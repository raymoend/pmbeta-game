/**
 * entity-interaction.js
 * Professional click prevention and entity interaction utilities for PMBeta
 */

/**
 * Sets up global click prevention for all entity markers
 * Prevents map panning/zooming when clicking on entities
 * This allows entities to be properly clickable without triggering map events
 */
function setupEntityClickPrevention() {
    console.log('Setting up global entity click prevention');
    
    // Get the map container element
    const mapContainer = document.querySelector('.mapboxgl-canvas-container');
    if (!mapContainer) {
        console.error('Map container not found for click prevention setup');
        return;
    }
    
    // Add a capture phase event listener to catch all clicks
    mapContainer.addEventListener('mousedown', function(e) {
        // Check if clicked element or any parent is a marker
        let target = e.target;
        while (target && target !== mapContainer) {
            if (
                target.classList && (
                    target.classList.contains('npc-marker') ||
                    target.classList.contains('resource-marker') ||
                    target.classList.contains('flag-marker') ||
                    target.classList.contains('player-marker') ||
                    target.classList.contains('other-player-marker') ||
                    target.classList.contains('structure-marker')
                )
            ) {
                // Stop propagation to prevent map panning/zooming
                e.stopPropagation();
                console.log('Prevented map interaction for entity click');
                return;
            }
            target = target.parentElement;
        }
    }, true); // Use capture phase to intercept before map handlers
    
    console.log('Entity click prevention setup complete');
}

/**
 * Enhances NPC markers with professional styling and animations
 * @param {HTMLElement} markerElement - The marker DOM element to enhance
 */
function enhanceNPCMarker(markerElement) {
    if (!markerElement) return;
    
    // Add CSS pulse animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.1); opacity: 0.9; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .npc-marker-enhanced {
            animation: pulse 2s infinite ease-in-out;
            transform-origin: center center;
            z-index: 1001 !important;
            pointer-events: auto !important;
        }
        
        .npc-marker-enhanced:hover {
            animation: none;
            transform: scale(1.2);
            transition: transform 0.2s ease-out;
        }
        
        .npc-marker-enhanced.combat-mode {
            animation: pulse 0.5s infinite ease-in-out;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.7) !important;
        }
    `;
    
    document.head.appendChild(style);
    
    // Add enhancement class
    markerElement.classList.add('npc-marker-enhanced');
    
    // Add drop shadow
    markerElement.style.filter = 'drop-shadow(0px 3px 5px rgba(0,0,0,0.5))';
}

/**
 * Improves entity marker interaction behavior
 * @param {string} entityType - Type of entity ('npc', 'resource', 'flag')
 * @param {HTMLElement} markerElement - The marker DOM element
 * @param {Function} clickHandler - Function to call when marker is clicked
 */
function setupEnhancedMarkerInteraction(entityType, markerElement, clickHandler) {
    if (!markerElement) return;
    
    // Clear any existing listeners to prevent duplicates
    const newMarker = markerElement.cloneNode(true);
    markerElement.parentNode.replaceChild(newMarker, markerElement);
    
    // Add mousedown handler with immediate stopPropagation
    newMarker.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    }, true);
    
    // Add click handler with custom behavior
    newMarker.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        // Apply visual feedback
        this.style.transform = 'scale(1.2)';
        setTimeout(() => {
            this.style.transform = 'scale(1)';
        }, 200);
        
        // Call the click handler
        if (typeof clickHandler === 'function') {
            clickHandler(e);
        }
        
        return false;
    }, true);
    
    // Add accessibility attributes
    newMarker.setAttribute('role', 'button');
    newMarker.setAttribute('aria-label', `${entityType} interaction`);
    newMarker.setAttribute('tabindex', '0');
    
    // Handle keyboard interaction for accessibility
    newMarker.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            if (typeof clickHandler === 'function') {
                clickHandler(e);
            }
        }
    });
    
    return newMarker;
}

/**
 * Adds combat feedback animation to an NPC marker
 * @param {string} npcId - ID of the NPC
 * @param {number} damage - Amount of damage dealt
 */
function showCombatFeedback(npcId, damage) {
    const marker = npcMarkers[npcId];
    if (!marker || !marker.getElement()) return;
    
    const markerEl = marker.getElement();
    
    // Create damage indicator
    const damageEl = document.createElement('div');
    damageEl.className = 'damage-indicator';
    damageEl.textContent = `-${damage}`;
    damageEl.style.cssText = `
        position: absolute;
        top: -20px;
        left: 50%;
        transform: translateX(-50%);
        color: #2196F3;
        font-weight: bold;
        font-size: 14px;
        text-shadow: 0 0 3px black;
        pointer-events: none;
        animation: fadeUp 1s forwards;
        z-index: 2000;
    `;
    
    // Add keyframe animation if it doesn't exist
    if (!document.querySelector('#damage-animation')) {
        const style = document.createElement('style');
        style.id = 'damage-animation';
        style.textContent = `
            @keyframes fadeUp {
                0% { opacity: 1; transform: translate(-50%, 0); }
                100% { opacity: 0; transform: translate(-50%, -30px); }
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-3px); }
                75% { transform: translateX(3px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Add to DOM and remove after animation
    markerEl.appendChild(damageEl);
    
    // Add shake animation to the marker
    markerEl.style.animation = 'shake 0.5s ease-in-out';
    
    // Remove after animation completes
    setTimeout(() => {
        if (markerEl.contains(damageEl)) {
            markerEl.removeChild(damageEl);
        }
        markerEl.style.animation = '';
    }, 1000);
}
