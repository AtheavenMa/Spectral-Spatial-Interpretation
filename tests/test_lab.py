"""CPU integration tests for the live SSI Playground and bundled HLS checkpoint."""
import base64
from io import BytesIO
import unittest

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from lab.app import app
from lab import engine


class SSILabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_catalog_and_health(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["model_ready"])
        self.assertTrue(health.json()["sample_ready"])
        response = self.client.get("/api/catalog")
        self.assertEqual(response.status_code, 200)
        model = response.json()["models"][0]
        self.assertEqual(model["id"], engine.MODEL_ID)
        self.assertEqual(model["channels"], list(engine.BAND_NAMES))
        self.assertEqual(model["grids"], [4, 8, 16])

    def test_static_frontend(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("SSI Playground", page.text)
        self.assertIn('id="run"', page.text)
        self.assertIn('id="spectralGrid"', page.text)
        self.assertIn('id="overlayOpacity"', page.text)
        self.assertNotIn('id="predImage"', page.text)
        self.assertEqual(page.text.count("class=\"visual-panel\""), 3)
        atlas = self.client.get("/static/atlas-render.js")
        self.assertEqual(atlas.status_code, 200)
        self.assertIn("sampleSmooth", atlas.text)
        self.assertIn("overlayPixels", atlas.text)
        js = self.client.get("/static/app.js")
        self.assertEqual(js.status_code, 200)
        self.assertIn("/api/jobs", js.text)

    def test_real_checkpoint_previews(self):
        response = self.client.get("/api/preview")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["width"], 128)
        self.assertEqual(result["height"], 128)
        for name in ("input", "ground_truth", "prediction", "target_mask"):
            prefix, data = result[name].split(",", 1)
            self.assertEqual(prefix, "data:image/png;base64")
            im = Image.open(BytesIO(base64.b64decode(data)))
            self.assertEqual(im.size, (128, 128))
            if name == "target_mask":
                values = np.asarray(im.convert("L"))
                self.assertTrue(np.any(values > 128))
                self.assertTrue(np.any(values < 128))

    def test_cpu_attribution_matches_core(self):
        settings = dict(
            model_id=engine.MODEL_ID, sample_id=engine.SAMPLE_ID,
            grid=4, baseline="mean", method="permutation",
            permutations=2, seed=0,
        )
        response = self.client.post("/api/explain", json=settings)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        values = np.asarray(data["attribution"])
        self.assertEqual(values.shape, (4, 4, 6))
        self.assertTrue(np.isfinite(values).all())
        np.testing.assert_allclose(
            values.sum(axis=2), np.asarray(data["spatial"]),
            atol=1e-6, rtol=0,
        )
        np.testing.assert_allclose(
            values.sum(axis=(0, 1)), np.asarray(data["spectral"]),
            atol=1e-6, rtol=0,
        )
        self.assertLess(data["local_efficiency_error"], 1e-5)
        self.assertGreater(data["n_evaluations"], 0)
        self.assertIn("--grid 4", data["command"])
        self.assertEqual(engine.run(**settings)["attribution"], data["attribution"])

    def test_default_hls_matches_recorded_reference(self):
        import json
        reference = json.loads((engine.ROOT / "assets" / "demo_summary.json").read_text())
        result = engine.run(
            model_id=engine.MODEL_ID, sample_id=engine.SAMPLE_ID,
            grid=8, baseline="mean", method="permutation",
            permutations=10, seed=0,
        )
        expected = [reference["spectral_attribution"][band] for band in engine.BAND_NAMES]
        np.testing.assert_allclose(result["spectral"], expected, atol=2e-3, rtol=0)
        self.assertEqual(result["n_evaluations"], reference["n_evaluations"])
        self.assertLess(result["local_efficiency_error"], 1e-5)

    def test_bad_parameters_and_unknown_models(self):
        bad = self.client.post("/api/explain", json={"grid": 3})
        self.assertEqual(bad.status_code, 422)
        exact = self.client.post("/api/explain", json={"grid": 16, "method": "exact"})
        self.assertEqual(exact.status_code, 400)
        unknown = self.client.post("/api/explain", json={"model_id": "../../unsafe"})
        self.assertEqual(unknown.status_code, 400)
        guard = self.client.post("/api/explain", json={"grid": 16, "permutations": 20})
        self.assertEqual(guard.status_code, 400)
        wide = self.client.post("/api/explain", json={
            "model_id": "eurosat", "sample_id": "eurosat-1294",
            "grid": 4, "method": "exact", "permutations": 1,
        })
        self.assertEqual(wide.status_code, 400)

    def test_extra_models_match_recorded_reference(self):
        import json
        reference = json.loads((engine.ROOT / "assets" / "lab" / "references.json").read_text())
        models = self.client.get("/api/catalog").json()["models"]
        self.assertEqual(
            [model["id"] for model in models],
            ["hls-unet", "cub-200", "eurosat", "paviau", "salinas", "whu-hi-longkou"],
        )
        for model in models[1:]:
            settings = dict(
                model_id=model["id"], sample_id=model["samples"][0]["id"],
                grid=4, baseline="mean", method="permutation",
                permutations=1, seed=0,
            )
            result = engine.run(**settings)
            values = np.asarray(result["attribution"])
            self.assertEqual(values.shape, (4, 4, len(model["channels"])))
            self.assertTrue(np.isfinite(values).all())
            np.testing.assert_allclose(values.sum(axis=(0, 1)), result["spectral"], atol=1e-6, rtol=0)
            self.assertLess(result["local_efficiency_error"], 1e-5)
            self.assertEqual(result["n_evaluations"], reference[model["id"]]["n_evaluations"])
            # The stored vectors were produced with a newer CPU/CUDA wheel.
            # GitHub Actions uses torch 2.6 CPU, which drifts by about 1e-5.
            np.testing.assert_allclose(result["spectral"], reference[model["id"]]["spectral"], atol=1e-4, rtol=0)
            self.assertEqual(engine.run(**settings)["spectral"], result["spectral"])
            preview = self.client.get("/api/preview", params={
                "model_id": model["id"], "sample_id": model["samples"][0]["id"],
            })
            self.assertEqual(preview.status_code, 200, preview.text)
            image = Image.open(BytesIO(base64.b64decode(preview.json()["input"].split(",", 1)[1])))
            self.assertEqual(image.size[0], image.size[1])
            if model["id"] in ("paviau", "salinas", "whu-hi-longkou"):
                target = preview.json()["target_mask"]
                self.assertTrue(target.startswith("data:image/png;base64,"))
                mask = np.asarray(Image.open(BytesIO(base64.b64decode(target.split(",", 1)[1]))).convert("L"))
                self.assertTrue(np.any(mask == 255))
                self.assertTrue(np.any(mask == 0))
            else:
                self.assertIsNone(preview.json()["target_mask"])


if __name__ == "__main__":
    unittest.main()
