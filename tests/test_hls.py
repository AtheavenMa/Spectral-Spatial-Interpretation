"""Check the image-to-coalition adapter independently of the attribution solver."""
import unittest

import numpy as np
import torch

from lab.adapters.hls import HLSValueFunction, HLS_MEAN, HLS_STD
from ssi import explain


class PixelModel(torch.nn.Module):
    def forward(self, x):
        burn = x[:, 0] + 2*x[:, 1] + x[:, 0]*x[:, 2]
        return torch.stack([torch.zeros_like(burn), burn], dim=1)


class HLSAdapterTests(unittest.TestCase):
    def setUp(self):
        self.x = np.arange(6*4*4, dtype=np.float32).reshape(6,4,4)/100
        self.gt = np.zeros((4,4), dtype=np.uint8)
        self.gt[0,0] = 1; self.gt[3,2] = 1; self.gt[1,1] = 255

    def test_batched_coalitions_match_explicit_pixel_masks(self):
        vf = HLSValueFunction(PixelModel(), self.x, self.gt, grid=2, baseline="zero", batch_size=3)
        masks = np.random.default_rng(4).random((9,4,6)) > .5
        actual = vf(masks)
        expected = []
        baseline = -HLS_MEAN/HLS_STD
        for coalition in masks:
            perturbed = np.broadcast_to(baseline[:,None,None],self.x.shape).copy()
            for g in range(4):
                r,c = divmod(g,2)
                for ch in range(6):
                    if coalition[g,ch]:
                        perturbed[ch,2*r:2*r+2,2*c:2*c+2] = self.x[ch,2*r:2*r+2,2*c:2*c+2]
            logits = PixelModel()(torch.from_numpy(perturbed)[None])[0,1].numpy()
            expected.append(logits[self.gt == 1].mean())
        np.testing.assert_allclose(actual,expected,rtol=2e-6,atol=1e-6)
        self.assertEqual(vf.forward_calls,3)

    def test_zero_is_raw_zero_after_normalization(self):
        vf = HLSValueFunction(PixelModel(), self.x, self.gt, grid=2, baseline="zero")
        raw = vf.baseline.numpy().reshape(6)*HLS_STD + HLS_MEAN
        np.testing.assert_allclose(raw,0,atol=3e-4)

    def test_fixed_region_and_local_efficiency(self):
        vf = HLSValueFunction(PixelModel(), self.x, self.gt, grid=2)
        r = explain(vf,4,6,method="exact")
        self.assertLess(r.max_local_efficiency_error,1e-12)
        # Neither of these cells contains the fixed target region, and this
        # model is pointwise. They must remain null despite nonzero input.
        np.testing.assert_allclose(r.attribution[[1,2]],0,atol=1e-12)

    def test_empty_region_and_incompatible_grid_rejected(self):
        with self.assertRaises(ValueError):
            HLSValueFunction(PixelModel(),self.x,np.zeros_like(self.gt),grid=2)
        with self.assertRaises(ValueError):
            HLSValueFunction(PixelModel(),self.x,self.gt,grid=3)


if __name__ == "__main__":
    unittest.main()
