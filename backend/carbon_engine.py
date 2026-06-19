"""
carbon_engine.py — Karbon.io CO2 Calculation Engine
=====================================================
Single source of truth for all carbon coefficient math.
All coefficients are documented with their source assumptions in README.md.

Emission factors represent kg CO2 *saved* vs. an average high-carbon baseline:
  - Commute baseline: single-occupancy petrol car (~0.192 kg CO2/km)
  - Diet baseline: omnivore diet (~7.0 kg CO2/day from food)
  - Energy baseline: average UK/US household (12 kWh/day, ~0.45 kg CO2/kWh)
"""

from __future__ import annotations
from dataclasses import dataclass
from models import CommuteMode, MealType, EnergyAction


# ---------------------------------------------------------------------------
# 1. Emission Coefficient Tables
# ---------------------------------------------------------------------------

# kg CO2 emitted per km per mode (absolute, not relative savings)
# Sources: UK Dept for Transport, EPA, IPCC AR6
COMMUTE_EMISSION_KG_PER_KM: dict[str, float] = {
    CommuteMode.CAR:     0.192,   # avg petrol car, single occupancy
    CommuteMode.BUS:     0.089,   # avg diesel bus, shared occupancy
    CommuteMode.TRANSIT: 0.041,   # avg electric metro/rail
    CommuteMode.EBIKE:   0.008,   # e-bike (embodied + charging electricity)
    CommuteMode.BIKE:    0.000,   # zero direct emissions
    CommuteMode.WALK:    0.000,   # zero direct emissions
}

# For the fixed daily activity logger (no distance), we show daily savings
# vs. an average car commute of 15 km/day baseline
_BASELINE_CAR_15KM = 15 * COMMUTE_EMISSION_KG_PER_KM[CommuteMode.CAR]  # 2.88 kg

COMMUTE_DAILY_SAVINGS_KG: dict[str, float] = {
    CommuteMode.WALK:    round(_BASELINE_CAR_15KM - 0.0,   2),   # 2.88
    CommuteMode.BIKE:    round(_BASELINE_CAR_15KM - 0.0,   2),   # 2.88
    CommuteMode.EBIKE:   round(_BASELINE_CAR_15KM - 15 * COMMUTE_EMISSION_KG_PER_KM[CommuteMode.EBIKE], 2),  # 2.76
    CommuteMode.TRANSIT: round(_BASELINE_CAR_15KM - 15 * COMMUTE_EMISSION_KG_PER_KM[CommuteMode.TRANSIT], 2), # 2.265
    CommuteMode.BUS:     round(_BASELINE_CAR_15KM - 15 * COMMUTE_EMISSION_KG_PER_KM[CommuteMode.BUS], 2),    # 1.545
    CommuteMode.CAR:     0.0,
}

# kg CO2 saved per day vs. omnivore heavy-meat baseline (~7.0 kg CO2/day)
# Sources: Oxford University (Poore & Nemecek 2018), OurWorldInData
MEAL_DAILY_SAVINGS_KG: dict[str, float] = {
    MealType.VEGAN:       5.20,   # 7.0 - 1.8 (vegan diet)
    MealType.VEGETARIAN:  3.60,   # 7.0 - 3.4 (vegetarian)
    MealType.MEAT_LIGHT:  1.60,   # 7.0 - 5.4 (low meat)
    MealType.MEAT_HEAVY:  0.00,   # baseline
}

# kg CO2 saved per day per action
# Sources: Energy Saving Trust, US EIA
ENERGY_DAILY_SAVINGS_KG: dict[str, float] = {
    EnergyAction.HIGH_EFFICIENCY: 2.40,  # smart thermostat + HVAC optimization
    EnergyAction.LIGHTS_OFF:      1.20,  # eliminating idle lighting
    EnergyAction.LED_UPGRADE:     0.80,  # replacing incandescent bulbs
    EnergyAction.SOLAR_ACTIVE:    3.50,  # home solar (avg 5kWh/day offset)
}

# Custom one-off action savings (kg CO2 per event)
CUSTOM_ACTION_SAVINGS_KG: dict[str, float] = {
    "led":      1.20,
    "tree":    15.00,
    "recycle":  0.80,
    "bag":      0.50,
    "compost":  2.10,
}


# ---------------------------------------------------------------------------
# 2. Calculation Functions
# ---------------------------------------------------------------------------

@dataclass
class DailySummary:
    """Structured breakdown of a user's daily carbon savings."""
    commute_savings_kg:  float
    meal_savings_kg:     float
    energy_savings_kg:   float
    total_savings_kg:    float
    trees_equivalent:    float   # trees planted equivalent (1 tree ≈ 20 kg CO2/yr)
    reduction_pct:       float   # % reduction from personal daily baseline


def calculate_daily_summary(
    commute_mode: str,
    meal_type: str,
    energy_actions: list[str],
    baseline_daily_kg: float = 12.0,
) -> DailySummary:
    """
    Compute the full daily carbon savings breakdown for a user's logged choices.

    Args:
        commute_mode:      One of CommuteMode values.
        meal_type:         One of MealType values.
        energy_actions:    List of EnergyAction values active today.
        baseline_daily_kg: User's personal high-carbon baseline (kg CO2/day).

    Returns:
        DailySummary with per-category and total savings.
    """
    commute_kg = COMMUTE_DAILY_SAVINGS_KG.get(commute_mode, 0.0)
    meal_kg    = MEAL_DAILY_SAVINGS_KG.get(meal_type, 0.0)
    energy_kg  = sum(ENERGY_DAILY_SAVINGS_KG.get(a, 0.0) for a in energy_actions)

    total_kg   = round(commute_kg + meal_kg + energy_kg, 2)
    trees_eq   = round(total_kg / (20.0 / 365), 2)   # normalize to daily tree absorption
    reduction  = round((total_kg / baseline_daily_kg) * 100, 1) if baseline_daily_kg else 0.0

    return DailySummary(
        commute_savings_kg=round(commute_kg, 2),
        meal_savings_kg=round(meal_kg, 2),
        energy_savings_kg=round(energy_kg, 2),
        total_savings_kg=total_kg,
        trees_equivalent=trees_eq,
        reduction_pct=min(reduction, 100.0),
    )


def calculate_route_savings(
    distance_km: float,
    chosen_mode: str,
    baseline_mode: str = CommuteMode.CAR,
) -> dict:
    """
    Calculate CO2 saved for a specific route by comparing chosen mode
    against a baseline mode (default: single-occupancy car).

    Args:
        distance_km:   Trip distance in kilometres.
        chosen_mode:   The mode the user selected (e.g. "ebike").
        baseline_mode: The comparison baseline (default "car").

    Returns:
        dict with chosen_kg, baseline_kg, saved_kg, saved_pct.
    """
    chosen_kg   = round(distance_km * COMMUTE_EMISSION_KG_PER_KM.get(chosen_mode, 0.0), 3)
    baseline_kg = round(distance_km * COMMUTE_EMISSION_KG_PER_KM.get(baseline_mode, 0.192), 3)
    saved_kg    = round(max(baseline_kg - chosen_kg, 0.0), 3)
    saved_pct   = round((saved_kg / baseline_kg * 100) if baseline_kg else 0.0, 1)

    return {
        "distance_km":  distance_km,
        "chosen_mode":  chosen_mode,
        "baseline_mode": baseline_mode,
        "chosen_emission_kg":   chosen_kg,
        "baseline_emission_kg": baseline_kg,
        "co2_saved_kg":  saved_kg,
        "saved_pct":     saved_pct,
    }


def calculate_custom_action_saving(action_key: str) -> float:
    """Return the CO2 saving (kg) for a one-off custom action."""
    return CUSTOM_ACTION_SAVINGS_KG.get(action_key, 0.0)
