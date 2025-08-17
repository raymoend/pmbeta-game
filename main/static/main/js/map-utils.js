/**
 * Professional Mapbox coordinate conversion utilities
 * Provides precise lat/lon ↔ pixel conversion for PMBeta game
 */

/**
 * Convert longitude/latitude to screen pixels using Mapbox projection
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {number} lng - Longitude
 * @param {number} lat - Latitude
 * @returns {mapboxgl.Point} Screen pixel coordinates {x, y}
 */
export function lngLatToPixels(map, lng, lat) {
    return map.project([lng, lat]);
}

/**
 * Convert screen pixels to longitude/latitude using Mapbox projection
 * @param {mapboxgl.Map} map - Mapbox map instance  
 * @param {number} x - Screen X coordinate
 * @param {number} y - Screen Y coordinate
 * @returns {mapboxgl.LngLat} Geographic coordinates {lng, lat}
 */
export function pixelsToLngLat(map, x, y) {
    return map.unproject([x, y]);
}

/**
 * Check if a point is within a circular radius
 * @param {number} centerLat - Center latitude
 * @param {number} centerLon - Center longitude
 * @param {number} pointLat - Point latitude
 * @param {number} pointLon - Point longitude
 * @param {number} radiusMeters - Radius in meters
 * @returns {boolean} True if within radius
 */
export function isWithinRadius(centerLat, centerLon, pointLat, pointLon, radiusMeters) {
    const distance = calculateDistance(centerLat, centerLon, pointLat, pointLon);
    return distance <= radiusMeters;
}

/**
 * Calculate distance between two coordinates in meters (Haversine formula)
 * @param {number} lat1 - First point latitude
 * @param {number} lon1 - First point longitude
 * @param {number} lat2 - Second point latitude
 * @param {number} lon2 - Second point longitude
 * @returns {number} Distance in meters
 */
export function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

/**
 * Get viewport bounds from map
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @returns {Object} Bounds object with {north, south, east, west}
 */
export function getMapBounds(map) {
    const bounds = map.getBounds();
    return {
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest()
    };
}

/**
 * Convert map click event to lat/lon coordinates
 * @param {mapboxgl.MapMouseEvent} e - Map click event
 * @returns {Object} Coordinates {lat, lon}
 */
export function eventToCoords(e) {
    return {
        lat: e.lngLat.lat,
        lon: e.lngLat.lng
    };
}

/**
 * Professional hit detection for markers/entities
 * @param {mapboxgl.Map} map - Mapbox map instance
 * @param {number} x - Click X coordinate
 * @param {number} y - Click Y coordinate
 * @param {Array} entities - Array of entities to check
 * @param {number} tolerance - Hit tolerance in pixels (default: 20)
 * @returns {Object|null} Hit entity or null
 */
export function hitTest(map, x, y, entities, tolerance = 20) {
    const clickPoint = { x, y };
    
    for (const entity of entities) {
        const entityPixels = lngLatToPixels(map, entity.lon, entity.lat);
        const distance = Math.sqrt(
            Math.pow(clickPoint.x - entityPixels.x, 2) + 
            Math.pow(clickPoint.y - entityPixels.y, 2)
        );
        
        if (distance <= tolerance) {
            return entity;
        }
    }
    
    return null;
}
