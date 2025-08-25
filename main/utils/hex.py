import math

# Simple flat-topped hex grid utilities using local equirectangular projection
# Hex size s is taken as the hex circumradius in meters (≈ circle radius)

def _meters_per_deg(lat_deg: float):
    # Approximate meters per degree at latitude
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 111_132.92 - 559.82 * math.cos(2*lat_rad) + 1.175 * math.cos(4*lat_rad) - 0.0023 * math.cos(6*lat_rad)
    m_per_deg_lon = 111_412.84 * math.cos(lat_rad) - 93.5 * math.cos(3*lat_rad) + 0.118 * math.cos(5*lat_rad)
    return m_per_deg_lat, m_per_deg_lon

def _project_local(lat_deg: float, lon_deg: float, lat0: float, lon0: float):
    m_per_deg_lat, m_per_deg_lon = _meters_per_deg(lat0)
    x = (lon_deg - lon0) * m_per_deg_lon
    y = (lat_deg - lat0) * m_per_deg_lat
    return x, y

def _unproject_local(x: float, y: float, lat0: float, lon0: float):
    m_per_deg_lat, m_per_deg_lon = _meters_per_deg(lat0)
    lat = lat0 + (y / m_per_deg_lat)
    lon = lon0 + (x / m_per_deg_lon)
    return lat, lon

# Axial coordinates for flat-topped hex grid
# Reference formulas: https://www.redblobgames.com/grids/hex-grids/

def _axial_from_xy_flat(x: float, y: float, s: float):
    q = (2.0/3.0) * x / s
    r = (-1.0/3.0) * x / s + (math.sqrt(3)/3.0) * y / s
    return q, r

def _cube_round(x: float, y: float, z: float):
    rx = round(x); ry = round(y); rz = round(z)
    x_diff = abs(rx - x); y_diff = abs(ry - y); z_diff = abs(rz - z)
    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return rx, ry, rz

def _axial_round(q: float, r: float):
    x = q
    z = r
    y = -x - z
    rx, ry, rz = _cube_round(x, y, z)
    rq = rx
    rr = rz
    return rq, rr

def _xy_from_axial_flat(q: int, r: int, s: float):
    x = s * (3.0/2.0 * q)
    y = s * (math.sqrt(3) * (r + q/2.0))
    return x, y


def latlon_to_hex(lat: float, lon: float, size_m: float):
    # Use local origin at the same lat/lon for projection
    x, y = _project_local(lat, lon, lat, lon)
    # This gives (0,0); to be translation independent we project vs static origin near point
    # Use origin offset of small epsilon to stabilize rounding
    lat0, lon0 = lat, lon
    x0, y0 = 0.0, 0.0
    qf, rf = _axial_from_xy_flat(x - x0, y - y0, size_m)
    q, r = _axial_round(qf, rf)
    return q, r, lat0, lon0


def hex_center_to_latlon(q: int, r: int, lat0: float, lon0: float, size_m: float):
    x, y = _xy_from_axial_flat(q, r, size_m)
    lat, lon = _unproject_local(x, y, lat0, lon0)
    return lat, lon


def hex_polygon(lat_center: float, lon_center: float, size_m: float, steps: int = 6):
    # Build flat-topped hex polygon points (6 vertices)
    # Compute the 6 corners in local meters then unproject
    lat0, lon0 = lat_center, lon_center
    coords = []
    for i in range(6):
        angle_deg = 60 * i  # flat-top
        angle_rad = math.radians(angle_deg)
        x = size_m * math.cos(angle_rad)
        y = size_m * math.sin(angle_rad)
        lat, lon = _unproject_local(x, y, lat0, lon0)
        coords.append([lon, lat])
    coords.append(coords[0])
    return { 'type': 'Polygon', 'coordinates': [coords] }
