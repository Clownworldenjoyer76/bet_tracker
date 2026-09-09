# MLB Run Model Comparison

- Generated: `2026-09-09T07:41:08.332054+00:00`
- Untouched chronological test period: `2026-08-12` through `2026-09-08`
- Test games: `159`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.152535 | 2.195841 | NO |
| away | 2.485670 | 2.415179 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 159 | 2.301069 | 2.152535 | 4.356038 | 4.515723 |
| new_model | home | 159 | 2.356981 | 2.195841 | 4.372372 | 4.515723 |
| dratings | away | 159 | 2.495786 | 2.485670 | 4.117673 | 4.314465 |
| new_model | away | 159 | 2.485069 | 2.415179 | 4.251949 | 4.314465 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.301069` -> `2.356981`; Poisson deviance `2.152535` -> `2.195841`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.495786` -> `2.485069`; Poisson deviance `2.485670` -> `2.415179`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.094945 | NO | 0.857143 | NO | 8 |
| run_line | 0.121255 | NO | 0.586837 | NO | 8 |
| total | 0.096889 | NO | -0.028571 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 159 | 0.669133 |
| dratings | run_line | home | 158 | 0.683654 |
| dratings | total | over_resolved | 155 | 0.719688 |
| new_model | moneyline | home | 159 | 0.683805 |
| new_model | run_line | home | 158 | 0.692203 |
| new_model | total | over_resolved | 155 | 0.720907 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `952`; positive-EV candidates: `417`.
- New-model all-candidate mean predicted EV vs realized return: `-0.043865` vs `-0.048529`.
- New-model positive-EV mean predicted EV vs realized return: `0.172054` vs `-0.008297`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.020279`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049544` vs `-0.048529`; EV/return Spearman `-0.110029`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993979`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `158`.
- Higher-EV side was `-1.5` in `37` games (`23.42%` of non-ties).
- Higher-EV side was `+1.5` in `121` games (`76.58%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
