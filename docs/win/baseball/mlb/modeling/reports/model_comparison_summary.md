# MLB Run Model Comparison

- Generated: `2026-09-08T12:16:16.040419+00:00`
- Untouched chronological test period: `2026-08-12` through `2026-09-07`
- Test games: `154`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.198154 | 2.245248 | NO |
| away | 2.493626 | 2.431618 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 154 | 2.329481 | 2.198154 | 4.351818 | 4.551948 |
| new_model | home | 154 | 2.388592 | 2.245248 | 4.372950 | 4.551948 |
| dratings | away | 154 | 2.498636 | 2.493626 | 4.125130 | 4.318182 |
| new_model | away | 154 | 2.493586 | 2.431618 | 4.256527 | 4.318182 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.329481` -> `2.388592`; Poisson deviance `2.198154` -> `2.245248`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.498636` -> `2.493586`; Poisson deviance `2.493626` -> `2.431618`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.099608 | NO | 0.857143 | NO | 8 |
| run_line | 0.138417 | NO | 0.586837 | NO | 8 |
| total | 0.101507 | NO | -0.485714 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 154 | 0.673669 |
| dratings | run_line | home | 153 | 0.685102 |
| dratings | total | over_resolved | 150 | 0.720374 |
| new_model | moneyline | home | 154 | 0.687833 |
| new_model | run_line | home | 153 | 0.697277 |
| new_model | total | over_resolved | 150 | 0.724203 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `922`; positive-EV candidates: `407`.
- New-model all-candidate mean predicted EV vs realized return: `-0.043752` vs `-0.046605`.
- New-model positive-EV mean predicted EV vs realized return: `0.173811` vs `-0.015184`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.012374`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049247` vs `-0.046605`; EV/return Spearman `-0.109859`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993996`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `153`.
- Higher-EV side was `-1.5` in `37` games (`24.18%` of non-ties).
- Higher-EV side was `+1.5` in `116` games (`75.82%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
