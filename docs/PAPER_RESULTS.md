# Paper-reported numerical results

These values are transcribed from *Spectral-Spatial Interpretation* and were checked
against the rendered PDF tables. They are distinct from the bundled HLS demonstration. This page preserves the
printed mean and bootstrap-standard-deviation precision, including entries rounded to `.000` in Table 1.

All estimates are shown as **mean ± bootstrap standard deviation**. The manuscript reports 1,000 bootstrap
resamples over per-image metrics. Bold marks the best numerical mean in a column (or across methods for a metric),
not statistical significance. No confidence interval or paired significance test is inferred from these values.

| Source | Settings and content |
|---|---|
| Table 1 | Mean and zero baselines; CUB 16 × 16, EuroSAT/HLS 8 × 8 grids |
| Table 2 | SSI versus MC-Owen on HLS, 384 grid-cell/channel players |
| Tables 4–7 | Alternative grids, per-channel mean baseline |
| Tables 8–9 | Spatial mIoU at reported coverage levels |
| Tables 10–11 | Channel deletion and Hit@1 through Hit@5 |

Return to the [README](../README.md#-comparison-of-methods).

## Table 1: Joint faithfulness

Joint deletion ranks grid-cell/channel players. Rank-1 deletion evaluates the leading rank-1 approximation of the
joint attribution matrix. Insertion ranks spatial cells by channel-summed attribution. Lower deletion AUC and higher
insertion AUC are better. These settings use the same player space for every method.

### Per-channel mean baseline

**CUB-200**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.0088±.001** | **.0104±.001** | **.7132±.019** |
| IG | .0112±.001 | .0126±.001 | .2895±.022 |
| DeepSHAP | .0112±.001 | .0127±.001 | .2853±.022 |
| KernelSHAP | .0178±.001 | .0222±.002 | .3481±.019 |
| RISE | .0183±.001 | .0183±.001 | .6886±.017 |

**EuroSAT**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.1397±.020** | **.1682±.021** | **.7319±.023** |
| IG | .2097±.030 | .2267±.030 | .6621±.029 |
| DeepSHAP | .2078±.029 | .2255±.031 | .6614±.028 |
| KernelSHAP | .2434±.027 | .2824±.028 | .5767±.030 |
| RISE | .2130±.026 | .1969±.023 | .7091±.023 |

**HLS Burn Scar**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.1545±.008** | **.1657±.010** | **.6638±.008** |
| IG | .2160±.011 | .2723±.015 | .6291±.009 |
| DeepSHAP | .2149±.011 | .2704±.016 | .6321±.009 |
| KernelSHAP | .2096±.012 | .2558±.016 | .5500±.008 |
| RISE | .2888±.016 | .2871±.015 | .6130±.009 |

### Zero baseline

**CUB-200**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.0063±.000** | **.0072±.001** | **.5224±.017** |
| IG | .0083±.001 | .0085±.001 | .0832±.013 |
| DeepSHAP | .0083±.000 | .0084±.001 | .0802±.012 |
| KernelSHAP | .0154±.001 | .0327±.003 | .1523±.011 |
| RISE | .0142±.001 | .0144±.001 | .4246±.021 |

**EuroSAT**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.0763±.015** | **.0850±.017** | **.6001±.024** |
| IG | .1434±.023 | .1874±.029 | .4983±.033 |
| DeepSHAP | .1444±.024 | .1876±.028 | .4963±.032 |
| KernelSHAP | .1521±.017 | .1862±.020 | .4257±.031 |
| RISE | .1599±.019 | .1741±.023 | .5644±.029 |

**HLS Burn Scar**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.1203±.009** | **.1175±.010** | **.6564±.008** |
| IG | .1785±.010 | .1802±.011 | .6140±.009 |
| DeepSHAP | .1776±.010 | .1802±.011 | .6174±.009 |
| KernelSHAP | .1555±.009 | .1637±.009 | .5503±.008 |
| RISE | .1971±.010 | .2229±.010 | .6116±.008 |

## Table 2: Observed-context SSI versus MC-Owen

| Metric | SSI | MC-Owen |
|---|:---:|:---:|
| Joint deletion ↓ | **.155±.008** | .173±.010 |
| Rank-1 deletion ↓ | **.166±.010** | .254±.017 |
| Channel deletion ↓ | **.218±.009** | .261±.017 |
| Grid-sum insertion ↑ | **.664±.008** | .627±.009 |
| Spatial mIoU at Top-5% ↑ | **.311±.012** | .299±.018 |
| Spatial mIoU at Top-15% ↑ | **.387±.014** | .254±.017 |
| Spatial mIoU at Top-25% ↑ | **.332±.017** | .224±.017 |
| Spectral Hit@1 ↑ | **.317±.007** | .287±.011 |
| Spectral Hit@3 ↑ | **.603±.016** | .460±.017 |
| Spectral Hit@5 ↑ | **.887±.016** | .730±.013 |

The paper reports up to 4,480 SSI evaluations and 76,800 MC-Owen evaluations using its stated
forward-pass counting convention. These counts are not measured wall-clock runtime.

## Tables 4-7: Grid resolution

Per-channel mean baseline for every method and setting.

**Table 4. HLS Burn Scar · 4 × 4**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.1544±.0082** | **.1588±.0097** | **.6310±.0077** |
| IG | .2499±.0159 | .2792±.0171 | .5739±.0089 |
| DeepSHAP | .2481±.0145 | .2793±.0176 | .5835±.0089 |
| KernelSHAP | .2129±.0149 | .2534±.0179 | .5651±.0080 |
| RISE | .4320±.0188 | .4330±.0190 | .5327±.0070 |

**Table 5. CUB-200 · 4 × 4**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.0239±.0011** | **.0264±.0013** | **.7267±.0111** |
| IG | .0257±.0012 | .0284±.0015 | .6515±.0149 |
| DeepSHAP | .0259±.0012 | .0279±.0013 | .6511±.0146 |
| KernelSHAP | .0263±.0012 | .0285±.0013 | .6900±.0124 |
| RISE | .0329±.0017 | .0329±.0015 | .7109±.0113 |

**Table 6. CUB-200 · 8 × 8**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.0123±.0007** | **.0154±.0010** | **.7567±.0116** |
| IG | .0152±.0008 | .0169±.0010 | .5215±.0213 |
| DeepSHAP | .0151±.0008 | .0170±.0010 | .5204±.0221 |
| KernelSHAP | .0169±.0008 | .0240±.0016 | .5688±.0188 |
| RISE | .0225±.0013 | .0225±.0012 | .7425±.0118 |

**Table 7. EuroSAT · 4 × 4**

| Method | Joint deletion ↓ | Rank-1 deletion ↓ | Insertion ↑ |
|---|:---:|:---:|:---:|
| 🧩 **SSI** | **.1295±.0158** | **.1425±.0155** | **.7096±.0195** |
| IG | .1957±.0233 | .1745±.0217 | .6731±.0224 |
| DeepSHAP | .1963±.0234 | .1750±.0217 | .6730±.0223 |
| KernelSHAP | .1416±.0199 | .1458±.0181 | .6432±.0240 |
| RISE | .2116±.0272 | .2120±.0263 | .7007±.0188 |

## Tables 8-9: Spatial localization

Higher mIoU is better. “Average” retains the paper's reported mean and uncertainty across its coverage levels.

**CUB-200 · Table 8**

| Method | Top-10% ↑ | Top-20% ↑ | Top-30% ↑ | Top-40% ↑ | Top-50% ↑ | Average ↑ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🧩 **SSI** | **.2208±.0102** | **.3103±.0080** | **.3592±.0082** | **.3893±.0102** | **.4036±.0118** | **.3366±.0044** |
| IG | .2148±.0083 | .2926±.0053 | .3228±.0054 | .3342±.0079 | .3361±.0099 | .3001±.0034 |
| DeepSHAP | .2150±.0079 | .2929±.0050 | .3220±.0052 | .3333±.0074 | .3362±.0101 | .2999±.0033 |
| KernelSHAP | .1061±.0024 | .1787±.0030 | .2267±.0044 | .2674±.0071 | .2970±.0095 | .2152±.0026 |
| RISE | .2099±.0090 | .2888±.0074 | .3293±.0072 | .3529±.0086 | .3671±.0103 | .3096±.0038 |

**HLS Burn Scar · Table 9**

| Method | Top-5% ↑ | Top-10% ↑ | Top-15% ↑ | Top-20% ↑ | Top-25% ↑ | Average ↑ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🧩 **SSI** | **.3109±.0113** | **.3886±.0131** | **.3874±.0137** | **.3587±.0159** | **.3321±.0155** | **.3555±.0065** |
| IG | .2722±.0175 | .2699±.0162 | .2552±.0162 | .2396±.0168 | .2245±.0174 | .2523±.0075 |
| DeepSHAP | .2850±.0177 | .2776±.0157 | .2583±.0157 | .2441±.0178 | .2270±.0174 | .2584±.0076 |
| KernelSHAP | .0809±.0102 | .0932±.0101 | .1075±.0115 | .1183±.0115 | .1228±.0127 | .1045±.0050 |
| RISE | .1589±.0108 | .1913±.0116 | .2145±.0119 | .2346±.0113 | .2585±.0131 | .2116±.0048 |

EuroSAT is omitted because the manuscript reports no discriminative spatial ground-truth proxy for this evaluation.

## Tables 10-11: Spectral aggregation

Lower channel deletion AUC and higher Hit@K are better. Hit@K is `|TopK(A) ∩ T_y| / |T_y|`, where `T_y` is the
class-specific prior-band set (Appendix C.2). The paper defines this average over correctly classified samples.

**HLS Burn Scar · Table 10**

| Method | Channel deletion ↓ | Hit@1 ↑ | Hit@2 ↑ | Hit@3 ↑ | Hit@4 ↑ | Hit@5 ↑ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🧩 **SSI** | **.2180±.0094** | **.3167±.0068** | **.4333±.0158** | **.6033±.0159** | **.7567±.0193** | **.8867±.0163** |
| IG | .2724±.0178 | .3000±.0092 | .3667±.0148 | .4200±.0154 | .5767±.0148 | .7600±.0148 |
| DeepSHAP | .2723±.0174 | .3000±.0103 | .3667±.0145 | .4233±.0160 | .5767±.0147 | .7600±.0151 |
| KernelSHAP | .2568±.0161 | .2833±.0120 | .3567±.0126 | .4633±.0163 | .6067±.0167 | .7533±.0145 |
| RISE | .3166±.0204 | .2333±.0153 | .3067±.0200 | .5000±.0192 | .5533±.0159 | .6700±.0034 |

**EuroSAT · Table 11**

| Method | Channel deletion ↓ | Hit@1 ↑ | Hit@2 ↑ | Hit@3 ↑ | Hit@4 ↑ | Hit@5 ↑ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🧩 **SSI** | **.1039±.0165** | **.1768±.0231** | **.3472±.0236** | **.4545±.0323** | **.5328±.0289** | **.5960±.0264** |
| IG | .1426±.0231 | .0258±.0115 | .2220±.0283 | .3061±.0313 | .3881±.0322 | .4624±.0335 |
| DeepSHAP | .1437±.0241 | .0258±.0113 | .2220±.0291 | .3061±.0306 | .3843±.0341 | .4573±.0358 |
| KernelSHAP | .1347±.0209 | .0879±.0205 | .2207±.0298 | .3295±.0330 | .4232±.0335 | .5394±.0366 |
| RISE | .1387±.0207 | .0788±.0181 | .1876±.0241 | .2629±.0288 | .3311±.0270 | .4258±.0242 |
