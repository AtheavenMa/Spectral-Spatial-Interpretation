"""Repository-level contracts that guard packaging and asset refactors."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTests(unittest.TestCase):
    def test_shared_renderers_are_identical(self):
        source = ROOT / "docs/playground/atlas-render.js"
        api_copy = ROOT / "lab/static/atlas-render.js"
        self.assertEqual(source.read_bytes(), api_copy.read_bytes())

    def test_core_and_model_assets_are_resolved(self):
        from lab.adapters.hls import load_sample
        from lab.models.hls_unet import UNet
        self.assertTrue(callable(load_sample))
        self.assertTrue(callable(UNet))
        manifest = json.loads((ROOT / "assets/metadata/model_manifest.json").read_text())
        for path in manifest["files"]:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_published_browser_catalog_is_complete(self):
        manifest = json.loads((ROOT / "docs/playground/compute-manifest.json").read_text())
        self.assertEqual(len(manifest["models"]), 6)
        self.assertEqual(manifest["gallery_count"], 57)
        self.assertEqual(len(manifest["samples"]), 58)
        self.assertTrue(all(s["status"] == "ready" for s in manifest["samples"]))


if __name__ == "__main__":
    unittest.main()
