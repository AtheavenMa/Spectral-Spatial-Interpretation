"""Model migration checks against numerical outputs captured from the old model.

The reference fixture contains arrays only. No legacy implementation is imported.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from lab.adapters.hls import HLSValueFunction, load_model, load_sample
from lab.models.hls_unet import UNet, convert_legacy_state_dict
from ssi import explain

ROOT = Path(__file__).resolve().parents[1]


class ModelMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(4)
        cls.weights = ROOT / "assets/checkpoints/hls_unet.pt"
        cls.model = load_model(cls.weights, torch.device("cpu"))
        _, cls.mask, cls.x = load_sample(ROOT / "assets/examples/hls_sample.npz")
        with np.load(ROOT / "tests/fixtures/hls_legacy_reference.npz", allow_pickle=False) as data:
            cls.reference = {key: data[key].copy() for key in data.files}

    def test_pixel_logits_match_legacy_reference(self):
        with torch.inference_mode():
            actual = self.model(torch.from_numpy(self.x)[None]).numpy()
        np.testing.assert_allclose(actual, self.reference["logits"], rtol=1e-5, atol=1e-5)
        np.testing.assert_array_equal(actual.argmax(1), self.reference["logits"].argmax(1))

    def test_odd_dimensions_match_legacy_reference(self):
        with torch.inference_mode():
            actual = self.model(torch.from_numpy(self.reference["odd_input"])).numpy()
        np.testing.assert_allclose(actual, self.reference["odd_logits"], rtol=1e-5, atol=1e-5)

    def test_default_attribution_matches_legacy_reference(self):
        vf = HLSValueFunction(self.model, self.x, self.mask)
        result = explain(vf, 64, 6, n_permutations=10, seed=0)
        np.testing.assert_allclose(result.attribution, self.reference["mean_permutation"],
                                   rtol=1e-5, atol=1e-5)
        np.testing.assert_allclose(result.position_contrasts, self.reference["position_contrasts"],
                                   rtol=1e-5, atol=1e-5)

    def test_legacy_prefix_and_native_weights_load(self):
        state = torch.load(self.weights, weights_only=True)
        before = {k: v.clone() for k, v in state.items()}
        prefixed = {"model." + k: v for k, v in state.items()}
        converted = convert_legacy_state_dict(prefixed)
        model = UNet()
        model.load_state_dict(converted, strict=True)
        self.assertEqual(len(converted), 62)
        for key, tensor in state.items():
            self.assertTrue(torch.equal(tensor, before[key]))
        for key, tensor in self.model.state_dict().items():
            self.assertTrue(torch.equal(tensor, model.state_dict()[key]))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "native.pt"
            torch.save(model.state_dict(), path)
            restored = load_model(path, torch.device("cpu"))
            for key, tensor in model.state_dict().items():
                self.assertTrue(torch.equal(tensor, restored.state_dict()[key]))

    def test_incompatible_checkpoints_fail(self):
        state = torch.load(self.weights, weights_only=True)
        with self.assertRaises(ValueError):
            convert_legacy_state_dict({**state, "unknown.weight": torch.zeros(1)})
        with self.assertRaises(ValueError):
            convert_legacy_state_dict({**state, "model.outc.bias": state["outc.bias"]})
        for bad in ({k: v for k, v in state.items() if k != "outc.bias"},
                    {**state, "outc.weight": torch.zeros(3, 4, 1, 1)}):
            with self.assertRaises(RuntimeError):
                UNet().load_state_dict(convert_legacy_state_dict(bad), strict=True)


if __name__ == "__main__":
    unittest.main()
