"""Data and provenance contracts for the 57-image static SSI Playground."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.export_playground_assets import (
    MANIFEST, ROOT, manifest_read, sample_export, validate_manifest,
)


class PlaygroundManifestTests(unittest.TestCase):
    def test_every_atlas_figure_has_an_exact_compute_slot(self):
        manifest = manifest_read()
        atlas = json.loads((ROOT / "docs/playground/atlas-catalog.json").read_text())
        expected = {
            group["id"] + "/" + name.removesuffix(".png")
            for group in atlas["groups"] for name in group["files"]
        }
        records = [s for s in manifest["samples"] if s.get("image_url")]
        self.assertEqual(len(expected), 57)
        self.assertEqual(len(records), 57)
        self.assertEqual({s["id"] for s in records}, expected)
        self.assertEqual(len(manifest["models"]), 6)
        self.assertEqual({m["id"] for m in manifest["models"]},
                         {s["model_id"] for s in records})
        for rec in records:
            img = ROOT / "examples" / (rec["id"] + ".png")
            self.assertTrue(img.is_file(), f"No published Atlas figure for {rec['id']}")
            self.assertIn(rec["status"], ("ready", "awaiting_assets"))
            self.assertIn("metadata", rec["required_assets"])
            self.assertIn("tensor", rec["required_assets"])
            self.assertIn("rgb", rec["required_assets"])
        # The existing HLS compute demo is separate from the numbered Atlas images.
        hls = next(x for x in manifest["samples"] if x["id"] == "hls-bundled")
        self.assertEqual(hls["status"], "ready")
        self.assertFalse(hls["gallery_example"])

    def test_manifest_can_be_validated_without_fake_readiness(self):
        summary = validate_manifest()
        self.assertEqual(summary["gallery_images"], 57)
        self.assertEqual(summary["ready_samples"] + summary["pending"], 58)
        self.assertGreaterEqual(summary["ready_samples"], 1)

    def test_wrong_image_provenance_is_rejected_before_export(self):
        # The source file can have the right dimensions and still belong to
        # the wrong sample ID. Reject before creating any assets/ready entries.
        source = ROOT / "assets/lab/samples/paviau_0008.npz"
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "sample_0010.npz"
            candidate.write_bytes(source.read_bytes())
            candidate.with_suffix(".json").write_text(
                json.dumps({"atlas_id": "PaviaU/sample_0008", "index": 10})
            )
            with self.assertRaisesRegex(ValueError, "atlas_id disagrees"):
                sample_export("PaviaU/sample_0010", candidate)
        before = json.loads(MANIFEST.read_text())
        record = next(x for x in before["samples"] if x["id"] == "PaviaU/sample_0010")
        self.assertEqual(record["status"], "awaiting_assets")

    def test_original_pavia_npz_exports_real_browser_input_without_fake_readiness(self):
        import tools.export_playground_assets as exporter
        from unittest.mock import patch

        original = ROOT / "assets/lab/samples/paviau_0008.npz"
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            manifest_path = workspace / "compute-manifest.json"
            manifest_path.write_bytes(MANIFEST.read_bytes())
            # The independent bundled HLS demo must remain a valid registered
            # ready item even in a temporary asset workspace.
            source_assets = ROOT / "docs/playground/assets"
            dest_assets = workspace / "assets"
            dest_assets.mkdir(parents=True, exist_ok=True)
            for name in ("hls_unet.onnx", "hls_input.f32", "hls_mask.u8",
                         "hls_rgb.webp", "hls_meta.json"):
                shutil.copy2(source_assets / name, dest_assets / name)
            with patch.object(exporter, "WEB", workspace), patch.object(
                exporter, "MANIFEST", manifest_path
            ):
                info = exporter.sample_export("PaviaU/sample_0008", original)
                self.assertEqual(info["status"], "awaiting_assets")
                data = json.loads(
                    (workspace / "assets/samples/PaviaU/sample_0008/meta.json").read_text()
                )
                self.assertEqual(data["sample_id"], "PaviaU/sample_0008")
                self.assertEqual(data["model_id"], "paviau")
                self.assertEqual(len(data["channels"]), 103)
                shape = data["width"] * data["height"] * len(data["channels"]) * 4
                self.assertEqual(
                    (workspace / "assets/samples/PaviaU/sample_0008/x.f32").stat().st_size,
                    shape,
                )
                self.assertGreater(data["region_pixels"], 0)
                counts = exporter.validate_manifest()
                self.assertEqual(counts["ready_gallery"], 0)
                self.assertEqual(counts["ready_samples"], 1)

    def test_batch_template_covers_exactly_the_atlas_gallery(self):
        from tools.export_playground_assets import batch_export
        template = json.loads(
            (ROOT / "docs/playground/57_sources.template.json").read_text()
        )
        manifest = manifest_read()
        gallery_ids = {
            x["id"] for x in manifest["samples"] if x.get("image_url")
        }
        self.assertEqual({s["id"] for s in template["samples"]}, gallery_ids)
        self.assertEqual(len(template["samples"]), 57)
        self.assertEqual(len(template["models"]), 6)
        # Empty source entries remain pending; nothing is fabricated/exported.
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping = Path(temp_dir) / "only_missing.json"
            mapping.write_text(json.dumps({
                "models": [{"id": "hls-unet", "export": False}],
                "samples": [{"id": "PaviaU/sample_0010", "source": None}],
            }))
            report = batch_export(mapping)
            self.assertEqual(report["skipped_samples"], ["PaviaU/sample_0010"])
            self.assertEqual(report["errors"], [])

    def test_hls_has_a_recorded_reference_hash(self):
        manifest = manifest_read()
        model = next(m for m in manifest["models"] if m["id"] == "hls-unet")
        sample = next(s for s in manifest["samples"] if s["id"] == "hls-bundled")
        self.assertEqual(len(model["checkpoint_sha256"]), 64)
        self.assertEqual(len(model["onnx_sha256"]), 64)
        self.assertEqual(len(sample["source_sha256"]), 64)
        self.assertEqual(
            model["checkpoint_sha256"],
            json.loads((ROOT / "docs/playground/assets/hls_meta.json").read_text())[
                "original_checkpoint_sha256"
            ],
        )


if __name__ == "__main__":
    unittest.main()
