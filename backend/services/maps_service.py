"""
services/maps_service.py — Google Maps Service Integration (London Centered)
"""

from __future__ import annotations
import os
import urllib.parse
import urllib.request
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from models import CommuteMode
from carbon_engine import calculate_route_savings

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


def fetch_route_details(
    origin: str,
    destination: str,
    mode: str = "driving"
) -> Optional[Dict[str, Any]]:
    """
    Query Google Directions API for distance, duration, and coordinate details.
    """
    # Preset coordinates for specific London targets
    london_db = {
        "home": (51.4875, -0.1682),        # Kensington, London
        "office": (51.5137, -0.0904),      # City of London
        "visit": (51.5033, -0.1195),       # London Eye (Visiting Place)
        "london": (51.5074, -0.1278),      # Central London
    }

    # Immediate exit if searching from a place to itself (prevents home to home showing 15km)
    if origin.lower().strip() == destination.lower().strip():
        # Get matching coordinate point
        resolved_coords = london_db.get(origin.lower().strip(), london_db["london"])
        return {
            "distance_km": 0.0,
            "duration_s": 0,
            "origin_addressed": origin.capitalize(),
            "destination_addressed": destination.capitalize(),
            "start_coords": {"lat": resolved_coords[0], "lng": resolved_coords[1]},
            "end_coords": {"lat": resolved_coords[0], "lng": resolved_coords[1]},
            "polyline": ""
        }

    if not GOOGLE_MAPS_API_KEY:
        return _mock_fallback_route(origin, destination, mode)

    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": GOOGLE_MAPS_API_KEY
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Karb0n-Backend"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        if data.get("status") != "OK":
            return None
            
        route = data["routes"][0]
        leg = route["legs"][0]
        
        start_coords = leg["start_location"]
        end_coords = leg["end_location"]
        
        return {
            "distance_km": round(leg["distance"]["value"] / 1000.0, 2),
            "duration_s": leg["duration"]["value"],
            "origin_addressed": leg["start_address"],
            "destination_addressed": leg["end_address"],
            "start_coords": {"lat": start_coords["lat"], "lng": start_coords["lng"]},
            "end_coords": {"lat": end_coords["lat"], "lng": end_coords["lng"]},
            "polyline": route.get("overview_polyline", {}).get("points", "")
        }
    except Exception:
        return None


def _mock_fallback_route(origin: str, destination: str, mode: str) -> Dict[str, Any]:
    """
    Provides fallback coordinates centered in London.
    Supports specific terms like 'home', 'office', 'visiting' or general London queries.
    """
    london_db = {
        "home": (51.4875, -0.1682),        # Kensington, London
        "office": (51.5137, -0.0904),      # City of London
        "visit": (51.5033, -0.1195),       # London Eye (Visiting Place)
        "london": (51.5074, -0.1278),      # Central London
    }

    def get_coords(name: str, seed: int) -> tuple[float, float]:
        name_clean = name.lower().strip()
        
        if "home" in name_clean:
            return london_db["home"]
        if "office" in name_clean:
            return london_db["office"]
        if "visit" in name_clean:
            return london_db["visit"]
            
        val_sum = sum(ord(c) for c in name_clean) + seed
        lat_offset = ((val_sum * 17) % 100) / 1500.0 - 0.03
        lng_offset = ((val_sum * 31) % 100) / 1500.0 - 0.03
        return 51.5074 + lat_offset, -0.1278 + lng_offset

    start_lat, start_lng = get_coords(origin, 10)
    end_lat, end_lng = get_coords(destination, 20)

    # Estimate Manhattan-style distance
    lat_diff = abs(start_lat - end_lat)
    lng_diff = abs(start_lng - end_lng)
    distance_km = round((lat_diff + lng_diff) * 111.0, 1)
    if distance_km < 1.0:
        distance_km = 4.2

    return {
        "distance_km": distance_km,
        "duration_s": int(distance_km * 140),
        "origin_addressed": origin.capitalize(),
        "destination_addressed": destination.capitalize(),
        "start_coords": {"lat": start_lat, "lng": start_lng},
        "end_coords": {"lat": end_lat, "lng": end_lng},
        "polyline": ""
    }


def process_commute_savings(
    origin: str,
    destination: str,
    chosen_mode: str,
    baseline_mode: str = "car"
) -> Dict[str, Any]:
    """
    Processes geodata and carbon offsets.
    """
    google_mode = "transit"
    if chosen_mode in (CommuteMode.BIKE, CommuteMode.EBIKE):
        google_mode = "bicycling"
    elif chosen_mode == CommuteMode.WALK:
        google_mode = "walking"
    elif chosen_mode == CommuteMode.CAR:
        google_mode = "driving"

    # Immediate safety check for same start/end inputs
    if origin.lower().strip() == destination.lower().strip():
        # Get matching coordinate point
        london_db = {
            "home": (51.4875, -0.1682),
            "office": (51.5137, -0.0904),
            "visit": (51.5033, -0.1195),
            "london": (51.5074, -0.1278),
        }
        resolved_coords = london_db.get(origin.lower().strip(), london_db["london"])
        return {
            "distance_km": 0.0,
            "duration_s": 0,
            "origin_addressed": origin.capitalize(),
            "destination_addressed": destination.capitalize(),
            "start_coords": {"lat": resolved_coords[0], "lng": resolved_coords[1]},
            "end_coords": {"lat": resolved_coords[0], "lng": resolved_coords[1]},
            "polyline": "",
            "chosen_emission_kg": 0.0,
            "baseline_emission_kg": 0.0,
            "co2_saved_kg": 0.0,
            "saved_pct": 0.0
        }

    route_data = fetch_route_details(origin, destination, google_mode)
    
    if not route_data and google_mode == "bicycling":
        route_data = fetch_route_details(origin, destination, "driving")

    if not route_data:
        route_data = _mock_fallback_route(origin, destination, google_mode)

    distance = route_data["distance_km"]
    savings_calc = calculate_route_savings(
        distance_km=distance,
        chosen_mode=chosen_mode,
        baseline_mode=baseline_mode
    )

    return {
        **route_data,
        **savings_calc
    }