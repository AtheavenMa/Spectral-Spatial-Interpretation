# Numerical regression reference

`hls_legacy_reference.npz` records outputs from the previous model, generated
locally during the MIT migration. It includes full HLS logits, four SSI
attribution arrays, position contrasts, and a synthetic odd-size input/output
probe. It contains no legacy source code and no model parameters.

The corresponding HLS example and model sources are documented in [third-party notices](../../THIRD_PARTY_NOTICES.md).
HLS-derived arrays use the dataset attribution in [third-party notices](../../THIRD_PARTY_NOTICES.md).
They are separate from the MIT-licensed test code. The old implementation is not
needed to run these tests.
