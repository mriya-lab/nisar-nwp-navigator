import unittest

import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import LineString

from app.routing import evaluate_corridor


class CorridorCoverageTests(unittest.TestCase):
    def setUp(self):
        self.hazard = np.ones((10, 10), dtype=np.uint8)
        self.transform = from_origin(-95.0, 75.5, 0.1, 0.1)

    def evaluate(self, start_lon, end_lon):
        route = LineString([(start_lon, 75.0), (end_lon, 75.0)])
        return evaluate_corridor(route, self.hazard, self.transform, "EPSG:4326")

    def test_partial_scene_reports_coverage_and_withholds_trip_estimates(self):
        result = self.evaluate(-96.0, -94.0)
        coverage = result["breakdown"]["swath_coverage_pct"]
        self.assertAlmostEqual(coverage, 50, delta=1)
        self.assertEqual(result["breakdown"]["open_water_pct"], 100)
        for telemetry in result["all_vessel_profiles"].values():
            self.assertEqual(telemetry["status"], "UNASSESSED")
            self.assertIsNone(telemetry["actual_transit_hours"])
            self.assertIsNone(telemetry["total_fuel_tons"])

    def test_no_observations_withhold_trip_estimates(self):
        result = self.evaluate(-98.0, -97.0)
        self.assertEqual(result["breakdown"]["swath_coverage_pct"], 0)
        self.assertEqual(result["breakdown"]["open_water_count"], 0)
        self.assertIsNone(result["telemetry"]["transit_delay_hours"])
        self.assertIsNone(result["telemetry"]["excess_fuel_penalty_tons"])

    def test_invalid_pixels_inside_the_scene_reduce_coverage(self):
        self.hazard[:, 4:6] = 0
        result = self.evaluate(-94.8, -94.2)
        self.assertAlmostEqual(result["breakdown"]["swath_coverage_pct"], 67, delta=1)
        self.assertIsNone(result["telemetry"]["actual_transit_hours"])

    def test_full_coverage_keeps_trip_estimates(self):
        result = self.evaluate(-94.8, -94.2)
        self.assertEqual(result["breakdown"]["swath_coverage_pct"], 100)
        self.assertEqual(result["telemetry"]["status"], "NAVIGABLE")
        self.assertGreater(result["telemetry"]["actual_transit_hours"], 0)
        self.assertGreater(result["telemetry"]["total_fuel_tons"], 0)
