# Model adapter contract

The runnable v1 adapter is the bundled HLS path in [lab/engine.py](../engine.py). The additional datasets listed in [pending_models.json](pending_models.json) are asset-intake slots, not synthetic demos.

A new adapter must provide:

1. A stable **model ID**, **input/sample ID**, safe, allowlisted checkpoint and sample paths, model architecture, checkpoint hash and source.
2. A loader that reconstructs the checkpoint in inference mode, with an explicit tensor shape and channel order.
3. Fixed preprocessing/normalization and physically meaningful channel names/wavelengths.
4. A scalar scoring function accepting Boolean masks of shape (batch, grid², channels). True retains the observed value; False inserts the declared baseline.
5. A fixed scalar target (classification logit or segmentation score over a fixed region) that stays constant for all coalition evaluations.
6. Deterministic CPU inference for the declared seed and settings, or an explicit GPU requirement when CPU operation is genuinely infeasible.
7. A preview adapter for original input, ground truth (if applicable), and model prediction. Preview conversion must not alter attribution inputs.
8. Grid and estimation options with run-cost caps. Exact Shapley enumeration is exponential in the number of channels; high-dimensional spectral cubes normally require permutation sampling.
9. An end-to-end test loading the actual checkpoint/input and checking channel/cell shape, finite values, per-cell efficiency and a saved reference output.

No model should appear as a runnable option in /api/catalog until all required pieces exist and the adapter passes a real-data test.

For a newly supplied dataset, start with a single verified input and model. Add more examples after the full checkpoint→preprocessing→scalar score→SSI path is reproducible.
