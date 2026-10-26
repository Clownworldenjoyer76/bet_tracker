# MLB Run Model Comparison

- Generated: `2026-10-26T12:24:35.779287+00:00`
- Untouched chronological test period: `2026-09-18` through `2026-10-24`
- Test games: `74`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= DRatings for BOTH run sides, plus log loss <= DRatings for moneyline, run line, and totals on comparable held-out games.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.898979 | 2.019634 | NO |
| away | 1.907450 | 1.895549 | YES |

- Production artifacts changed: **NO**.

## Market probability promotion gate

| Market | Rows | DRatings log loss | Candidate log loss | Pass |
| --- | --- | --- | --- | --- |
| moneyline | 74 | 0.631539 | 0.674812 | NO |
| run_line | 73 | 0.712562 | 0.749702 | NO |
| total | 71 | 0.702772 | 0.733079 | NO |

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 74 | 2.217432 | 1.898979 | 4.093378 | 4.081081 |
| new_model | home | 74 | 2.343894 | 2.019634 | 4.488662 | 4.081081 |
| dratings | away | 74 | 2.107973 | 1.907450 | 3.784730 | 4.270270 |
| new_model | away | 74 | 2.114542 | 1.895549 | 4.013276 | 4.270270 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.217432` -> `2.343894`; Poisson deviance `1.898979` -> `2.019634`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.107973` -> `2.114542`; Poisson deviance `1.907450` -> `1.895549`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.107869 | NO | 0.857143 | NO | 8 |
| run_line | 0.171961 | NO | 0.467074 | NO | 8 |
| total | 0.153659 | NO | -0.238095 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 74 | 0.631539 |
| new_model | moneyline | home | 74 | 0.674812 |
| dratings | run_line | home | 73 | 0.712562 |
| new_model | run_line | home | 73 | 0.749702 |
| dratings | total | over_resolved | 71 | 0.702772 |
| new_model | total | over_resolved | 71 | 0.733079 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `442`; positive-EV candidates: `199`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045840` vs `-0.052602`.
- New-model positive-EV mean predicted EV vs realized return: `0.189092` vs `-0.105930`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.038392`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055400` vs `-0.052602`; EV/return Spearman `-0.070027`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992814`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `73`.
- Higher-EV side was `-1.5` in `32` games (`43.84%` of non-ties).
- Higher-EV side was `+1.5` in `41` games (`56.16%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
