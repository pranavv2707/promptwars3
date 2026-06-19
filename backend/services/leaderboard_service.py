"""
services/leaderboard_service.py — Leaderboard Computation Matrix
==============================================================
Calculates individual and group carbon reduction percentages against 
established baselines.
"""

from __future__ import annotations
import karbon_db as db
from models import LeaderboardEntry


def get_family_leaderboard(circle_id: str, current_user_id: str) -> list[LeaderboardEntry]:
    """
    Compiles the live leaderboard metrics for a designated family circle.
    
    Formula:
      reduction_pct = (monthly_savings / (baseline_daily_kg * 30 days)) * 100
    """
    members = db.get_circle_members(circle_id)
    if not members:
        return []

    entries: list[LeaderboardEntry] = []
    
    for user in members:
        # Determine current month footprint reduction efficiency
        baseline_daily = user.get("baseline_daily_kg", 12.0)
        expected_monthly_footprint = baseline_daily * 30.0
        
        monthly_saved = user.get("co2_saved_month", 0.0)
        
        if expected_monthly_footprint > 0:
            reduction_pct = round((monthly_saved / expected_monthly_footprint) * 100.0, 1)
        else:
            reduction_pct = 0.0

        # Enforce mathematical bound to maintain logic consistency
        reduction_pct = min(reduction_pct, 100.0)

        entries.append(
            LeaderboardEntry(
                rank=0, # Assigned dynamically below after sorting
                user_id=user["user_id"],
                name=user["name"],
                location=user["location"],
                co2_saved_total=round(user["co2_saved_total"], 2),
                co2_saved_month=round(monthly_saved, 2),
                reduction_pct=reduction_pct,
                is_current_user=(user["user_id"] == current_user_id)
            )
        )

    # Sort primarily by monthly savings to prioritize current active habits
    entries.sort(key=lambda x: x.co2_saved_month, reverse=True)

    for index, entry in enumerate(entries):
        entry.rank = index + 1

    return entries