# MLB Run Model Comparison

- Generated: `2026-10-11T07:43:16.686336+00:00`
- Untouched chronological test period: `2026-09-09` through `2026-10-10`
- Test games: `78`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.081789 | 2.293055 | NO |
| away | 2.145972 | 2.105698 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 78 | 2.383590 | 2.081789 | 4.210513 | 4.333333 |
| new_model | home | 78 | 2.519699 | 2.293055 | 4.562755 | 4.333333 |
| dratings | away | 78 | 2.291538 | 2.145972 | 4.031026 | 4.653846 |
| new_model | away | 78 | 2.322355 | 2.105698 | 4.247121 | 4.653846 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.383590` -> `2.519699`; Poisson deviance `2.081789` -> `2.293055`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.291538` -> `2.322355`; Poisson deviance `2.145972` -> `2.105698`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.087152 | NO | 0.586837 | NO | 8 |
| run_line | 0.184103 | NO | 0.380952 | NO | 8 |
| total | 0.099804 | NO | -0.443122 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 78 | 0.622450 |
| dratings | run_line | home | 77 | 0.712836 |
| dratings | total | over_resolved | 75 | 0.708136 |
| new_model | moneyline | home | 78 | 0.693609 |
| new_model | run_line | home | 77 | 0.773776 |
| new_model | total | over_resolved | 75 | 0.729001 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `466`; positive-EV candidates: `199`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046757` vs `-0.053283`.
- New-model positive-EV mean predicted EV vs realized return: `0.189543` vs `-0.178291`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.107362`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.054928` vs `-0.053283`; EV/return Spearman `-0.058412`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994083`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `77`.
- Higher-EV side was `-1.5` in `25` games (`32.47%` of non-ties).
- Higher-EV side was `+1.5` in `52` games (`67.53%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
