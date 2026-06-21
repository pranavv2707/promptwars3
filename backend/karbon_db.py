"""
backend/karbon_db.py — Carbon Footprint Firebase Persistence Layer
==================================================================
Uses Cloud Firestore instead of SQLite.
"""

from __future__ import annotations
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import firebase_admin
from firebase_admin import credentials, firestore

# Self-healing key path resolution: search in current folder, parent, and grandparent
KEY_PATH = None
for directory in [Path(__file__).parent, Path(__file__).parent.parent, Path(__file__).parent.parent.parent]:
    candidate = directory / "firebase-key.json"
    if candidate.exists():
        KEY_PATH = candidate
        break

if not firebase_admin._apps:
    if KEY_PATH:
        print(f"[FIREBASE] Successfully located credentials key at: {KEY_PATH}")
        cred = credentials.Certificate(str(KEY_PATH))
        firebase_admin.initialize_app(cred)
    else:
        raise FileNotFoundError(
            "Firebase private key file 'firebase-key.json' not found. "
            "Please ensure it is uploaded in the backend/ folder or as a secret file."
        )

# EXPLICITLY INITIALIZE THE CLIENT GLOBALLY AFTER APP AUTHENTICATION
db_client = firestore.client()


# ---------------------------------------------------------------------------
# Database Seeding for Demo Standings
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Initializes collections and seeds demo leaderboard users if empty."""
    users_ref = db_client.collection("users")
    
    # Check if we have users already to avoid duplicate seeding
    existing_users = users_ref.limit(1).get()
    if len(existing_users) == 0:
        _seed_demo_data()


def _seed_demo_data() -> None:
    """Seeds the demo leaderboard users into Firestore."""
    circle_id = "circle_demo_01"
    
    # 1. Create family circle
    db_client.collection("family_circles").document(circle_id).set({
        "circle_name": "Global Guardians",
        "member_ids": ["user_alex", "user_elena", "user_hiroshi", "user_sofia", "user_jordan"]
    })

    # 2. Add demo users (Using Kensington, London for Alex Chen)
    demo_users = [
        ("user_alex",    "Alex Chen",        "Kensington, London", 42, 1894.2, 320.4, 12.0),
        ("user_elena",   "Elena Greenheart", "Oslo, Norway",      58, 2482.5, 395.2, 12.0),
        ("user_hiroshi", "Hiroshi Tanaka",   "Kyoto, Japan",      51, 2310.1, 410.5, 12.0),
        ("user_sofia",   "Sofia Rossi",      "Milan, Italy",      47, 2155.8, 298.1, 12.0),
        ("user_jordan",  "Jordan Smith",     "Austin, USA",       39, 1980.4, 240.2, 12.0),
    ]

    for uid, name, loc, level, saved_total, saved_month, baseline in demo_users:
        db_client.collection("users").document(uid).set({
            "user_id": uid,
            "name": name,
            "location": loc,
            "family_circle_id": circle_id,
            "level": level,
            "co2_saved_total": float(saved_total),
            "co2_saved_month": float(saved_month),
            "baseline_daily_kg": float(baseline),
            "created_at": datetime.utcnow().isoformat()
        })


# ---------------------------------------------------------------------------
# CRUD Implementations
# ---------------------------------------------------------------------------

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user document by ID."""
    doc = db_client.collection("users").document(user_id).get()
    return doc.to_dict() if doc.exists else None


def update_user_co2(user_id: str, delta_kg: float) -> None:
    """Atomically updates cumulative and monthly totals in Firestore."""
    user_ref = db_client.collection("users").document(user_id)
    user_ref.update({
        "co2_saved_total": firestore.Increment(delta_kg),
        "co2_saved_month": firestore.Increment(delta_kg)
    })


def get_circle_members(circle_id: str) -> List[Dict[str, Any]]:
    """Retrieves all user documents matching a specific family circle ID."""
    query = db_client.collection("users").where("family_circle_id", "==", circle_id).get()
    return [doc.to_dict() for doc in query]


def insert_activity_log(
    user_id: str,
    category: str,
    action: str,
    co2_saved_kg: float,
    distance_km: float = 0.0,
    notes: str = "",
    log_date: Optional[date] = None,
) -> str:
    """Inserts a new activity log entry and updates user totals."""
    log_id = str(uuid.uuid4())
    resolved_date = (log_date or date.today()).isoformat()
    
    log_data = {
        "log_id": log_id,
        "user_id": user_id,
        "log_date": resolved_date,
        "category": category,
        "action": action,
        "co2_saved_kg": float(co2_saved_kg),
        "distance_km": float(distance_km),
        "notes": notes,
        "created_at": datetime.utcnow().isoformat()
    }
    
    db_client.collection("activity_logs").document(log_id).set(log_data)
    update_user_co2(user_id, co2_saved_kg)
    return log_id


def insert_route_log(
    user_id: str,
    origin: str,
    destination: str,
    distance_km: float,
    mode: str,
    co2_saved_kg: float,
    maps_duration_s: int = 0,
) -> str:
    """Inserts an extended route log entry and updates user totals."""
    log_id = str(uuid.uuid4())
    resolved_date = date.today().isoformat()
    
    route_data = {
        "log_id": log_id,
        "user_id": user_id,
        "log_date": resolved_date,
        "origin": origin,
        "destination": destination,
        "distance_km": float(distance_km),
        "mode": mode,
        "co2_saved_kg": float(co2_saved_kg),
        "maps_duration_s": int(maps_duration_s),
        "created_at": datetime.utcnow().isoformat()
    }
    
    db_client.collection("route_logs").document(log_id).set(route_data)
    update_user_co2(user_id, co2_saved_kg)
    return log_id


def get_weekly_logs(user_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """Retrieves activity logs for the past N days for a user."""
    cutoff_date = (date.today() - timedelta(days=days)).isoformat()
    
    query = (
        db_client.collection("activity_logs")
        .where("user_id", "==", user_id)
        .get()
    )
    
    logs = []
    for doc in query:
        data = doc.to_dict()
        if data.get("log_date", "") >= cutoff_date:
            logs.append(data)
            
    logs.sort(key=lambda x: x.get("log_date", ""), reverse=True)
    return logs