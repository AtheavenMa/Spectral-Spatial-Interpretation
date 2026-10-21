"""Public image interface: numerical checks, spatial geometry, bad inputs and packaging."""
import unittest
import numpy as np
import torch
from ssi import SSI


class WeightedClassifier(torch.nn.Module):
    def forward(self, x):
        value = (x * torch.tensor([2., -3.], device=x.device)[None, :, None, None]).sum((1, 2, 3))
        return torch.stack([value, -value], dim=1)


class PixelSegmenter(torch.nn.Module):
    def forward(self, x):
        value = x[:, 0] + 2 * x[:, 1]
        return torch.stack([torch.zeros_like(value), value], dim=1)


class ImageSSITests(unittest.TestCase):
    def test_dataset_vector_baseline_exact_contributions(self):
        model = WeightedClassifier()
        image = np.stack([np.full((4, 6), .8), np.full((4, 6), .3)]).astype("float32")
        result = SSI(model, image, target=0, baseline=[.2, .1],
                     image_size=(8, 12), grid_size=(2, 3)).explain()
        self.assertEqual(result.attribution.shape, (4, 4, 2))
        self.assertEqual(result.image_size, (8, 12))
        self.assertEqual(result.grid_size, (2, 3))
        np.testing.assert_allclose(result.attribution[:, :, 0], 6 * 2 * (.8 - .2), atol=1e-5)
        np.testing.assert_allclose(result.attribution[:, :, 1], 6 * (-3) * (.3 - .1), atol=1e-5)
        np.testing.assert_allclose(result.spectral, result.attribution.sum((0, 1)))
        np.testing.assert_allclose(result.spatial, result.position_contrasts, atol=1e-5)
        self.assertLess(result.max_local_efficiency_error, 1e-5)

    def test_nonsquare_image_and_hwc_uint8(self):
        img = np.full((4, 6, 2), 128, dtype=np.uint8)
        value = SSI(WeightedClassifier(), img, target=0,
                    baseline=[0., 0.], grid_size=(2, 3)).explain()
        self.assertEqual(value.attribution.shape, (2, 2, 2))
        np.testing.assert_allclose(value.spectral[0], 4 * 6 * 2 * (128 / 255), atol=1e-5)

    def test_fixed_segmentation_roi(self):
        img = torch.ones(2, 4, 4)
        roi = torch.zeros(4, 4)
        roi[0:2, 0:2] = 1
        result = SSI(PixelSegmenter(), img, baseline=[0., 0.],
                     target=1, target_mask=roi, grid_size=2).explain()
        self.assertEqual(result.attribution.shape, (2, 2, 2))
        np.testing.assert_allclose(result.attribution[0, 0], [1, 2], atol=1e-5)
        np.testing.assert_allclose(result.attribution[0, 1], 0, atol=1e-6)
        np.testing.assert_allclose(result.attribution[1], 0, atol=1e-6)
        self.assertLess(result.max_local_efficiency_error, 1e-5)

    def test_callable_target_and_train_state_restored(self):
        model = WeightedClassifier().train()
        result = SSI(model, torch.ones(2, 2, 2), baseline=[0., 0.],
                     target=lambda logits: logits[:, 0] - logits[:, 1],
                     grid_size=2).explain()
        self.assertTrue(model.training)
        np.testing.assert_allclose(result.attribution[0, 0], [16, -24], atol=1e-5)

    def test_rejects_unreliable_geometry_and_baselines(self):
        image = torch.ones(2, 4, 6)
        model = WeightedClassifier()
        invalid = (
            dict(baseline="mean"),
            dict(baseline=[0.]),
            dict(baseline=[0., float("nan")]),
            dict(baseline=[0., 0.], image_size=(7, 12), grid_size=(2, 3)),
            dict(baseline=[0., 0.], grid_size=0),
            dict(baseline=[0., 0.], target_mask=np.zeros((4, 6))),
        )
        for kw in invalid:
            with self.subTest(kw=kw), self.assertRaises((ValueError, TypeError)):
                SSI(model, image, target=0, **kw)
        with self.assertRaises(ValueError):
            SSI(PixelSegmenter(), image, target=1, baseline=[0., 0.],
                grid_size=2).explain()


if __name__ == "__main__":
    unittest.main()
