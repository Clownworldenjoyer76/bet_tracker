# MLB Run Model Comparison

- Generated: `2026-09-19T07:41:41.415021+00:00`
- Untouched chronological test period: `2026-08-24` through `2026-09-18`
- Test games: `120`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_promoted`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.079114 | 2.041504 | YES |
| away | 2.476341 | 2.473104 | YES |

- Production artifacts changed: **YES**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 120 | 2.336333 | 2.079114 | 4.270167 | 4.475000 |
| new_model | home | 120 | 2.350027 | 2.041504 | 4.316313 | 4.475000 |
| dratings | away | 120 | 2.553500 | 2.476341 | 4.161667 | 4.608333 |
| new_model | away | 120 | 2.620588 | 2.473104 | 4.253318 | 4.608333 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.336333` -> `2.350027`; Poisson deviance `2.079114` -> `2.041504`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.553500` -> `2.620588`; Poisson deviance `2.476341` -> `2.473104`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.118557 | NO | 0.680854 | NO | 10 |
| run_line | 0.095771 | NO | 0.733333 | NO | 10 |
| total | 0.135622 | NO | -0.285714 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 120 | 0.674548 |
| dratings | run_line | home | 119 | 0.678670 |
| dratings | total | over_resolved | 116 | 0.722744 |
| new_model | moneyline | home | 120 | 0.676891 |
| new_model | run_line | home | 119 | 0.672980 |
| new_model | total | over_resolved | 116 | 0.743276 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `718`; positive-EV candidates: `307`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046663` vs `-0.046198`.
- New-model positive-EV mean predicted EV vs realized return: `0.172938` vs `0.010423`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.042694`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.050353` vs `-0.046198`; EV/return Spearman `-0.119579`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993974`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `119`.
- Higher-EV side was `-1.5` in `25` games (`21.01%` of non-ties).
- Higher-EV side was `+1.5` in `94` games (`78.99%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
