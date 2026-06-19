"""
services/ai_service.py — Personalized AI Insights Engine
=========================================================
Interfaces with Gemini API using the official google-genai SDK.
Translates weekly user achievements and standings into coaching actions.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Initialize client using standard environmental variable resolution
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def generate_sustainability_insights(
    user_name: str,
    current_rank: int,
    weekly_savings_kg: float,
    family_members: List[Dict[str, Any]],
    recent_logs: List[Dict[str, Any]]
) -> str:
    """
    Produces highly tailored, actionable eco-tips matching user context.
    """
    if not GEMINI_API_KEY or genai is None or types is None:
        return (
            f"Keep up the effort, {user_name}! You have saved {weekly_savings_kg} kg of CO2 "
            f"this week and hold spot #{current_rank} on the family leaderboard."
        )

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Format family matrix for LLM consumption
    standings = []
    for m in family_members:
        standings.append(f"- {m['name']}: {m['co2_saved_total']:.1f} kg saved (Rank {m.get('rank', 'N/A')})")
    standings_str = "\n".join(standings)

    # Clean action details for prompt context
    recent_actions = [f"{log['category']}: {log['action']}" for log in recent_logs[:5]]
    actions_str = ", ".join(recent_actions) if recent_actions else "None logged yet"

    # Contextual system prompt framing
    system_instruction = (
        "You are 'Antigravity AI', an encouraging, professional, and practical green coach. "
        "Analyze the user's progress against family standings. Provide 1 to 2 sentences max "
        "of direct, highly personalized advice. Address the user directly by name. "
        "Point out a specific, realistic action based on their logs or immediate rank competitors. "
        "Avoid generalizations, fluff, or sounding overly excited. Maintain a helpful and professional tone."
    )

    prompt = (
        f"User Name: {user_name}\n"
        f"Current Leaderboard Rank: #{current_rank}\n"
        f"Your CO2 Savings This Week: {weekly_savings_kg:.2f} kg\n\n"
        f"Family Leaderboard Standing:\n{standings_str}\n\n"
        f"Recent Actions Logged:\n{actions_str}\n"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                max_output_tokens=120,
            )
        )
        return response.text.strip()
    except Exception as e:
        # Structured fallback in case of rate limits or connection interruptions
        return (
            f"Great work, {user_name}. You saved {weekly_savings_kg:.1f} kg of CO2 recently. "
            "Check back soon for optimized environmental recommendations."
        )
