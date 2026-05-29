import requests
import json
import logging
import urllib.parse

def get_coordinates_from_address(address, here_api_key):
    """
    Sử dụng HERE Geocoding API để chuyển đổi địa chỉ thành tọa độ.
    """
    if not here_api_key:
        raise ValueError("Thiếu HERE Maps API Key")
    
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {
        "q": f"{address}, Vietnam",
        "apiKey": here_api_key
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if "items" in data and len(data["items"]) > 0:
            location = data["items"][0]["position"]
            return location["lat"], location["lng"]
        else:
            logging.error(f"Geocoding failed for '{address}': {data}")
            return None, None
    except Exception as e:
        logging.error(f"Geocoding exception: {e}")
        return None, None


def get_optimized_motorcycle_route(start_point, waypoints, here_api_key):
    """
    Sử dụng HERE Waypoint Sequence API để tối ưu hóa thứ tự các điểm dừng, dành cho xe máy (scooter).
    start_point: dict {"id": "start", "lat": 10.7, "lng": 106.6}
    waypoints: list of dict [{"id": "id1", "lat": 10.7, "lng": 106.7}]
    
    Returns: list of dicts with optimized order, and the polyline points (if requested)
    """
    if not here_api_key:
        raise ValueError("Thiếu HERE Maps API Key")
        
    url = "https://wse.ls.hereapi.com/2/findsequence.json"
    
    params = {
        "apiKey": here_api_key,
        "start": f"{start_point['lat']},{start_point['lng']}",
        "mode": "fastest;scooter;traffic:enabled"
    }
    
    for i, wp in enumerate(waypoints):
        params[f"destination{i+1}"] = f"{wp['id']};{wp['lat']},{wp['lng']}"
        
    resp = requests.get(url, params=params)
    data = resp.json()
    
    if "results" in data and len(data["results"]) > 0:
        result = data["results"][0]
        optimized_waypoints = result.get("waypoints", [])
        
        sequence = []
        for wp in optimized_waypoints:
            wp_id = wp.get("id")
            if wp_id and wp_id != "start":
                sequence.append({
                    "id": wp_id,
                    "lat": wp.get("lat"),
                    "lng": wp.get("lng"),
                    "sequence": wp.get("sequence")
                })
                
        # Call HERE Routing API to get polyline shape
        polyline_points = []
        if len(sequence) > 0:
            try:
                polyline_points = get_route_polyline(start_point, sequence, here_api_key)
            except Exception as e:
                logging.error(f"Error fetching polyline: {e}")
                
        return sequence, polyline_points
    else:
        raise Exception(f"HERE Waypoint Sequence Error: {json.dumps(data)}")

def get_route_polyline(start_point, sequence, here_api_key):
    """
    Gọi HERE Routing API v8 để lấy Polyline cho danh sách điểm đã sắp xếp
    """
    url = "https://router.hereapi.com/v8/routes"
    
    origin = start_point
    destination = sequence[-1]
    
    params = {
        "apiKey": here_api_key,
        "transportMode": "scooter",
        "origin": f"{origin['lat']},{origin['lng']}",
        "destination": f"{destination['lat']},{destination['lng']}",
        "return": "polyline"
    }
    
    vias = sequence[:-1]  # all points except destination
    if vias:
        # requests uses list for multiple parameters with same key
        params["via"] = [f"{wp['lat']},{wp['lng']}" for wp in vias]
            
    resp = requests.get(url, params=params)
    data = resp.json()
    
    points = []
    if "routes" in data and len(data["routes"]) > 0:
        try:
            import flexpolyline
            for section in data["routes"][0]["sections"]:
                pts = flexpolyline.decode(section["polyline"])
                points.extend(pts)
        except ImportError:
            logging.error("flexpolyline module not installed")
            
    return points
