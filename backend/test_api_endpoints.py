"""
Integration tests for FastAPI endpoints
Tests API contract, input validation, and error handling
"""

import unittest
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from main import app


class TestAPIHealthEndpoint(unittest.TestCase):
    """Test health check endpoint"""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_returns_200(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.json())

    def test_health_check_response_structure(self):
        response = self.client.get("/api/health")
        data = response.json()
        self.assertIn("ok", data)
        self.assertIn("gemini_configured", data)
        self.assertIn("google_maps_configured", data)


class TestDailyLoggingEndpoint(unittest.TestCase):
    """Test daily logging endpoint validation and error handling"""

    def setUp(self):
        self.client = TestClient(app)

    def test_daily_logging_invalid_user_id(self):
        """Test that invalid user_id is rejected"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "invalid@user!id",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": []
        })
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_daily_logging_missing_fields(self):
        """Test that missing required fields are rejected"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "user_alex",
            "commute_mode": "bike"
        })
        self.assertEqual(response.status_code, 422)

    def test_daily_logging_empty_user_id(self):
        """Test that empty user_id is rejected"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": []
        })
        self.assertEqual(response.status_code, 422)

    def test_daily_logging_notes_max_length(self):
        """Test that notes exceeding max length are rejected"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "user_alex",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": [],
            "notes": "x" * 1000  # Exceeds max length
        })
        self.assertEqual(response.status_code, 422)


class TestCustomLogEndpoint(unittest.TestCase):
    """Test custom impact logging endpoint"""

    def setUp(self):
        self.client = TestClient(app)

    def test_custom_log_invalid_action_key(self):
        """Test that invalid action_key is rejected"""
        response = self.client.post("/api/logs/custom", json={
            "user_id": "user_alex",
            "action_key": "invalid_action",
            "label": "Test action"
        })
        self.assertEqual(response.status_code, 422)

    def test_custom_log_valid_actions(self):
        """Test that valid action keys are accepted"""
        for action in ["led", "tree", "recycle", "bag", "compost"]:
            response = self.client.post("/api/logs/custom", json={
                "user_id": "user_alex",
                "action_key": action,
                "label": f"Test {action}"
            })
            # Should either succeed (201/200) or fail due to user not found (404)
            self.assertIn(response.status_code, [200, 201, 404])

    def test_custom_log_user_not_found(self):
        """Test that non-existent user returns 404"""
        response = self.client.post("/api/logs/custom", json={
            "user_id": "nonexistent_user_xyz",
            "action_key": "led",
            "label": "Test"
        })
        self.assertEqual(response.status_code, 404)

    def test_custom_log_response_structure(self):
        """Test response structure for custom logging"""
        response = self.client.post("/api/logs/custom", json={
            "user_id": "user_alex",
            "action_key": "led",
            "label": "Test LED upgrade"
        })
        if response.status_code in [200, 201]:
            data = response.json()
            self.assertIn("success", data)
            self.assertIn("co2_saved_kg", data)


class TestRoutePlanningEndpoint(unittest.TestCase):
    """Test route planning endpoint"""

    def setUp(self):
        self.client = TestClient(app)

    def test_route_plan_invalid_user_id(self):
        """Test that invalid user_id is rejected"""
        response = self.client.post("/api/route/plan", json={
            "user_id": "invalid@user!",
            "origin": "home",
            "destination": "office",
            "chosen_mode": "ebike"
        })
        self.assertEqual(response.status_code, 422)

    def test_route_plan_missing_fields(self):
        """Test that missing required fields are rejected"""
        response = self.client.post("/api/route/plan", json={
            "user_id": "user_alex",
            "origin": "home"
        })
        self.assertEqual(response.status_code, 422)

    def test_route_plan_response_structure(self):
        """Test route plan response structure"""
        response = self.client.post("/api/route/plan", json={
            "user_id": "user_alex",
            "origin": "home",
            "destination": "office",
            "chosen_mode": "ebike",
            "baseline_mode": "car"
        })
        if response.status_code in [200, 201]:
            data = response.json()
            self.assertIn("distance_km", data)
            self.assertIn("duration_s", data)
            self.assertIn("co2_saved_kg", data)


class TestLeaderboardEndpoint(unittest.TestCase):
    """Test leaderboard endpoint"""

    def setUp(self):
        self.client = TestClient(app)

    def test_leaderboard_missing_user_id_param(self):
        """Test that missing user_id query param is rejected"""
        response = self.client.get("/api/leaderboard/circle_demo_01")
        self.assertEqual(response.status_code, 422)

    def test_leaderboard_invalid_circle_id(self):
        """Test invalid circle_id returns 404"""
        response = self.client.get("/api/leaderboard/nonexistent_circle", params={"user_id": "user_alex"})
        self.assertEqual(response.status_code, 404)


class TestInputValidation(unittest.TestCase):
    """Test comprehensive input validation"""

    def setUp(self):
        self.client = TestClient(app)

    def test_xss_attempt_in_notes(self):
        """Test that XSS payloads in notes don't cause errors"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "user_alex",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": [],
            "notes": "<script>alert('xss')</script>"
        })
        # Should either validate and accept (treated as string) or reject via validation
        self.assertIn(response.status_code, [200, 201, 422, 404])

    def test_sql_injection_attempt_in_user_id(self):
        """Test that SQL injection attempts are blocked"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "user_alex'; DROP TABLE users; --",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": []
        })
        # Should be rejected due to validation
        self.assertEqual(response.status_code, 422)

    def test_unicode_characters_in_notes(self):
        """Test that unicode characters are handled safely"""
        response = self.client.post("/api/logs/daily", json={
            "user_id": "user_alex",
            "commute_mode": "bike",
            "meal_type": "vegan",
            "energy_actions": [],
            "notes": "日本語テキスト 🌍🚴‍♂️"
        })
        self.assertIn(response.status_code, [200, 201, 404])


if __name__ == "__main__":
    unittest.main()
