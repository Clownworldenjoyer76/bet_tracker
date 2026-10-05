# MLB Run Model Comparison

- Generated: `2026-10-05T18:59:37.248510+00:00`
- Untouched chronological test period: `2026-09-05` through `2026-10-04`
- Test games: `80`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.026137 | 2.340974 | NO |
| away | 2.055004 | 1.909737 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 80 | 2.374875 | 2.026137 | 4.291875 | 4.475000 |
| new_model | home | 80 | 2.541516 | 2.340974 | 4.354858 | 4.475000 |
| dratings | away | 80 | 2.254000 | 2.055004 | 4.032000 | 4.675000 |
| new_model | away | 80 | 2.230141 | 1.909737 | 4.302556 | 4.675000 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.374875` -> `2.541516`; Poisson deviance `2.026137` -> `2.340974`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.254000` -> `2.230141`; Poisson deviance `2.055004` -> `1.909737`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.130148 | NO | 0.733333 | NO | 10 |
| run_line | 0.152453 | NO | -0.179644 | NO | 8 |
| total | 0.175269 | NO | 0.428571 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 80 | 0.625437 |
| dratings | run_line | home | 79 | 0.700516 |
| dratings | total | over_resolved | 78 | 0.698819 |
| new_model | moneyline | home | 80 | 0.714033 |
| new_model | run_line | home | 79 | 0.743026 |
| new_model | total | over_resolved | 78 | 0.757563 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `478`; positive-EV candidates: `205`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045107` vs `-0.056067`.
- New-model positive-EV mean predicted EV vs realized return: `0.226254` vs `-0.043707`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.049260`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055822` vs `-0.056067`; EV/return Spearman `-0.042265`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.991882`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `79`.
- Higher-EV side was `-1.5` in `34` games (`43.04%` of non-ties).
- Higher-EV side was `+1.5` in `45` games (`56.96%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
