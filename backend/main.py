"""
main.py — Karbon.io REST API Entrypoint (with Live Firestore Tracer)
=====================================================================
"""

from __future__ import annotations
import sys
from pathlib import Path

# Insert absolute paths into Python's import search list
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import os
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, validator
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

import karbon_db as db
import carbon_engine
from services import maps_service, ai_service, leaderboard_service


# --- Modern Lifespan Diagnostics Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*50)
    print("[BACKEND STARTUP] Initializing Firestore Connection...")
    print("="*50)
    try:
        db.init_db()
        print("[BACKEND SUCCESS] Firestore connected and seeded successfully!")
    except Exception as e:
        print(f"[BACKEND ERROR] Database initialization failed: {str(e)}")
        print("[BACKEND ERROR] Please verify your key exists at: backend/firebase-key.json")
    print("="*50 + "\n")
    yield


app = FastAPI(
    title="Karb0n Backend Engine (Antigravity)",
    description="Micro-service orchestration for personal and family carbon analytics.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS with restricted origins
allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# --- API Model Definitions with Validation ---
class CustomLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    action_key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(default="", max_length=256)

    @validator('user_id')
    def validate_user_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid user_id format")
        return v

    @validator('action_key')
    def validate_action_key(cls, v):
        valid_actions = {"led", "tree", "recycle", "bag", "compost"}
        if v not in valid_actions:
            raise ValueError(f"Invalid action_key. Must be one of {valid_actions}")
        return v

class DailyLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    commute_mode: str = Field(..., min_length=1, max_length=64)
    meal_type: str = Field(..., min_length=1, max_length=64)
    energy_actions: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=512)

    @validator('user_id')
    def validate_user_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid user_id format")
        return v

class RoutePlanRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    origin: str = Field(..., min_length=1, max_length=256)
    destination: str = Field(..., min_length=1, max_length=256)
    chosen_mode: str = Field(..., min_length=1, max_length=64)
    baseline_mode: str = Field(default="car", max_length=64)

    @validator('user_id')
    def validate_user_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid user_id format")
        return v


# --- API Routes ---

@app.get("/api/db/seed")
def force_seed_database():
    """
    Advanced Live Tracer Endpoint:
    Forces seeding, writes a test connection document, and reads back the results.
    """
    try:
        project_id = db.db_client.project
        test_ref = db.db_client.collection("diagnostics").document("test_connection")
        test_ref.set({
            "timestamp": "active",
            "status": "connected",
            "message": "Tracer successfully bypassed cache and wrote to Firestore!"
        })
        db.init_db()
        users = db.db_client.collection("users").get()
        user_ids = [u.id for u in users]

        return {
            "status": "success",
            "connected_project_id": project_id,
            "test_document_written": True,
            "seeded_users": user_ids,
            "message": "Tracer complete. See connected_project_id and seeded_users above."
        }
    except Exception as e:
        logger.error(f"Firestore connection failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed. Please try again later."
        )


@app.get("/api/health")
def health_check():
    """Health status check to verify loaded API configurations."""
    return {
        "ok": True,
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "google_maps_configured": bool(os.environ.get("GOOGLE_MAPS_API_KEY"))
    }


@app.post("/api/logs/daily", status_code=status.HTTP_201_CREATED)
def log_daily_summary(payload: DailyLogRequest):
    """
    Computes summary savings and registers them as persistent daily activity logs.
    """
    try:
        user = db.get_user(payload.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        summary = carbon_engine.calculate_daily_summary(
            commute_mode=payload.commute_mode,
            meal_type=payload.meal_type,
            energy_actions=payload.energy_actions,
            baseline_daily_kg=user.get("baseline_daily_kg", 12.0)
        )

        db.insert_activity_log(
            user_id=payload.user_id,
            category="commute",
            action=payload.commute_mode,
            co2_saved_kg=summary.commute_savings_kg,
            notes=payload.notes or "Daily commute logging"
        )

        db.insert_activity_log(
            user_id=payload.user_id,
            category="meals",
            action=payload.meal_type,
            co2_saved_kg=summary.meal_savings_kg,
            notes=payload.notes or "Daily diet logging"
        )

        if payload.energy_actions:
            for action in payload.energy_actions:
                db.insert_activity_log(
                    user_id=payload.user_id,
                    category="energy",
                    action=action,
                    co2_saved_kg=carbon_engine.ENERGY_DAILY_SAVINGS_KG.get(action, 0.0),
                    notes=payload.notes or "Daily energy actions"
                )

        return {
            "success": True,
            "co2_saved_total_kg": summary.total_savings_kg,
            "trees_equivalent": summary.trees_equivalent,
            "reduction_pct": summary.reduction_pct
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging daily summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log daily summary. Please try again."
        )


@app.post("/api/route/plan")
def plan_route_simulation(payload: RoutePlanRequest):
    try:
        route_details = maps_service.process_commute_savings(
            origin=payload.origin,
            destination=payload.destination,
            chosen_mode=payload.chosen_mode,
            baseline_mode=payload.baseline_mode
        )
        return route_details
    except Exception as e:
        logger.error(f"Error planning route: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to plan route. Please check your input."
        )


@app.post("/api/logs/route")
def plan_and_log_route(payload: RoutePlanRequest):
    user = db.get_user(payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User reference not found.")

    try:
        route_details = maps_service.process_commute_savings(
            origin=payload.origin,
            destination=payload.destination,
            chosen_mode=payload.chosen_mode,
            baseline_mode=payload.baseline_mode
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.insert_route_log(
        user_id=payload.user_id,
        origin=route_details["origin_addressed"],
        destination=route_details["destination_addressed"],
        distance_km=route_details["distance_km"],
        mode=payload.chosen_mode,
        co2_saved_kg=route_details["co2_saved_kg"],
        maps_duration_s=route_details["duration_s"]
    )

    return route_details


@app.get("/api/leaderboard/{circle_id}")
def get_leaderboard(circle_id: str, user_id: str):
    leaderboard = leaderboard_service.get_family_leaderboard(circle_id, user_id)
    if not leaderboard:
        raise HTTPException(status_code=404, detail="Leaderboard circle empty or invalid.")
    return leaderboard


@app.get("/api/users/{user_id}/insights")
def get_user_insights(user_id: str):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    circle_id = user.get("family_circle_id")
    if not circle_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a family circle.")

    leaderboard = leaderboard_service.get_family_leaderboard(circle_id, user_id)
    
    current_rank = 1
    for entry in leaderboard:
        if entry.user_id == user_id:
            current_rank = entry.rank
            break

    weekly_logs = db.get_weekly_logs(user_id, days=7)
    weekly_savings = sum(log["co2_saved_kg"] for log in weekly_logs)

    family_members_payload = [
        {
            "name": entry.name,
            "co2_saved_total": entry.co2_saved_total,
            "rank": entry.rank
        }
        for entry in leaderboard
    ]

    insights = ai_service.generate_sustainability_insights(
        user_name=user["name"],
        current_rank=current_rank,
        weekly_savings_kg=weekly_savings,
        family_members=family_members_payload,
        recent_logs=weekly_logs
    )

    return {
        "user_id": user_id,
        "weekly_savings_kg": round(weekly_savings, 2),
        "rank": current_rank,
        "insight_tip": insights
    }

@app.post("/api/logs/custom")
def log_custom_impact(payload: CustomLogRequest):
    """
    Computes carbon savings for one-off custom actions and logs them.
    """
    user = db.get_user(payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User reference not found."
        )
    
    # Fetch exact carbon factor from the math engine
    co2_saved = carbon_engine.calculate_custom_action_saving(payload.action_key)
    
    db.insert_activity_log(
        user_id=payload.user_id,
        category="custom",
        action=payload.action_key,
        co2_saved_kg=co2_saved,
        notes=payload.label
    )
    
    return {
        "success": True,
        "co2_saved_kg": co2_saved
    }