# MLB Run Model Comparison

- Generated: `2026-10-15T07:48:15.026406+00:00`
- Untouched chronological test period: `2026-09-12` through `2026-10-14`
- Test games: `78`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= DRatings for BOTH run sides, plus log loss <= DRatings for moneyline, run line, and totals on comparable held-out games.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.890703 | 1.950845 | NO |
| away | 2.163253 | 2.142361 | YES |

- Production artifacts changed: **NO**.

## Market probability promotion gate

| Market | Rows | DRatings log loss | Candidate log loss | Pass |
| --- | --- | --- | --- | --- |
| moneyline | 78 | 0.638197 | 0.674324 | NO |
| run_line | 77 | 0.696193 | 0.733122 | NO |
| total | 75 | 0.704525 | 0.715246 | NO |

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 78 | 2.251923 | 1.890703 | 4.149872 | 4.115385 |
| new_model | home | 78 | 2.322515 | 1.950845 | 4.510628 | 4.115385 |
| dratings | away | 78 | 2.301923 | 2.163253 | 3.947308 | 4.692308 |
| new_model | away | 78 | 2.316341 | 2.142361 | 4.189843 | 4.692308 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.251923` -> `2.322515`; Poisson deviance `1.890703` -> `1.950845`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.301923` -> `2.316341`; Poisson deviance `2.163253` -> `2.142361`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.090964 | NO | 0.857143 | NO | 8 |
| run_line | 0.166311 | NO | 0.880952 | NO | 8 |
| total | 0.115443 | NO | 0.802410 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 78 | 0.638197 |
| new_model | moneyline | home | 78 | 0.674324 |
| dratings | run_line | home | 77 | 0.696193 |
| new_model | run_line | home | 77 | 0.733122 |
| dratings | total | over_resolved | 75 | 0.704525 |
| new_model | total | over_resolved | 75 | 0.715246 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `466`; positive-EV candidates: `190`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046492` vs `-0.054206`.
- New-model positive-EV mean predicted EV vs realized return: `0.183915` vs `-0.173737`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.065577`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055117` vs `-0.054206`; EV/return Spearman `-0.058084`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994886`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `77`.
- Higher-EV side was `-1.5` in `23` games (`29.87%` of non-ties).
- Higher-EV side was `+1.5` in `54` games (`70.13%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
