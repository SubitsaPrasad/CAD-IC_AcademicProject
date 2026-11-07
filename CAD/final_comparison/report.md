# Final comparison: TD3 vs random baseline (seed 1, 4950 sims each)

**Runs** (measured, from `solutions/*.csv`):
- TD3: `python td3_runner.py --batch_size 256 --w 100 --T 4500 --noise_sigma 0.2 --pi_lr 3e-4 --q_lr 3e-4 --run_id td3_5k_opt_s1_final` -> `td3_5k_opt_s1_final.csv`
- Baseline: `baseline_5k_s1_final.csv`
- Budget: 4950 sims each (T=4500, within the 5k limit). Feasible = gain>200, PM>60, UGBW>100 MHz, SR>30 V/us, noise<30 mV.

## Results
| Metric | TD3 | Baseline |
|---|---|---|
| Max FoM | **0.678** (sim 4623) | 0.637 (sim 4419) |
| Best-so-far @500 / 1000 / 2000 / 3000 / 4000 sims | 0.549 / 0.671 / 0.671 / 0.671 / 0.671 | -0.024 / 0.142 / 0.399 / 0.565 / 0.634 |
| Mean FoM, last 1000 sims | -0.549 | -0.662 |
| Feasible designs | 733 | 119 |
| First feasible design | sim 454 | sim 582 |

Best designs:
| Spec | TD3 | Baseline |
|---|---|---|
| Area | 6.02e-10 | 6.83e-10 |
| Current | 276 uA | 273 uA |
| Gain | 367 | 275 |
| PM | 64.4 deg | 64.7 deg |
| UGBW | 102.7 MHz | 110.8 MHz |
| SR | 55 V/us | 61 V/us |
| Noise | 9.5 mV | 7.6 mV |

Figure: `comparison.png` (max-FoM vs sims; feasible designs with current-area Pareto front).

## Discussion
- TD3 reaches FoM 0.671 within 1000 sims; the baseline needs about 4000 sims for 0.634. Learning from replay data gives clearly better sample efficiency than the baseline.
- TD3 finds about 6x more feasible designs, so its policy stays in the feasible region rather than only hitting it by chance.
- Final max FoM differs by only 0.041, and TD3 plateaued from sim 1000 to 4623. The advantage is mostly speed and consistency, not a much better optimum.
- TD3's best design uses about 12% less area at similar current.

## Caveats
- One seed per method. Baseline runs of the same seed differ (`baseline_5k_s1` max FoM 0.671 vs `baseline_5k_s1_final` 0.637), because warmup and action sampling are unseeded (TA code unchanged). The report needs >=3 seeds with mean +/- spread before claiming TD3 > baseline.
- Both best designs are close to the PM/UGBW limits, so small variations could break feasibility.
