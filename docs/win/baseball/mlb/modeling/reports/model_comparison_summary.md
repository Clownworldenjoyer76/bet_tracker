# MLB Run Model Comparison

- Generated: `2026-09-28T19:44:03.711306+00:00`
- Untouched chronological test period: `2026-09-01` through `2026-09-27`
- Test games: `89`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.746458 | 1.938263 | NO |
| away | 2.131562 | 2.288762 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 89 | 2.142697 | 1.746458 | 4.317753 | 4.359551 |
| new_model | home | 89 | 2.244533 | 1.938263 | 4.415504 | 4.359551 |
| dratings | away | 89 | 2.425056 | 2.131562 | 4.100337 | 5.224719 |
| new_model | away | 89 | 2.512566 | 2.288762 | 3.844006 | 5.224719 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.142697` -> `2.244533`; Poisson deviance `1.746458` -> `1.938263`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.425056` -> `2.512566`; Poisson deviance `2.131562` -> `2.288762`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.154087 | NO | -0.078788 | NO | 10 |
| run_line | 0.236561 | NO | 0.437692 | NO | 10 |
| total | 0.170024 | NO | -0.571429 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 89 | 0.653344 |
| dratings | run_line | home | 87 | 0.697042 |
| dratings | total | over_resolved | 86 | 0.704906 |
| new_model | moneyline | home | 89 | 0.753666 |
| new_model | run_line | home | 87 | 0.794257 |
| new_model | total | over_resolved | 86 | 0.736890 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `530`; positive-EV candidates: `230`.
- New-model all-candidate mean predicted EV vs realized return: `-0.047539` vs `-0.056774`.
- New-model positive-EV mean predicted EV vs realized return: `0.225984` vs `-0.192435`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.144439`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.056740` vs `-0.056774`; EV/return Spearman `-0.121329`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993341`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `87`.
- Higher-EV side was `-1.5` in `33` games (`37.93%` of non-ties).
- Higher-EV side was `+1.5` in `54` games (`62.07%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
