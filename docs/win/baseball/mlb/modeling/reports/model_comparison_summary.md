# MLB Run Model Comparison

- Generated: `2026-09-17T07:41:35.383032+00:00`
- Untouched chronological test period: `2026-08-19` through `2026-09-16`
- Test games: `139`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.101268 | 2.140279 | NO |
| away | 2.550691 | 2.642052 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 139 | 2.300504 | 2.101268 | 4.312158 | 4.374101 |
| new_model | home | 139 | 2.329379 | 2.140279 | 4.357069 | 4.374101 |
| dratings | away | 139 | 2.576978 | 2.550691 | 4.150504 | 4.647482 |
| new_model | away | 139 | 2.635765 | 2.642052 | 3.982741 | 4.647482 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.300504` -> `2.329379`; Poisson deviance `2.101268` -> `2.140279`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.576978` -> `2.635765`; Poisson deviance `2.550691` -> `2.642052`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.107650 | NO | 0.321212 | NO | 10 |
| run_line | 0.119038 | NO | 0.583589 | NO | 10 |
| total | 0.133682 | NO | -0.811754 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 139 | 0.682968 |
| dratings | run_line | home | 138 | 0.681756 |
| dratings | total | over_resolved | 135 | 0.717188 |
| new_model | moneyline | home | 139 | 0.723208 |
| new_model | run_line | home | 138 | 0.701423 |
| new_model | total | over_resolved | 135 | 0.764357 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `832`; positive-EV candidates: `354`.
- New-model all-candidate mean predicted EV vs realized return: `-0.047499` vs `-0.044507`.
- New-model positive-EV mean predicted EV vs realized return: `0.211629` vs `-0.019746`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.008557`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049504` vs `-0.044507`; EV/return Spearman `-0.114732`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994254`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `138`.
- Higher-EV side was `-1.5` in `39` games (`28.26%` of non-ties).
- Higher-EV side was `+1.5` in `99` games (`71.74%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
