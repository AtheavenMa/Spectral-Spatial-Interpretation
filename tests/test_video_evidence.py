"""Regression checks for the authentic sample_0163 promotional SSI evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/video/hls_burnscar_0163"
ORIGINAL = ROOT / "docs/playground/assets/samples/HLS_BurnScars/sample_0163"


class HLSVideoEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((DATA / "result.json").read_text())
        cls.analysis = json.loads((DATA / "analysis.json").read_text())
        cls.provenance = json.loads((DATA / "manifest.json").read_text())
        cls.meta = json.loads((ORIGINAL / "meta.json").read_text())
        cls.grid = np.asarray(cls.result["attribution"], dtype=np.float64)
        cls.spatial = np.asarray(cls.result["spatial"], dtype=np.float64)
        cls.spectral = np.asarray(cls.result["spectral"], dtype=np.float64)

    def test_parameters_target_and_provenance(self):
        self.assertEqual(self.result["sample_id"], "HLS_BurnScars/sample_0163")
        self.assertEqual(self.provenance["sample_id"], self.result["sample_id"])
        for key, expected in (
            ("grid", 16), ("baseline", "mean"), ("permutations", 5),
            ("seed", 0), ("method", "permutation"),
        ):
            self.assertEqual(self.result[key], expected)
        self.assertEqual(self.analysis["parameters"],
                         {"grid": 16, "baseline": "mean",
                          "permutations": 5, "seed": 0})
        self.assertEqual(self.meta["target_class"], 1)
        self.assertEqual(self.meta["region_pixels"], 2734)
        self.assertEqual(len(self.meta["original_checkpoint_sha256"]), 64)
        self.assertEqual(
            self.provenance["files"]["result.json"]["sha256"],
            hashlib.sha256((DATA / "result.json").read_bytes()).hexdigest(),
        )

    def test_joint_attributions_aggregate_exactly(self):
        self.assertEqual(self.grid.shape, (16, 16, 6))
        self.assertEqual(self.spatial.shape, (16, 16))
        self.assertEqual(self.spectral.shape, (6,))
        np.testing.assert_allclose(self.grid.sum(axis=2), self.spatial, atol=1e-8)
        np.testing.assert_allclose(self.grid.sum(axis=(0, 1)), self.spectral, atol=1e-8)
        self.assertAlmostEqual(float(self.spatial.sum()), 0.8745819359320286, places=5)
        self.assertAlmostEqual(float(self.spectral.sum()), float(self.spatial.sum()), places=10)
        self.assertLess(self.result["local_efficiency_error"], 1e-8)
        # Local contextual attribution is not globally efficient; the video
        # must not equate this sum with the full burn logit.
        self.assertGreater(
            abs(float(self.result["full_value"]) - float(self.spatial.sum())), 0.1
        )

    def test_real_gt_spatial_localization_and_band_order(self):
        label = np.frombuffer((ORIGINAL / "mask.u8").read_bytes(), dtype=np.uint8)
        self.assertEqual(label.size, 128 * 128)
        burn = (label.reshape(128, 128) == 1)
        self.assertEqual(int(burn.sum()), 2734)
        fraction = burn.reshape(16, 8, 16, 8).mean(axis=(1, 3))
        mass = np.clip(self.spatial, 0.0, None)
        measured = float((mass * fraction).sum() / mass.sum())
        self.assertAlmostEqual(measured,
                               self.analysis["positive_spatial_ssi_weighted_fraction_inside_GT"],
                               places=8)
        self.assertGreater(measured, 0.8)
        self.assertAlmostEqual(float(burn.mean()), self.analysis["target_area_fraction"], places=8)
        channels = self.result["channels"]
        self.assertEqual(channels, ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"])
        by_name = dict(zip(channels, self.spectral))
        self.assertGreater(by_name["SWIR2"], by_name["SWIR1"])
        self.assertGreater(by_name["SWIR1"], 0)
        self.assertLess(by_name["Red"], 0)
        self.assertLess(by_name["Green"], 0)
        self.assertLess(by_name["NIR"], 0)
        self.assertLess(by_name["Blue"], 0)
        np.testing.assert_allclose(
            [item["spectral_total"] for item in self.analysis["spectral_ranking_by_absolute_total"]],
            [by_name[item["name"]] for item in self.analysis["spectral_ranking_by_absolute_total"]],
            atol=1e-9,
        )

    def test_all_shipped_pngs_and_hashes_are_real(self):
        required = ["input.png", "ground_truth.png", "spatial_ssi.png",
                    "spectral_contributions.png", "ssi_explanation_overview.png",
                    "playground_screenshot.png"]
        required.extend(
            f"channel_{i:02d}_{band}.png"
            for i, band in enumerate(("blue", "green", "red", "nir", "swir1", "swir2"), 1)
        )
        for name in required:
            with self.subTest(file=name):
                path = DATA / name
                self.assertTrue(path.is_file())
                with Image.open(path) as im:
                    self.assertEqual(im.format, "PNG")
                    self.assertGreaterEqual(im.width, 300)
                manifest = self.provenance["files"][name]
                self.assertEqual(path.stat().st_size, manifest["size"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                                 manifest["sha256"])


if __name__ == "__main__":
    unittest.main()
