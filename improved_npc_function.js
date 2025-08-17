// 🎯 IMPROVED NPC MARKER FUNCTION - Much cleaner and simpler!

function createNPCMarker(npc) {
    const color = npc.is_alive ? '#FF5722' : '#757575';
    
    // 🎯 Create the outer HTML element for the marker
    const el = document.createElement('div');
    el.className = 'npc-marker';

    el.innerHTML = `
        <div style="
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, ${color} 0%, ${color}AA 100%);
            border: 3px solid #FFFFFF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
            animation: subtlePulse 3s infinite ease-in-out;
            cursor: pointer;
            position: relative;
            transition: all 0.3s ease;
            text-shadow: 0 1px 2px rgba(0,0,0,0.7);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            ${!npc.is_alive ? 'opacity: 0.5; filter: grayscale(50%);' : ''}
        ">
            ${npc.name.substring(0, 2).toUpperCase()}
            ${npc.is_alive ? '<div style="position: absolute; top: -2px; right: -2px; width: 8px; height: 8px; background: #4CAF50; border-radius: 50%; border: 1px solid white;"></div>' : ''}
        </div>
    `;

    // Add the pulse animation CSS if it doesn't exist
    if (!document.getElementById('npc-animations')) {
        const style = document.createElement('style');
        style.id = 'npc-animations';
        style.textContent = `
            @keyframes subtlePulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.9; }
            }
            .npc-marker:hover div {
                transform: scale(1.1) !important;
                box-shadow: 0 6px 16px rgba(0,0,0,0.5) !important;
            }
        `;
        document.head.appendChild(style);
    }

    // ✅ Add click handler with distance-based logic
    el.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log(`🎯 Clicked on ${npc.name} (Level ${npc.level})`);
        
        // Calculate distance for combat/info decision
        const distance = calculateDistance(
            currentPlayer.lat, currentPlayer.lon,
            npc.lat, npc.lon
        );
        
        if (distance <= 50 && npc.is_alive) {
            console.log('⚔️ Attacking NPC:', npc.name);
            attackNPC(npc.id);
        } else if (npc.is_alive) {
            console.log('ℹ️ Showing NPC info (too far to attack):', npc.name);
            showNPCInfo(npc);
        } else {
            console.log('💀 NPC is dead:', npc.name);
            alert(`${npc.name} is dead. Find another target!`);
        }
    });

    // ✅ Add the marker to the map at NPC lat/lon coordinates
    const marker = new mapboxgl.Marker({
        element: el,
        anchor: 'center'
    })
        .setLngLat([npc.lon, npc.lat])
        .addTo(map);
    
    // Add hover popup with NPC info
    const popup = new mapboxgl.Popup({ 
        offset: 25, 
        closeButton: false,
        closeOnClick: false
    })
        .setHTML(`
            <div style="text-align: center; min-width: 120px;">
                <strong>${npc.name}</strong><br>
                <small>Level ${npc.level} ${npc.npc_type}</small><br>
                <small>HP: ${npc.current_hp}/${npc.max_hp}</small><br>
                ${npc.is_alive ? '<em style="color: #4CAF50">Alive</em>' : '<em style="color: #757575">Dead</em>'}
            </div>
        `);
    
    marker.setPopup(popup);
    npcMarkers[npc.id] = marker;
    
    console.log(`📍 NPC ${npc.name} placed at: ${npc.lat}, ${npc.lon}`);
}

// BENEFITS of this cleaner version:
// ✅ Much simpler and easier to read
// ✅ Clear separation of concerns
// ✅ Better comments with emojis
// ✅ Removed unnecessary complexity
// ✅ Still maintains all game functionality
// ✅ Easy to modify and extend
// ✅ Uses proper Mapbox marker positioning
