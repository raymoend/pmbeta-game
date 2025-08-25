/**
 * TARGETED PHANTOM MARKER FIX
 * Simple approach - just remove duplicate markers
 */

console.log('🎯 Targeted phantom marker fix loading...');

function removePhantomMarkers() {
    try {
        const markers = document.querySelectorAll('.mapboxgl-marker');
        const positions = new Map();
        let removedCount = 0;

        markers.forEach(marker => {
            // Skip if this marker doesn't contain emojis we care about
            if (!marker.innerHTML || (!marker.innerHTML.includes('🏴') && !marker.innerHTML.includes('⚡'))) {
                return;
            }

            const rect = marker.getBoundingClientRect();
            const x = Math.round(rect.left / 10) * 10; // Group by 10px intervals
            const y = Math.round(rect.top / 10) * 10;
            const key = `${x},${y}`;

            if (positions.has(key)) {
                // This is a duplicate at the same position - remove it
                console.log('🎯 Removing phantom marker at', key);
                marker.remove();
                removedCount++;
            } else {
                positions.set(key, marker);
            }
        });

        if (removedCount > 0) {
            console.log(`🎯 Removed ${removedCount} phantom markers`);
        }
    } catch (e) {
        // Be resilient; never break the page if this utility fails
        console.warn('Phantom marker cleanup failed:', e);
    }
}

// Simple periodic cleanup
setInterval(removePhantomMarkers, 2000);

// Initial cleanup
setTimeout(removePhantomMarkers, 3000);

console.log('🎯 Phantom marker fix active');
