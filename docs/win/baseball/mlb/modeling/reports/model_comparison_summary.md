# MLB Run Model Comparison

- Generated: `2026-10-03T15:00:42.260401+00:00`
- Untouched chronological test period: `2026-09-03` through `2026-10-01`
- Test games: `83`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.914439 | 1.968534 | NO |
| away | 2.026247 | 2.038193 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 83 | 2.279759 | 1.914439 | 4.315663 | 4.566265 |
| new_model | home | 83 | 2.297389 | 1.968534 | 4.570546 | 4.566265 |
| dratings | away | 83 | 2.277108 | 2.026247 | 4.036627 | 4.783133 |
| new_model | away | 83 | 2.352037 | 2.038193 | 4.110341 | 4.783133 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.279759` -> `2.297389`; Poisson deviance `1.914439` -> `1.968534`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.277108` -> `2.352037`; Poisson deviance `2.026247` -> `2.038193`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.104850 | NO | 0.857143 | NO | 8 |
| run_line | 0.135758 | NO | 0.738095 | NO | 8 |
| total | 0.176336 | NO | -0.380952 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 83 | 0.636523 |
| dratings | run_line | home | 81 | 0.698506 |
| dratings | total | over_resolved | 80 | 0.703897 |
| new_model | moneyline | home | 83 | 0.665127 |
| new_model | run_line | home | 81 | 0.705124 |
| new_model | total | over_resolved | 80 | 0.713106 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `494`; positive-EV candidates: `217`.
- New-model all-candidate mean predicted EV vs realized return: `-0.044941` vs `-0.054534`.
- New-model positive-EV mean predicted EV vs realized return: `0.201627` vs `-0.065438`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.027866`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.056580` vs `-0.054534`; EV/return Spearman `-0.062983`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992317`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `81`.
- Higher-EV side was `-1.5` in `28` games (`34.57%` of non-ties).
- Higher-EV side was `+1.5` in `53` games (`65.43%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
