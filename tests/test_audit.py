"""Independent checks for the six registered playground models."""
import hashlib
import json
import subprocess
import sys
import unittest

import numpy as np

from lab import engine
from lab.runtime import HOOK, Cancelled, RunHook


def _sha(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PlaygroundAudit(unittest.TestCase):
    def test_lab_manifest_hashes_match_files(self):
        manifest = json.loads((engine.ROOT / "assets" / "metadata" / "model_manifest.json").read_text())
        self.assertIn("region_agreement", manifest["records"]["whu-hi-longkou"])
        self.assertLess(manifest["records"]["whu-hi-longkou"]["region_agreement"], 1)
        for relative, meta in manifest["files"].items():
            path = engine.ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(_sha(path), meta["sha256"])
            self.assertEqual(path.stat().st_size, meta["bytes"])

    def test_high_band_16_grid_is_rejected(self):
        with self.assertRaises(ValueError):
            engine.run("whu-hi-longkou", "longkou-0000", 16, "mean", "permutation", 1, 0)

    def test_hyperspectral_labels_are_channel_indices(self):
        catalog = {model["id"]: model for model in engine.catalog()["models"]}
        for model_id in ("paviau", "salinas", "whu-hi-longkou"):
            names = catalog[model_id]["channels"]
            self.assertEqual(names[0], "Band 001")
            self.assertEqual(names[-1], f"Band {len(names):03d}")
            self.assertFalse(any("nm" in name for name in names))
            self.assertIn("no wavelength", catalog[model_id]["band_note"])
        self.assertEqual(catalog["hls-unet"]["channels"][0], "Blue")
        self.assertIn("B01", catalog["eurosat"]["channels"][0])

    def test_direct_mask_matches_spatial_sum(self):
        cases = (
            ("hls-unet", "hls-burn-scar", 6),
            ("cub-200", "cub-0158", 3),
            ("paviau", "paviau-0008", 103),
        )
        for model_id, sample_id, channels in cases:
            result = engine.run(model_id, sample_id, 4, "mean", "permutation", 1, 0)
            masks = np.ones((1, 16, channels), dtype=bool)
            masks[0, 0, :] = False
            held = engine.score_masks(model_id, sample_id, 4, "mean", masks)
            full = engine.score_masks(model_id, sample_id, 4, "mean", np.ones_like(masks))
            np.testing.assert_allclose(full[0], result["full_value"], atol=1e-5, rtol=0)
            np.testing.assert_allclose(full[0] - held[0], result["spatial"][0][0], atol=1e-5, rtol=0)
            self.assertLess(result["local_efficiency_error"], 1e-5)

    def test_zero_baseline_stays_efficient(self):
        for model_id, sample_id in (
            ("hls-unet", "hls-burn-scar"),
            ("cub-200", "cub-0158"),
            ("salinas", "salinas-0000"),
        ):
            result = engine.run(model_id, sample_id, 4, "zero", "permutation", 1, 0)
            self.assertTrue(np.isfinite(result["spectral"]).all())
            self.assertLess(result["local_efficiency_error"], 1e-5)
            self.assertEqual(result["baseline"], "zero")

    def test_cub_exact_and_permutation_share_the_full_score(self):
        exact = engine.run("cub-200", "cub-0158", 4, "mean", "exact", 1, 0)
        sampled = engine.run("cub-200", "cub-0158", 4, "mean", "permutation", 20, 0)
        self.assertEqual(exact["method"], "exact")
        self.assertEqual(sampled["method"], "permutation")
        self.assertAlmostEqual(exact["full_value"], sampled["full_value"], places=5)
        self.assertLess(exact["local_efficiency_error"], 1e-5)
        self.assertGreater(np.corrcoef(exact["spectral"], sampled["spectral"])[0, 1], 0.8)

    def test_cancel_hook_stops_before_scoring(self):
        hook = RunHook()
        hook.cancel.set()
        token = HOOK.set(hook)
        try:
            with self.assertRaises(Cancelled):
                engine.run("eurosat", "eurosat-1294", 4, "mean", "permutation", 1, 1)
        finally:
            HOOK.reset(token)

    def test_cli_matches_api_and_rejects_a_bad_checkpoint(self):
        completed = subprocess.run(
            [sys.executable, "-m", "lab.cli", "explain",
             "--model-id", "cub-200", "--sample-id", "cub-0158",
             "--grid", "4", "--permutations", "1", "--seed", "0"],
            cwd=engine.ROOT, check=True, capture_output=True, text=True,
        )
        payload = json.loads(completed.stdout)
        reference = engine.run("cub-200", "cub-0158", 4, "mean", "permutation", 1, 0)
        np.testing.assert_allclose(payload["spectral"], reference["spectral"], atol=1e-6, rtol=0)
        self.assertIn("python -m lab.cli explain", payload["command"])
        rejected = subprocess.run(
            [sys.executable, "-m", "lab.cli", "explain-files",
             "--family", "cub-200",
             "--checkpoint", "assets/checkpoints/paviau_unet.pt",
             "--sample", "assets/samples/cub_0158.npz",
             "--grid", "4", "--permutations", "1"],
            cwd=engine.ROOT, capture_output=True, text=True,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("does not match", rejected.stderr + rejected.stdout)


if __name__ == "__main__":
    unittest.main()
