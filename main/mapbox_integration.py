"""
MapBox Integration for Real-Time Location-Based RPG
Handles map rendering, location tracking, and world visualization
"""
import json
import requests
import math
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta


@dataclass
class GeoLocation:
    """Geographic location with utilities"""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def distance_to(self, other: 'GeoLocation') -> float:
        """Calculate distance to another location in meters"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(self.latitude)
        lat2_rad = math.radians(other.latitude)
        delta_lat = math.radians(other.latitude - self.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        a = (math.sin(delta_lat/2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def bearing_to(self, other: 'GeoLocation') -> float:
        """Calculate bearing to another location in degrees"""
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        y = math.sin(delta_lon) * math.cos(lat2)
        x = (math.cos(lat1) * math.sin(lat2) - 
             math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
        
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360
    
    def move_by(self, distance: float, bearing: float) -> 'GeoLocation':
        """Move by distance and bearing to get new location"""
        R = 6371000  # Earth radius in meters
        
        lat1 = math.radians(self.latitude)
        lon1 = math.radians(self.longitude)
        bearing_rad = math.radians(bearing)
        
        lat2 = math.asin(
            math.sin(lat1) * math.cos(distance/R) + 
            math.cos(lat1) * math.sin(distance/R) * math.cos(bearing_rad)
        )
        
        lon2 = lon1 + math.atan2(
            math.sin(bearing_rad) * math.sin(distance/R) * math.cos(lat1),
            math.cos(distance/R) - math.sin(lat1) * math.sin(lat2)
        )
        
        return GeoLocation(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2),
            timestamp=timezone.now()
        )
    
    def to_dict(self) -> Dict:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class MapRegion:
    """Represents a bounded map region"""
    name: str
    center: GeoLocation
    radius: float  # meters
    bounds: Dict[str, float]  # north, south, east, west
    properties: Dict[str, Any] = None
    
    def contains_point(self, location: GeoLocation) -> bool:
        """Check if location is within this region"""
        return (self.bounds['south'] <= location.latitude <= self.bounds['north'] and
                self.bounds['west'] <= location.longitude <= self.bounds['east'])
    
    def distance_from_center(self, location: GeoLocation) -> float:
        """Get distance from region center"""
        return self.center.distance_to(location)


class MapBoxAPI:
    """MapBox API integration"""
    
    def __init__(self):
        self.access_token = getattr(settings, 'MAPBOX_ACCESS_TOKEN', '')
        self.base_url = "https://api.mapbox.com"
        self.cache_timeout = 300  # 5 minutes
    
    def geocode(self, query: str, proximity: GeoLocation = None) -> List[Dict]:
        """Geocode an address or place name"""
        cache_key = f"geocode_{hash(query)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            'access_token': self.access_token,
            'limit': 5,
            'types': 'place,locality,neighborhood,address'
        }
        
        if proximity:
            params['proximity'] = f"{proximity.longitude},{proximity.latitude}"
        
        url = f"{self.base_url}/geocoding/v5/mapbox.places/{query}.json"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for feature in data.get('features', []):
                coords = feature['geometry']['coordinates']
                results.append({
                    'name': feature['place_name'],
                    'location': GeoLocation(
                        latitude=coords[1],
                        longitude=coords[0]
                    ),
                    'relevance': feature.get('relevance', 0),
                    'context': feature.get('context', [])
                })
            
            cache.set(cache_key, results, self.cache_timeout)
            return results
            
        except Exception as e:
            print(f"Geocoding error: {e}")
            return []
    
    def reverse_geocode(self, location: GeoLocation) -> Dict:
        """Reverse geocode a location to get address/place info"""
        cache_key = f"reverse_geocode_{location.latitude}_{location.longitude}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        url = f"{self.base_url}/geocoding/v5/mapbox.places/{location.longitude},{location.latitude}.json"
        params = {
            'access_token': self.access_token,
            'types': 'place,locality,neighborhood,address'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            if features:
                feature = features[0]
                result = {
                    'name': feature['place_name'],
                    'short_name': feature['text'],
                    'relevance': feature.get('relevance', 0),
                    'context': feature.get('context', [])
                }
            else:
                result = {
                    'name': f"Location {location.latitude:.4f}, {location.longitude:.4f}",
                    'short_name': "Unknown Location",
                    'relevance': 0,
                    'context': []
                }
            
            cache.set(cache_key, result, self.cache_timeout)
            return result
            
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return {
                'name': f"Location {location.latitude:.4f}, {location.longitude:.4f}",
                'short_name': "Unknown Location",
                'relevance': 0,
                'context': []
            }
    
    def get_static_map_url(self, center: GeoLocation, zoom: int = 15, 
                          width: int = 600, height: int = 400,
                          markers: List[Dict] = None, style: str = 'streets-v11') -> str:
        """Generate static map image URL"""
        
        markers_str = ""
        if markers:
            marker_parts = []
            for marker in markers:
                loc = marker.get('location')
                if loc:
                    color = marker.get('color', 'red')
                    size = marker.get('size', 'small')
                    marker_parts.append(f"pin-{size}-{color}({loc.longitude},{loc.latitude})")
            
            if marker_parts:
                markers_str = "/" + ",".join(marker_parts)
        
        url = (f"{self.base_url}/styles/v1/mapbox/{style}/static"
               f"{markers_str}/{center.longitude},{center.latitude},{zoom}"
               f"/{width}x{height}@2x?access_token={self.access_token}")
        
        return url
    
    def get_directions(self, waypoints: List[GeoLocation], 
                      profile: str = 'walking') -> Dict:
        """Get directions between waypoints"""
        if len(waypoints) < 2:
            return {}
        
        # Build coordinates string
        coords = ";".join([f"{wp.longitude},{wp.latitude}" for wp in waypoints])
        
        url = f"{self.base_url}/directions/v5/mapbox/{profile}/{coords}"
        params = {
            'access_token': self.access_token,
            'geometries': 'geojson',
            'overview': 'full',
            'steps': 'true'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('routes'):
                route = data['routes'][0]
                return {
                    'distance': route['distance'],  # meters
                    'duration': route['duration'],  # seconds
                    'geometry': route['geometry'],
                    'steps': route.get('legs', [{}])[0].get('steps', [])
                }
            
        except Exception as e:
            print(f"Directions error: {e}")
        
        return {}


class GameWorldMap:
    """Manages the game world map and location-based features"""
    
    def __init__(self):
        self.mapbox = MapBoxAPI()
        self.regions = {}
        self.poi_cache = {}  # Points of Interest cache
        
    def register_region(self, region: MapRegion):
        """Register a game region"""
        self.regions[region.name] = region
    
    def find_region_for_location(self, location: GeoLocation) -> Optional[MapRegion]:
        """Find which region contains the given location"""
        for region in self.regions.values():
            if region.contains_point(location):
                return region
        return None
    
    def get_nearby_players(self, location: GeoLocation, radius: float = 100) -> List[Dict]:
        """Get nearby players within radius (would typically query database)"""
        # This would typically query the Character model
        # For now, return empty list as placeholder
        return []
    
    def get_nearby_monsters(self, location: GeoLocation, radius: float = 200) -> List[Dict]:
        """Get nearby monsters within radius"""
        # This would typically query the Monster model
        return []
    
    def get_nearby_items(self, location: GeoLocation, radius: float = 50) -> List[Dict]:
        """Get nearby items within radius"""
        # This would typically query ground items
        return []
    
    def get_points_of_interest(self, location: GeoLocation, radius: float = 1000) -> List[Dict]:
        """Get points of interest near location"""
        cache_key = f"poi_{location.latitude:.4f}_{location.longitude:.4f}_{radius}"
        cached_poi = cache.get(cache_key)
        if cached_poi:
            return cached_poi
        
        # Use MapBox to find nearby places
        search_queries = ["restaurant", "shop", "park", "hospital", "school"]
        poi_list = []
        
        for query in search_queries:
            results = self.mapbox.geocode(query, proximity=location)
            for result in results[:3]:  # Limit to 3 per category
                if result['location'].distance_to(location) <= radius:
                    poi_list.append({
                        'name': result['name'],
                        'location': result['location'].to_dict(),
                        'category': query,
                        'distance': result['location'].distance_to(location)
                    })
        
        # Sort by distance
        poi_list.sort(key=lambda x: x['distance'])
        poi_list = poi_list[:15]  # Limit total results
        
        cache.set(cache_key, poi_list, 600)  # Cache for 10 minutes
        return poi_list
    
    def create_map_data(self, center: GeoLocation, zoom_level: int = 15) -> Dict:
        """Create comprehensive map data for frontend"""
        
        # Get location info
        location_info = self.mapbox.reverse_geocode(center)
        
        # Find current region
        current_region = self.find_region_for_location(center)
        
        # Get nearby entities
        nearby_players = self.get_nearby_players(center)
        nearby_monsters = self.get_nearby_monsters(center)
        nearby_items = self.get_nearby_items(center)
        poi_list = self.get_points_of_interest(center)
        
        # Create marker list for static map
        markers = []
        
        # Add player markers
        for player in nearby_players:
            markers.append({
                'location': GeoLocation(player['lat'], player['lon']),
                'color': 'blue',
                'size': 'small'
            })
        
        # Add monster markers
        for monster in nearby_monsters:
            markers.append({
                'location': GeoLocation(monster['lat'], monster['lon']),
                'color': 'red',
                'size': 'medium'
            })
        
        # Get static map URL
        static_map_url = self.mapbox.get_static_map_url(
            center=center,
            zoom=zoom_level,
            markers=markers
        )
        
        return {
            'center': center.to_dict(),
            'zoom': zoom_level,
            'location_info': location_info,
            'current_region': current_region.name if current_region else None,
            'nearby_players': nearby_players,
            'nearby_monsters': nearby_monsters,
            'nearby_items': nearby_items,
            'points_of_interest': poi_list,
            'static_map_url': static_map_url,
            'regions': [
                {
                    'name': region.name,
                    'center': region.center.to_dict(),
                    'radius': region.radius,
                    'distance': region.distance_from_center(center)
                }
                for region in self.regions.values()
                if region.distance_from_center(center) <= 5000  # Within 5km
            ]
        }
    
    def calculate_travel_route(self, start: GeoLocation, end: GeoLocation) -> Dict:
        """Calculate optimal travel route between two points"""
        
        # Get directions from MapBox
        directions = self.mapbox.get_directions([start, end])
        
        if not directions:
            # Fallback to straight line distance
            distance = start.distance_to(end)
            bearing = start.bearing_to(end)
            
            return {
                'distance': distance,
                'duration': distance / 1.4,  # Assume 1.4 m/s walking speed
                'bearing': bearing,
                'waypoints': [start.to_dict(), end.to_dict()],
                'route_type': 'direct'
            }
        
        return {
            'distance': directions['distance'],
            'duration': directions['duration'],
            'geometry': directions['geometry'],
            'steps': directions['steps'],
            'route_type': 'routed'
        }
    
    def validate_movement(self, from_location: GeoLocation, 
                         to_location: GeoLocation, 
                         max_distance: float = 100) -> bool:
        """Validate that movement is within allowed parameters"""
        
        distance = from_location.distance_to(to_location)
        
        # Check maximum distance
        if distance > max_distance:
            return False
        
        # Check if movement crosses any restricted areas
        # (This would be implemented based on game rules)
        
        # Check movement speed (prevent teleportation)
        if from_location.timestamp and to_location.timestamp:
            time_diff = (to_location.timestamp - from_location.timestamp).total_seconds()
            if time_diff > 0:
                speed = distance / time_diff  # m/s
                max_speed = 10.0  # 10 m/s max (36 km/h)
                
                if speed > max_speed:
                    return False
        
        return True
    
    def get_spawn_locations_near(self, center: GeoLocation, 
                               entity_type: str = 'monster',
                               count: int = 5, 
                               min_distance: float = 50,
                               max_distance: float = 200) -> List[GeoLocation]:
        """Generate spawn locations around a center point"""
        
        spawn_locations = []
        attempts = 0
        max_attempts = count * 5
        
        while len(spawn_locations) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate random distance and bearing
            distance = min_distance + (max_distance - min_distance) * math.sqrt(random.random())
            bearing = random.uniform(0, 360)
            
            # Calculate new location
            spawn_location = center.move_by(distance, bearing)
            
            # Validate location (not too close to existing spawns, not in restricted areas)
            valid = True
            for existing in spawn_locations:
                if existing.distance_to(spawn_location) < min_distance / 2:
                    valid = False
                    break
            
            if valid:
                spawn_locations.append(spawn_location)
        
        return spawn_locations


# Global game world map instance
game_world = GameWorldMap()

# Initialize some default regions (these would typically be loaded from database)
if hasattr(settings, 'MAPBOX_ACCESS_TOKEN'):
    # Example regions - replace with your actual game world regions
    default_regions = [
        MapRegion(
            name="Central Park",
            center=GeoLocation(40.7829, -73.9654),
            radius=1000,
            bounds={
                'north': 40.7972,
                'south': 40.7686,
                'east': -73.9485,
                'west': -73.9823
            },
            properties={'type': 'park', 'level_range': '1-10'}
        ),
        MapRegion(
            name="Times Square",
            center=GeoLocation(40.7580, -73.9855),
            radius=500,
            bounds={
                'north': 40.7625,
                'south': 40.7535,
                'east': -73.9815,
                'west': -73.9895
            },
            properties={'type': 'urban', 'level_range': '5-15'}
        )
    ]
    
    for region in default_regions:
        game_world.register_region(region)
