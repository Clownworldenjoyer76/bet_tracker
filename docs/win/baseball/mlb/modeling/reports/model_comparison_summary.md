# MLB Run Model Comparison

- Generated: `2026-10-09T07:44:55.630744+00:00`
- Untouched chronological test period: `2026-09-08` through `2026-10-08`
- Test games: `82`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.006797 | 2.098162 | NO |
| away | 2.089375 | 2.087415 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 82 | 2.325976 | 2.006797 | 4.225976 | 4.304878 |
| new_model | home | 82 | 2.374267 | 2.098162 | 4.500895 | 4.304878 |
| dratings | away | 82 | 2.282317 | 2.089375 | 4.027195 | 4.682927 |
| new_model | away | 82 | 2.307078 | 2.087415 | 4.102078 | 4.682927 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.325976` -> `2.374267`; Poisson deviance `2.006797` -> `2.098162`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.282317` -> `2.307078`; Poisson deviance `2.089375` -> `2.087415`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.150371 | NO | -0.127273 | NO | 10 |
| run_line | 0.244827 | NO | -0.011976 | NO | 8 |
| total | 0.054842 | NO | 0.507093 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 82 | 0.618355 |
| dratings | run_line | home | 81 | 0.705240 |
| dratings | total | over_resolved | 79 | 0.701752 |
| new_model | moneyline | home | 82 | 0.704905 |
| new_model | run_line | home | 81 | 0.771285 |
| new_model | total | over_resolved | 79 | 0.688205 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `490`; positive-EV candidates: `201`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046109` vs `-0.057755`.
- New-model positive-EV mean predicted EV vs realized return: `0.198058` vs `-0.124627`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.084984`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055166` vs `-0.057755`; EV/return Spearman `-0.050934`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993817`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `81`.
- Higher-EV side was `-1.5` in `27` games (`33.33%` of non-ties).
- Higher-EV side was `+1.5` in `54` games (`66.67%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
