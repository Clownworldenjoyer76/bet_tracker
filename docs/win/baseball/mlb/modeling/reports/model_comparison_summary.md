# MLB Run Model Comparison

- Generated: `2026-10-21T07:48:13.179941+00:00`
- Untouched chronological test period: `2026-09-16` through `2026-10-19`
- Test games: `76`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= DRatings for BOTH run sides, plus log loss <= DRatings for moneyline, run line, and totals on comparable held-out games.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.885082 | 1.969682 | NO |
| away | 1.889762 | 1.883022 | YES |

- Production artifacts changed: **NO**.

## Market probability promotion gate

| Market | Rows | DRatings log loss | Candidate log loss | Pass |
| --- | --- | --- | --- | --- |
| moneyline | 76 | 0.640233 | 0.667684 | NO |
| run_line | 75 | 0.716563 | 0.746630 | NO |
| total | 73 | 0.707511 | 0.724662 | NO |

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 76 | 2.222500 | 1.885082 | 4.120658 | 4.039474 |
| new_model | home | 76 | 2.310105 | 1.969682 | 4.539465 | 4.039474 |
| dratings | away | 76 | 2.114474 | 1.889762 | 3.856053 | 4.394737 |
| new_model | away | 76 | 2.152487 | 1.883022 | 4.176148 | 4.394737 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.222500` -> `2.310105`; Poisson deviance `1.885082` -> `1.969682`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.114474` -> `2.152487`; Poisson deviance `1.889762` -> `1.883022`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.151530 | NO | 0.885714 | NO | 6 |
| run_line | 0.216846 | NO | 0.500000 | NO | 8 |
| total | 0.128494 | NO | 0.880952 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 76 | 0.640233 |
| new_model | moneyline | home | 76 | 0.667684 |
| dratings | run_line | home | 75 | 0.716563 |
| new_model | run_line | home | 75 | 0.746630 |
| dratings | total | over_resolved | 73 | 0.707511 |
| new_model | total | over_resolved | 73 | 0.724662 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `454`; positive-EV candidates: `191`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046583` vs `-0.050903`.
- New-model positive-EV mean predicted EV vs realized return: `0.175983` vs `-0.137801`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.058933`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055378` vs `-0.050903`; EV/return Spearman `-0.090123`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994684`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `75`.
- Higher-EV side was `-1.5` in `22` games (`29.33%` of non-ties).
- Higher-EV side was `+1.5` in `53` games (`70.67%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
