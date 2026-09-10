# MLB Run Model Comparison

- Generated: `2026-09-10T07:43:30.946897+00:00`
- Untouched chronological test period: `2026-08-13` through `2026-09-09`
- Test games: `158`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.224821 | 2.334194 | NO |
| away | 2.494362 | 2.436373 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 158 | 2.357848 | 2.224821 | 4.353418 | 4.575949 |
| new_model | home | 158 | 2.416945 | 2.334194 | 4.237851 | 4.575949 |
| dratings | away | 158 | 2.496203 | 2.494362 | 4.109367 | 4.322785 |
| new_model | away | 158 | 2.487689 | 2.436373 | 4.207553 | 4.322785 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.357848` -> `2.416945`; Poisson deviance `2.224821` -> `2.334194`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.496203` -> `2.487689`; Poisson deviance `2.494362` -> `2.436373`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.076664 | NO | 0.952381 | NO | 8 |
| run_line | 0.139232 | NO | 0.738095 | NO | 8 |
| total | 0.117280 | NO | -0.083834 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 158 | 0.668039 |
| dratings | run_line | home | 157 | 0.684723 |
| dratings | total | over_resolved | 154 | 0.719583 |
| new_model | moneyline | home | 158 | 0.682599 |
| new_model | run_line | home | 157 | 0.690358 |
| new_model | total | over_resolved | 154 | 0.715295 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `946`; positive-EV candidates: `413`.
- New-model all-candidate mean predicted EV vs realized return: `-0.043737` vs `-0.048605`.
- New-model positive-EV mean predicted EV vs realized return: `0.186513` vs `-0.023898`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.024945`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049595` vs `-0.048605`; EV/return Spearman `-0.110606`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993912`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `157`.
- Higher-EV side was `-1.5` in `38` games (`24.20%` of non-ties).
- Higher-EV side was `+1.5` in `119` games (`75.80%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
