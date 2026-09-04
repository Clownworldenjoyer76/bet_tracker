# MLB Run Model Comparison

- Generated: `2026-09-04T07:43:18.789333+00:00`
- Untouched chronological test period: `2026-08-08` through `2026-09-03`
- Test games: `164`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.180586 | 2.198607 | NO |
| away | 2.538785 | 2.506198 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 164 | 2.312866 | 2.180586 | 4.345061 | 4.493902 |
| new_model | home | 164 | 2.325306 | 2.198607 | 4.290154 | 4.493902 |
| dratings | away | 164 | 2.523293 | 2.538785 | 4.155610 | 4.219512 |
| new_model | away | 164 | 2.527390 | 2.506198 | 4.286937 | 4.219512 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.312866` -> `2.325306`; Poisson deviance `2.180586` -> `2.198607`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.523293` -> `2.527390`; Poisson deviance `2.538785` -> `2.506198`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.071259 | NO | 0.952381 | NO | 8 |
| run_line | 0.105747 | NO | 0.261905 | NO | 8 |
| total | 0.121939 | NO | -0.285714 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 164 | 0.669613 |
| dratings | run_line | home | 164 | 0.695688 |
| dratings | total | over_resolved | 162 | 0.716395 |
| new_model | moneyline | home | 164 | 0.680006 |
| new_model | run_line | home | 164 | 0.687358 |
| new_model | total | over_resolved | 162 | 0.720907 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `984`; positive-EV candidates: `417`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045298` vs `-0.046199`.
- New-model positive-EV mean predicted EV vs realized return: `0.152592` vs `-0.043573`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.002952`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049335` vs `-0.046199`; EV/return Spearman `-0.115564`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993878`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `164`.
- Higher-EV side was `-1.5` in `39` games (`23.78%` of non-ties).
- Higher-EV side was `+1.5` in `125` games (`76.22%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
