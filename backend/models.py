"""
models.py — Karbon.io Data Models
Lightweight dataclasses for Users, Family Circles, and Activity Logs.
No ORM needed — state is persisted in a local SQLite DB via db.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums — constrain category inputs for type-safety and clear coefficients
# ---------------------------------------------------------------------------

class CommuteMode(str, Enum):
    WALK    = "walk"
    BIKE    = "bike"
    TRANSIT = "transit"
    CAR     = "car"
    EBIKE   = "ebike"
    BUS     = "bus"


class MealType(str, Enum):
    VEGAN       = "vegan"
    VEGETARIAN  = "vegetarian"
    MEAT_LIGHT  = "meat-light"
    MEAT_HEAVY  = "meat-heavy"


class EnergyAction(str, Enum):
    HIGH_EFFICIENCY = "high_efficiency"
    LIGHTS_OFF      = "lights_off"
    SOLAR_ACTIVE    = "solar_active"
    LED_UPGRADE     = "led_upgrade"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class User:
    """A Karbon.io app user."""
    user_id:         str
    name:            str
    location:        str              = "Unknown"
    family_circle_id: Optional[str]  = None
    level:           int              = 1
    # Cumulative CO2 saved (kg) — updated on each confirmed activity log
    co2_saved_total: float            = 0.0
    co2_saved_month: float            = 0.0
    baseline_daily_kg: float          = 12.0  # average global per-person daily footprint


@dataclass
class FamilyCircle:
    """A group of Users competing on the same leaderboard."""
    circle_id:   str
    circle_name: str
    member_ids:  list[str] = field(default_factory=list)


@dataclass
class ActivityLog:
    """
    A single logged activity entry for a user on a given day.
    co2_saved_kg is derived by the carbon engine — not user-supplied.
    """
    log_id:       str
    user_id:      str
    log_date:     date
    category:     str        # "commute" | "meals" | "energy" | "custom"
    action:       str        # e.g. "bike", "vegan", "lights_off"
    co2_saved_kg: float      = 0.0
    distance_km:  float      = 0.0   # used for route-based commute logs
    notes:        str        = ""


@dataclass
class RouteLog:
    """
    Extended log for a planned/confirmed commute via the Route Planner.
    Includes Maps API metadata alongside the carbon calculation.
    """
    log_id:           str
    user_id:          str
    log_date:         date
    origin:           str
    destination:      str
    distance_km:      float
    mode:             CommuteMode
    co2_saved_kg:     float  = 0.0
    maps_duration_s:  int    = 0     # seconds, from Directions API


@dataclass
class LeaderboardEntry:
    """A single row in the computed leaderboard."""
    rank:            int
    user_id:         str
    name:            str
    location:        str
    co2_saved_total: float
    co2_saved_month: float
    reduction_pct:   float   # % reduction vs. their personal baseline
    is_current_user: bool = False
