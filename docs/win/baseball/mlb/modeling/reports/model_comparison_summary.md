# MLB Run Model Comparison

- Generated: `2026-09-30T11:18:18.019985+00:00`
- Untouched chronological test period: `2026-09-01` through `2026-09-29`
- Test games: `89`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.789772 | 1.899814 | NO |
| away | 2.261457 | 2.442277 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 89 | 2.186517 | 1.789772 | 4.302697 | 4.438202 |
| new_model | home | 89 | 2.228894 | 1.899814 | 4.521947 | 4.438202 |
| dratings | away | 89 | 2.466742 | 2.261457 | 4.066067 | 5.134831 |
| new_model | away | 89 | 2.596737 | 2.442277 | 3.800909 | 5.134831 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.186517` -> `2.228894`; Poisson deviance `1.789772` -> `1.899814`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.466742` -> `2.596737`; Poisson deviance `2.261457` -> `2.442277`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.174033 | NO | 0.709091 | NO | 10 |
| run_line | 0.223490 | NO | 0.612121 | NO | 10 |
| total | 0.170132 | NO | -0.666667 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 89 | 0.650455 |
| dratings | run_line | home | 87 | 0.692985 |
| dratings | total | over_resolved | 86 | 0.709785 |
| new_model | moneyline | home | 89 | 0.747111 |
| new_model | run_line | home | 87 | 0.770421 |
| new_model | total | over_resolved | 86 | 0.727526 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `530`; positive-EV candidates: `234`.
- New-model all-candidate mean predicted EV vs realized return: `-0.048411` vs `-0.056472`.
- New-model positive-EV mean predicted EV vs realized return: `0.221199` vs `-0.158077`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.114079`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.056805` vs `-0.056472`; EV/return Spearman `-0.116821`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.991159`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `87`.
- Higher-EV side was `-1.5` in `34` games (`39.08%` of non-ties).
- Higher-EV side was `+1.5` in `53` games (`60.92%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
