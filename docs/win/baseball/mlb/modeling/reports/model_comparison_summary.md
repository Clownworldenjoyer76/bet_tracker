# MLB Run Model Comparison

- Generated: `2026-09-06T07:41:56.461605+00:00`
- Untouched chronological test period: `2026-08-10` through `2026-09-05`
- Test games: `168`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.136876 | 2.446506 | NO |
| away | 2.523535 | 2.579746 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 168 | 2.277262 | 2.136876 | 4.353452 | 4.500000 |
| new_model | home | 168 | 2.317258 | 2.446506 | 3.550192 | 4.500000 |
| dratings | away | 168 | 2.520476 | 2.523535 | 4.136786 | 4.267857 |
| new_model | away | 168 | 2.593021 | 2.579746 | 4.215388 | 4.267857 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.277262` -> `2.317258`; Poisson deviance `2.136876` -> `2.446506`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.520476` -> `2.593021`; Poisson deviance `2.523535` -> `2.579746`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.133111 | NO | 0.515152 | NO | 10 |
| run_line | 0.132761 | NO | 0.915152 | NO | 10 |
| total | 0.175623 | NO | 0.042424 | NO | 10 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 168 | 0.675457 |
| dratings | run_line | home | 167 | 0.693208 |
| dratings | total | over_resolved | 165 | 0.714765 |
| new_model | moneyline | home | 168 | 0.731355 |
| new_model | run_line | home | 167 | 0.721487 |
| new_model | total | over_resolved | 165 | 0.766184 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `1006`; positive-EV candidates: `465`.
- New-model all-candidate mean predicted EV vs realized return: `-0.043492` vs `-0.046193`.
- New-model positive-EV mean predicted EV vs realized return: `0.288995` vs `-0.013677`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.062216`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049718` vs `-0.046193`; EV/return Spearman `-0.118307`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993492`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `167`.
- Higher-EV side was `-1.5` in `64` games (`38.32%` of non-ties).
- Higher-EV side was `+1.5` in `103` games (`61.68%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
