"""Small games with known answers; run with python -m unittest discover -s tests."""
import unittest

import numpy as np

from ssi import explain


class SSITests(unittest.TestCase):
    def test_additive_game_and_auto_exact(self):
        weights = np.array([[1., -2., 3.], [4., .5, -1.]])
        result = explain(lambda s: (s * weights).sum(axis=(1, 2)) + 17, 2, 3)
        np.testing.assert_allclose(result.attribution, weights, atol=1e-12)
        self.assertEqual(result.method, "exact")
        self.assertEqual(result.n_evaluations, 1 + 2 * 7)
        self.assertLess(result.max_local_efficiency_error, 1e-12)

    def test_interaction_allocation_with_observed_context(self):
        def game(s):
            # The local 6-point synergy is split equally. The cross-cell
            # interaction contributes 8 at either position in full context.
            return 2*s[:,0,0] + 4*s[:,0,1] + 6*(s[:,0,0]&s[:,0,1]) + 8*(s[:,0,0]&s[:,1,0])
        r = explain(game, 2, 2, method="exact")
        np.testing.assert_allclose(r.attribution, [[13, 7], [8, 0]])
        np.testing.assert_allclose(r.position_contrasts, [20, 8])

    def test_local_does_not_imply_global_efficiency(self):
        r = explain(lambda s: (s[:,0,0] & s[:,1,0]).astype(float), 2, 1)
        np.testing.assert_array_equal(r.attribution, [[1], [1]])
        self.assertEqual(r.full_value, 1)
        self.assertEqual(r.spatial.sum(), 2)

    def test_permutation_telescope_and_seed(self):
        def game(s):
            return np.sum(s * np.arange(8).reshape(2,4), axis=(1,2)) + 7*np.prod(s[:,0,:],axis=1)
        a = explain(game, 2, 4, n_permutations=13, seed=23)
        b = explain(game, 2, 4, n_permutations=13, seed=23)
        np.testing.assert_array_equal(a.attribution, b.attribution)
        self.assertLess(a.max_local_efficiency_error, 1e-12)
        exact = explain(game, 2, 4, method="exact")
        sampled = explain(game, 2, 4, n_permutations=5000, seed=23)
        np.testing.assert_allclose(sampled.attribution, exact.attribution, atol=.12)

    def test_constant_shift_invariance(self):
        def game(s): return (s[:,0,0] | s[:,0,1]).astype(float)
        a = explain(game, 1, 2)
        b = explain(lambda s: game(s) + 100, 1, 2)
        np.testing.assert_allclose(a.attribution, b.attribution)
        np.testing.assert_allclose(a.attribution, [[.5, .5]])

    def test_only_target_cell_changes_and_count_is_real(self):
        batches = []
        def game(s):
            batches.append(s.copy())
            self.assertTrue(np.all((~s.all(axis=2)).sum(axis=1) <= 1))
            return s.sum(axis=(1,2)).astype(float)
        result = explain(game, 4, 6, n_permutations=10)
        self.assertEqual(result.n_evaluations, sum(len(b) for b in batches))
        np.testing.assert_allclose(result.attribution, 1)

    def test_invalid_input_and_invalid_oracle(self):
        for kwargs in ({"n_cells":0}, {"n_channels":-1}, {"n_permutations":0}, {"n_cells":True}):
            params=dict(n_cells=2,n_channels=2); params.update(kwargs)
            with self.assertRaises(ValueError): explain(lambda s: s.sum((1,2)), **params)
        with self.assertRaises(ValueError): explain(lambda s: np.nan*np.ones(len(s)), 2, 2)
        with self.assertRaises(ValueError): explain(lambda s: np.ones((len(s),1)), 2, 2)
        with self.assertRaises(ValueError): explain(lambda s: s.sum((1,2)), 2, 20, method="exact")


if __name__ == "__main__":
    unittest.main()
