import math

TILE_DEG = 0.02

def tile_for(lat: float, lon: float, tile_deg: float = TILE_DEG) -> str:
    """Return a Channels-safe group name for a geo tile.
    Only ASCII alphanumerics, hyphens, underscores, or periods are allowed.
    """
    x = math.floor(lon / tile_deg)
    y = math.floor(lat / tile_deg)
    # Use underscores and dots only (no colons)
    return f"geo_{int(tile_deg*1000)}.{y}.{x}"

def tiles_within_radius(lat: float, lon: float, radius_m: float, tile_deg: float = TILE_DEG):
    """Return a list of Channels-safe group names for tiles overlapping a radius bbox."""
    deg = radius_m / 111000.0
    min_lat, max_lat = lat - deg, lat + deg
    min_lon, max_lon = lon - deg, lon + deg
    tiles = set()
    lat_start = math.floor(min_lat / tile_deg)
    lat_end = math.floor(max_lat / tile_deg)
    lon_start = math.floor(min_lon / tile_deg)
    lon_end = math.floor(max_lon / tile_deg)
    for iy in range(lat_start, lat_end + 1):
        for ix in range(lon_start, lon_end + 1):
            tiles.add(f"geo_{int(tile_deg*1000)}.{iy}.{ix}")
    return list(tiles)

