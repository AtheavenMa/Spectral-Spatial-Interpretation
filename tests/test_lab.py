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
        js = self.client.get("/static/app.js")
        self.assertEqual(js.status_code, 200)
        self.assertIn("/api/explain", js.text)

    def test_real_checkpoint_previews(self):
        response = self.client.get("/api/preview")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["width"], 128)
        self.assertEqual(result["height"], 128)
        for name in ("input", "ground_truth", "prediction"):
            prefix, data = result[name].split(",", 1)
            self.assertEqual(prefix, "data:image/png;base64")
            im = Image.open(BytesIO(base64.b64decode(data)))
            self.assertEqual(im.size, (128, 128))

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

    def test_bad_parameters_and_unknown_models(self):
        bad = self.client.post("/api/explain", json={"grid": 3})
        self.assertEqual(bad.status_code, 422)
        exact = self.client.post("/api/explain", json={"grid": 16, "method": "exact"})
        self.assertEqual(exact.status_code, 400)
        unknown = self.client.post("/api/explain", json={"model_id": "../../unsafe"})
        self.assertEqual(unknown.status_code, 400)
        guard = self.client.post("/api/explain", json={"grid": 16, "permutations": 20})
        self.assertEqual(guard.status_code, 400)


if __name__ == "__main__":
    unittest.main()
