# MLB Run Model Comparison

- Generated: `2026-09-27T11:46:06.732539+00:00`
- Untouched chronological test period: `2026-08-31` through `2026-09-26`
- Test games: `77`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.829146 | 2.128427 | NO |
| away | 2.400190 | 2.560048 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 77 | 2.209870 | 1.829146 | 4.301558 | 4.363636 |
| new_model | home | 77 | 2.382659 | 2.128427 | 4.433834 | 4.363636 |
| dratings | away | 77 | 2.657403 | 2.400190 | 4.084675 | 5.376623 |
| new_model | away | 77 | 2.698353 | 2.560048 | 3.781487 | 5.376623 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.209870` -> `2.382659`; Poisson deviance `1.829146` -> `2.128427`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.657403` -> `2.698353`; Poisson deviance `2.400190` -> `2.560048`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.249205 | NO | 0.431461 | NO | 10 |
| run_line | 0.234442 | NO | 0.481716 | NO | 10 |
| total | 0.214335 | NO | -0.634742 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 77 | 0.675670 |
| dratings | run_line | home | 76 | 0.695427 |
| dratings | total | over_resolved | 73 | 0.711361 |
| new_model | moneyline | home | 77 | 0.819802 |
| new_model | run_line | home | 76 | 0.791474 |
| new_model | total | over_resolved | 73 | 0.785168 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `460`; positive-EV candidates: `205`.
- New-model all-candidate mean predicted EV vs realized return: `-0.048403` vs `-0.049391`.
- New-model positive-EV mean predicted EV vs realized return: `0.252640` vs `-0.116390`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.135521`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.057440` vs `-0.049391`; EV/return Spearman `-0.159080`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992676`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `76`.
- Higher-EV side was `-1.5` in `30` games (`39.47%` of non-ties).
- Higher-EV side was `+1.5` in `46` games (`60.53%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
