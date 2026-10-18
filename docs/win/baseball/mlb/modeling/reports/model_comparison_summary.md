# MLB Run Model Comparison

- Generated: `2026-10-18T07:47:33.204150+00:00`
- Untouched chronological test period: `2026-09-13` through `2026-10-15`
- Test games: `79`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= DRatings for BOTH run sides, plus log loss <= DRatings for moneyline, run line, and totals on comparable held-out games.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.822886 | 1.868616 | NO |
| away | 1.913334 | 1.945305 | NO |

- Production artifacts changed: **NO**.

## Market probability promotion gate

| Market | Rows | DRatings log loss | Candidate log loss | Pass |
| --- | --- | --- | --- | --- |
| moneyline | 79 | 0.646013 | 0.687929 | NO |
| run_line | 78 | 0.689318 | 0.734696 | NO |
| total | 76 | 0.708143 | 0.708204 | NO |

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 79 | 2.199747 | 1.822886 | 4.149620 | 4.139241 |
| new_model | home | 79 | 2.257806 | 1.868616 | 4.507870 | 4.139241 |
| dratings | away | 79 | 2.154810 | 1.913334 | 3.918608 | 4.493671 |
| new_model | away | 79 | 2.155689 | 1.945305 | 3.955034 | 4.493671 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.199747` -> `2.257806`; Poisson deviance `1.822886` -> `1.868616`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.154810` -> `2.155689`; Poisson deviance `1.913334` -> `1.945305`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.093503 | NO | 0.915729 | NO | 8 |
| run_line | 0.184601 | NO | 0.915152 | NO | 10 |
| total | 0.096087 | NO | 0.634742 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 79 | 0.646013 |
| new_model | moneyline | home | 79 | 0.687929 |
| dratings | run_line | home | 78 | 0.689318 |
| new_model | run_line | home | 78 | 0.734696 |
| dratings | total | over_resolved | 76 | 0.708143 |
| new_model | total | over_resolved | 76 | 0.708204 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `472`; positive-EV candidates: `206`.
- New-model all-candidate mean predicted EV vs realized return: `-0.047643` vs `-0.054174`.
- New-model positive-EV mean predicted EV vs realized return: `0.218163` vs `-0.054806`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.002518`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055087` vs `-0.054174`; EV/return Spearman `-0.068953`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993070`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `78`.
- Higher-EV side was `-1.5` in `33` games (`42.31%` of non-ties).
- Higher-EV side was `+1.5` in `45` games (`57.69%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
