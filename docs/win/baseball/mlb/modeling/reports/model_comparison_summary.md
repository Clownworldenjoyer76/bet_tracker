# MLB Run Model Comparison

- Generated: `2026-10-07T07:46:49.758204+00:00`
- Untouched chronological test period: `2026-09-06` through `2026-10-06`
- Test games: `81`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.014094 | 2.134277 | NO |
| away | 2.001620 | 1.920083 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 81 | 2.351235 | 2.014094 | 4.251235 | 4.444444 |
| new_model | home | 81 | 2.405939 | 2.134277 | 4.541490 | 4.444444 |
| dratings | away | 81 | 2.197778 | 2.001620 | 4.035062 | 4.580247 |
| new_model | away | 81 | 2.245321 | 1.920083 | 4.295304 | 4.580247 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.351235` -> `2.405939`; Poisson deviance `2.014094` -> `2.134277`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.197778` -> `2.245321`; Poisson deviance `2.001620` -> `1.920083`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.072368 | NO | 0.952381 | NO | 8 |
| run_line | 0.174728 | NO | 0.404762 | NO | 8 |
| total | 0.125613 | NO | 0.952381 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 81 | 0.620366 |
| dratings | run_line | home | 80 | 0.698588 |
| dratings | total | over_resolved | 80 | 0.704978 |
| new_model | moneyline | home | 81 | 0.670556 |
| new_model | run_line | home | 80 | 0.741532 |
| new_model | total | over_resolved | 80 | 0.709066 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `484`; positive-EV candidates: `202`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046185` vs `-0.059773`.
- New-model positive-EV mean predicted EV vs realized return: `0.179715` vs `-0.150149`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.068111`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055507` vs `-0.059773`; EV/return Spearman `-0.065249`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994787`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `80`.
- Higher-EV side was `-1.5` in `23` games (`28.75%` of non-ties).
- Higher-EV side was `+1.5` in `57` games (`71.25%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
