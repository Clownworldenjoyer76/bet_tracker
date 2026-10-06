# MLB Run Model Comparison

- Generated: `2026-10-06T07:48:56.793590+00:00`
- Untouched chronological test period: `2026-09-06` through `2026-10-05`
- Test games: `80`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.010729 | 2.123706 | NO |
| away | 2.027658 | 1.933884 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 80 | 2.358250 | 2.010729 | 4.257000 | 4.475000 |
| new_model | home | 80 | 2.409053 | 2.123706 | 4.546299 | 4.475000 |
| dratings | away | 80 | 2.222500 | 2.027658 | 4.032750 | 4.612500 |
| new_model | away | 80 | 2.243261 | 1.933884 | 4.292465 | 4.612500 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.358250` -> `2.409053`; Poisson deviance `2.010729` -> `2.123706`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.222500` -> `2.243261`; Poisson deviance `2.027658` -> `1.933884`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.091010 | NO | 0.928571 | NO | 8 |
| run_line | 0.168670 | NO | 0.404762 | NO | 8 |
| total | 0.106519 | NO | 1.000000 | YES | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **YES**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 80 | 0.627187 |
| dratings | run_line | home | 79 | 0.692981 |
| dratings | total | over_resolved | 79 | 0.701792 |
| new_model | moneyline | home | 80 | 0.675745 |
| new_model | run_line | home | 79 | 0.737260 |
| new_model | total | over_resolved | 79 | 0.691485 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `478`; positive-EV candidates: `199`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046148` vs `-0.060000`.
- New-model positive-EV mean predicted EV vs realized return: `0.180865` vs `-0.137688`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.052214`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055439` vs `-0.060000`; EV/return Spearman `-0.061778`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994751`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `79`.
- Higher-EV side was `-1.5` in `23` games (`29.11%` of non-ties).
- Higher-EV side was `+1.5` in `56` games (`70.89%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
