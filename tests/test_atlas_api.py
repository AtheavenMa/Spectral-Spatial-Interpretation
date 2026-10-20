"""Real checkpoint/input -> full SSI Atlas figure + JSON/NPZ verification."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from lab.atlas_api import explain_artifacts, prepare
from lab.engine import ROOT, CHECKPOINT, SAMPLE


class AtlasArtifactsTest(unittest.TestCase):
    def check_artifacts(self, result, channels: int, grid: int):
        png, js, npz = [Path(result[name]) for name in ("png", "json", "npz")]
        self.assertTrue(png.is_file() and png.stat().st_size > 15000)
        self.assertTrue(js.is_file() and js.stat().st_size > 500)
        self.assertTrue(npz.is_file() and npz.stat().st_size > 100)
        with Image.open(png) as image:
            self.assertEqual(image.format, "PNG")
            self.assertGreaterEqual(image.width, 2400)
            self.assertGreaterEqual(image.height, 1000)
        payload = json.loads(js.read_text())
        a = np.asarray(payload["attribution"])
        self.assertEqual(a.shape, (grid, grid, channels))
        np.testing.assert_allclose(a.sum(axis=2), payload["spatial"], atol=1e-5)
        np.testing.assert_allclose(a.sum(axis=(0, 1)), payload["spectral"], atol=1e-5)
        self.assertLess(payload["local_efficiency_error"], 1e-4)
        self.assertEqual(len(payload["checkpoint_sha256"]), 64)
        with np.load(npz, allow_pickle=False) as arrays:
            np.testing.assert_allclose(arrays["attribution"], a, atol=1e-12)
            self.assertEqual(arrays["spatial"].shape, (grid, grid))
        return payload

    def test_hls_original_checkpoint_and_image(self):
        with tempfile.TemporaryDirectory() as d:
            out = explain_artifacts(
                CHECKPOINT, SAMPLE,
                family="hls-unet", output=Path(d) / "hls",
                grid=4, permutations=1, seed=0,
            )
            result = self.check_artifacts(out, 6, 4)
            self.assertEqual(result["target_class"], 1)
            self.assertGreater(result["fixed_region_pixels"], 0)

    def test_high_band_real_checkpoint(self):
        ckpt = ROOT / "assets/lab/checkpoints/paviau_unet.pt"
        image = ROOT / "assets/lab/samples/paviau_0008.npz"
        with tempfile.TemporaryDirectory() as d:
            out = explain_artifacts(
                ckpt, image, family="paviau", output=Path(d) / "paviau",
                grid=4, permutations=1, display_channels=8, seed=0,
            )
            result = self.check_artifacts(out, 103, 4)
            self.assertEqual(len(result["visualized_channel_indices"]), 8)
            self.assertTrue(all(x.startswith("Band ") for x in result["channels"]))
            self.assertGreater(result["fixed_region_pixels"], 0)

    def test_rgb_image_and_explicit_class(self):
        ckpt = ROOT / "assets/lab/checkpoints/cub_resnet18.pt"
        bundled = ROOT / "assets/lab/samples/cub_0158.npz"
        with np.load(bundled, allow_pickle=False) as archive:
            rgb = np.asarray(archive["rgb"], dtype=np.uint8)
            target = int(archive["target_class"])
        with tempfile.TemporaryDirectory() as d:
            rgb_path = Path(d) / "bird.png"
            Image.fromarray(rgb, "RGB").save(rgb_path)
            out = explain_artifacts(
                ckpt, rgb_path, family="cub-200", output=Path(d) / "cub",
                grid=4, permutations=1, target_class=target,
            )
            result = self.check_artifacts(out, 3, 4)
            self.assertIsNone(result["fixed_region_pixels"])

    def test_bad_family_input_and_missing_target(self):
        from PIL import Image as PILImage
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "photo.png"
            PILImage.new("RGB", (448, 448)).save(p)
            cub = ROOT / "assets/lab/checkpoints/cub_resnet18.pt"
            with self.assertRaisesRegex(ValueError, "requires --target-class"):
                prepare("cub-200", cub, p)
            pavia = ROOT / "assets/lab/checkpoints/paviau_unet.pt"
            with self.assertRaisesRegex(ValueError, "requires an NPZ"):
                prepare("paviau", pavia, p, target_class=8)


if __name__ == "__main__":
    unittest.main()
