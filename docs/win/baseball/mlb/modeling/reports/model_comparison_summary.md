# MLB Run Model Comparison

- Generated: `2026-09-12T07:43:09.168183+00:00`
- Untouched chronological test period: `2026-08-15` through `2026-09-11`
- Test games: `156`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.282237 | 2.318319 | NO |
| away | 2.480438 | 2.798593 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 156 | 2.376154 | 2.282237 | 4.346795 | 4.570513 |
| new_model | home | 156 | 2.417446 | 2.318319 | 4.351991 | 4.570513 |
| dratings | away | 156 | 2.496410 | 2.480438 | 4.117436 | 4.339744 |
| new_model | away | 156 | 2.641158 | 2.798593 | 3.690668 | 4.339744 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.376154` -> `2.417446`; Poisson deviance `2.282237` -> `2.318319`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.496410` -> `2.641158`; Poisson deviance `2.480438` -> `2.798593`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.178367 | NO | 0.975758 | NO | 10 |
| run_line | 0.141255 | NO | 0.668696 | NO | 10 |
| total | 0.168414 | NO | -0.928571 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 156 | 0.665047 |
| dratings | run_line | home | 155 | 0.693836 |
| dratings | total | over_resolved | 152 | 0.720577 |
| new_model | moneyline | home | 156 | 0.710761 |
| new_model | run_line | home | 155 | 0.753635 |
| new_model | total | over_resolved | 152 | 0.793401 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `934`; positive-EV candidates: `420`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046398` vs `-0.047409`.
- New-model positive-EV mean predicted EV vs realized return: `0.251140` vs `-0.055643`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.023010`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049780` vs `-0.047409`; EV/return Spearman `-0.121820`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993187`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `155`.
- Higher-EV side was `-1.5` in `52` games (`33.55%` of non-ties).
- Higher-EV side was `+1.5` in `103` games (`66.45%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
