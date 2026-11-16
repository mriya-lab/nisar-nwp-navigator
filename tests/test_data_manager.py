import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString

from app import data_manager
from app.routing import evaluate_corridor


class ManifestRasterTests(unittest.TestCase):
    def test_rgb_without_hazard_data_withholds_route_estimates(self):
        with TemporaryDirectory() as directory:
            rgb_path = Path(directory) / "scene.tif"
            transform = from_origin(-95.0, 75.5, 0.1, 0.1)
            with rasterio.open(
                rgb_path, "w", driver="GTiff", width=10, height=10,
                count=3, dtype="uint8", crs="EPSG:4326", transform=transform,
            ) as raster:
                raster.write(np.ones((3, 10, 10), dtype=np.uint8))
            scene = data_manager.load_scene_dataset("scene", {
                "is_fallback": False,
                "scenes": {"scene": {"rgb_path": rgb_path}},
            })
            result = evaluate_corridor(
                LineString([(-94.8, 75.0), (-94.2, 75.0)]),
                scene["hazard_source"], scene["transform"], scene["crs"],
            )
            self.assertEqual(result["breakdown"]["swath_coverage_pct"], 0)
            self.assertEqual(result["telemetry"]["status"], "UNASSESSED")
            self.assertEqual(scene["ice_condition"], "No classified ice data")

    def test_manifest_recognizes_previously_generated_scenes(self):
        with TemporaryDirectory() as directory:
            rgb_path = Path(directory) / "placeholder.tif"
            rgb_path.touch()
            generated = [
                f"NISAR_L2_GCOV_{meta['date_str'].replace('-', '')}_BARROW_STRAIT"
                for meta in data_manager.STAGE_METADATA.values()
            ]
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps({
                scene_id: {"rgb_path": str(rgb_path)}
                for scene_id in [*generated, "historical_scene"]
            }), encoding="utf-8")
            with patch.object(data_manager, "MANIFEST_PATH", manifest):
                scenes = data_manager.inspect_manifest()["scenes"]
            self.assertTrue(all(scenes[scene_id]["is_synthetic"] for scene_id in generated))
            self.assertFalse(scenes["historical_scene"]["is_synthetic"])
