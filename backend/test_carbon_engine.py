"""
Unit tests for carbon_engine.py — CO2 calculation verification
"""

import unittest
from carbon_engine import (
    calculate_daily_summary,
    calculate_route_savings,
    calculate_custom_action_saving,
    COMMUTE_DAILY_SAVINGS_KG,
    MEAL_DAILY_SAVINGS_KG,
    ENERGY_DAILY_SAVINGS_KG,
    CUSTOM_ACTION_SAVINGS_KG,
    DailySummary
)


class TestCarbonEngineCalculations(unittest.TestCase):
    """Test CO2 calculation accuracy and edge cases"""

    def test_daily_summary_vegan_walk(self):
        """Test optimal daily summary: walk + vegan"""
        result = calculate_daily_summary(
            commute_mode="walk",
            meal_type="vegan",
            energy_actions=["high_efficiency", "lights_off"],
            baseline_daily_kg=12.0
        )
        self.assertIsInstance(result, DailySummary)
        self.assertEqual(result.commute_savings_kg, 2.88)
        self.assertEqual(result.meal_savings_kg, 5.2)
        self.assertEqual(result.energy_savings_kg, 3.6)
        self.assertEqual(result.total_savings_kg, round(2.88 + 5.2 + 3.6, 2))
        self.assertGreater(result.trees_equivalent, 0)
        self.assertLessEqual(result.reduction_pct, 100.0)

    def test_daily_summary_car_meat_heavy(self):
        """Test baseline daily summary: car + meat-heavy"""
        result = calculate_daily_summary(
            commute_mode="car",
            meal_type="meat-heavy",
            energy_actions=[],
            baseline_daily_kg=12.0
        )
        self.assertEqual(result.commute_savings_kg, 0.0)
        self.assertEqual(result.meal_savings_kg, 0.0)
        self.assertEqual(result.energy_savings_kg, 0.0)
        self.assertEqual(result.total_savings_kg, 0.0)
        self.assertEqual(result.reduction_pct, 0.0)

    def test_daily_summary_multiple_energy_actions(self):
        """Test stacking multiple energy actions"""
        result = calculate_daily_summary(
            commute_mode="bike",
            meal_type="meat-light",
            energy_actions=["high_efficiency", "lights_off", "led_upgrade", "solar_active"],
            baseline_daily_kg=12.0
        )
        expected_energy = 2.4 + 1.2 + 0.8 + 3.5
        self.assertAlmostEqual(result.energy_savings_kg, expected_energy, places=1)

    def test_route_savings_ebike_vs_car(self):
        """Test route savings calculation: e-bike 5km vs car baseline"""
        result = calculate_route_savings(
            distance_km=5.0,
            chosen_mode="ebike",
            baseline_mode="car"
        )
        self.assertEqual(result["distance_km"], 5.0)
        self.assertEqual(result["chosen_mode"], "ebike")
        self.assertEqual(result["chosen_emission_kg"], round(5.0 * 0.008, 3))
        self.assertEqual(result["baseline_emission_kg"], round(5.0 * 0.192, 3))
        self.assertGreater(result["co2_saved_kg"], 0)
        self.assertGreater(result["saved_pct"], 0)

    def test_route_savings_walk_zero_distance(self):
        """Test route savings with zero distance"""
        result = calculate_route_savings(
            distance_km=0.0,
            chosen_mode="walk",
            baseline_mode="car"
        )
        self.assertEqual(result["distance_km"], 0.0)
        self.assertEqual(result["co2_saved_kg"], 0.0)
        self.assertEqual(result["saved_pct"], 0.0)

    def test_route_savings_transit_long_distance(self):
        """Test route savings for transit over 50km"""
        result = calculate_route_savings(
            distance_km=50.0,
            chosen_mode="transit",
            baseline_mode="car"
        )
        self.assertGreater(result["co2_saved_kg"], 0)
        self.assertAlmostEqual(
            result["co2_saved_kg"],
            round(50.0 * (0.192 - 0.041), 3)
        )

    def test_custom_action_saving_valid(self):
        """Test custom action CO2 savings"""
        self.assertEqual(calculate_custom_action_saving("led"), 1.20)
        self.assertEqual(calculate_custom_action_saving("tree"), 15.00)
        self.assertEqual(calculate_custom_action_saving("recycle"), 0.80)
        self.assertEqual(calculate_custom_action_saving("compost"), 2.10)

    def test_custom_action_saving_invalid(self):
        """Test invalid custom action returns zero"""
        self.assertEqual(calculate_custom_action_saving("invalid_action"), 0.0)

    def test_coefficient_table_consistency(self):
        """Test that all coefficient tables are properly defined"""
        self.assertGreater(len(COMMUTE_DAILY_SAVINGS_KG), 0)
        self.assertGreater(len(MEAL_DAILY_SAVINGS_KG), 0)
        self.assertGreater(len(ENERGY_DAILY_SAVINGS_KG), 0)
        self.assertGreater(len(CUSTOM_ACTION_SAVINGS_KG), 0)

        for value in COMMUTE_DAILY_SAVINGS_KG.values():
            self.assertGreaterEqual(value, 0.0)
        for value in MEAL_DAILY_SAVINGS_KG.values():
            self.assertGreaterEqual(value, 0.0)

    def test_reduction_percentage_capped_at_100(self):
        """Test that reduction percentage never exceeds 100%"""
        result = calculate_daily_summary(
            commute_mode="walk",
            meal_type="vegan",
            energy_actions=["high_efficiency", "lights_off", "solar_active"],
            baseline_daily_kg=1.0  # Very low baseline
        )
        self.assertLessEqual(result.reduction_pct, 100.0)

    def test_trees_equivalent_positive(self):
        """Test that tree equivalent is positive for positive savings"""
        result = calculate_daily_summary(
            commute_mode="bike",
            meal_type="vegan",
            energy_actions=["high_efficiency"],
            baseline_daily_kg=12.0
        )
        self.assertGreater(result.trees_equivalent, 0)

    def test_trees_equivalent_zero_savings(self):
        """Test that tree equivalent is zero for zero savings"""
        result = calculate_daily_summary(
            commute_mode="car",
            meal_type="meat-heavy",
            energy_actions=[],
            baseline_daily_kg=12.0
        )
        self.assertEqual(result.trees_equivalent, 0.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_empty_energy_actions(self):
        """Test with empty energy actions list"""
        result = calculate_daily_summary(
            commute_mode="bike",
            meal_type="vegan",
            energy_actions=[],
            baseline_daily_kg=12.0
        )
        self.assertEqual(result.energy_savings_kg, 0.0)

    def test_negative_baseline_not_capped(self):
        """Test with invalid negative baseline (calculation still proceeds)"""
        result = calculate_daily_summary(
            commute_mode="walk",
            meal_type="vegan",
            energy_actions=[],
            baseline_daily_kg=-12.0
        )
        # Negative baseline will result in negative reduction %, but should not crash
        self.assertIsNotNone(result.reduction_pct)
        self.assertIsInstance(result.total_savings_kg, float)

    def test_very_large_distance(self):
        """Test route savings with very large distance"""
        result = calculate_route_savings(
            distance_km=1000.0,
            chosen_mode="transit",
            baseline_mode="car"
        )
        self.assertGreater(result["co2_saved_kg"], 0)
        self.assertIsNotNone(result["saved_pct"])


if __name__ == "__main__":
    unittest.main()
