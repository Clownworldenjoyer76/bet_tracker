# MLB Run Model Comparison

- Generated: `2026-10-08T07:46:13.522429+00:00`
- Untouched chronological test period: `2026-09-07` through `2026-10-07`
- Test games: `83`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.998680 | 2.115861 | NO |
| away | 2.005622 | 1.911497 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 83 | 2.326867 | 1.998680 | 4.230482 | 4.337349 |
| new_model | home | 83 | 2.369897 | 2.115861 | 4.452265 | 4.337349 |
| dratings | away | 83 | 2.205301 | 2.005622 | 4.040723 | 4.614458 |
| new_model | away | 83 | 2.218325 | 1.911497 | 4.312761 | 4.614458 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.326867` -> `2.369897`; Poisson deviance `1.998680` -> `2.115861`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.205301` -> `2.218325`; Poisson deviance `2.005622` -> `1.911497`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.090385 | NO | 0.103660 | NO | 10 |
| run_line | 0.182959 | NO | 0.500000 | NO | 8 |
| total | 0.075006 | NO | 0.730552 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 83 | 0.625462 |
| dratings | run_line | home | 82 | 0.692329 |
| dratings | total | over_resolved | 80 | 0.703226 |
| new_model | moneyline | home | 83 | 0.694740 |
| new_model | run_line | home | 82 | 0.734115 |
| new_model | total | over_resolved | 80 | 0.688056 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `496`; positive-EV candidates: `210`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045602` vs `-0.058347`.
- New-model positive-EV mean predicted EV vs realized return: `0.175328` vs `-0.160333`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.067600`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055149` vs `-0.058347`; EV/return Spearman `-0.045155`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994504`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `82`.
- Higher-EV side was `-1.5` in `25` games (`30.49%` of non-ties).
- Higher-EV side was `+1.5` in `57` games (`69.51%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
