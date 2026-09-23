# MLB Run Model Comparison

- Generated: `2026-09-23T07:43:55.067537+00:00`
- Untouched chronological test period: `2026-08-27` through `2026-09-22`
- Test games: `93`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.008376 | 2.038332 | NO |
| away | 2.241720 | 2.181547 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 93 | 2.343226 | 2.008376 | 4.277849 | 4.623656 |
| new_model | home | 93 | 2.371880 | 2.038332 | 4.289691 | 4.623656 |
| dratings | away | 93 | 2.436559 | 2.241720 | 4.098065 | 4.602151 |
| new_model | away | 93 | 2.419439 | 2.181547 | 4.096628 | 4.602151 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.343226` -> `2.371880`; Poisson deviance `2.008376` -> `2.038332`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.436559` -> `2.419439`; Poisson deviance `2.241720` -> `2.181547`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.137308 | NO | 0.857143 | NO | 8 |
| run_line | 0.109319 | NO | 0.915152 | NO | 10 |
| total | 0.139987 | NO | -0.485714 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 93 | 0.641990 |
| dratings | run_line | home | 92 | 0.673585 |
| dratings | total | over_resolved | 88 | 0.708761 |
| new_model | moneyline | home | 93 | 0.634721 |
| new_model | run_line | home | 92 | 0.661004 |
| new_model | total | over_resolved | 88 | 0.737755 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `556`; positive-EV candidates: `233`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046376` vs `-0.053741`.
- New-model positive-EV mean predicted EV vs realized return: `0.173572` vs `0.033133`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.081071`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.052697` vs `-0.053741`; EV/return Spearman `-0.068868`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993080`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `92`.
- Higher-EV side was `-1.5` in `27` games (`29.35%` of non-ties).
- Higher-EV side was `+1.5` in `65` games (`70.65%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
