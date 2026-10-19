# MLB Run Model Comparison

- Generated: `2026-10-19T07:47:34.215826+00:00`
- Untouched chronological test period: `2026-09-15` through `2026-10-18`
- Test games: `77`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= DRatings for BOTH run sides, plus log loss <= DRatings for moneyline, run line, and totals on comparable held-out games.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.872870 | 1.934670 | NO |
| away | 1.919549 | 1.917918 | YES |

- Production artifacts changed: **NO**.

## Market probability promotion gate

| Market | Rows | DRatings log loss | Candidate log loss | Pass |
| --- | --- | --- | --- | --- |
| moneyline | 77 | 0.652402 | 0.679415 | NO |
| run_line | 76 | 0.708543 | 0.732660 | NO |
| total | 74 | 0.709670 | 0.721559 | NO |

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 77 | 2.210390 | 1.872870 | 4.125714 | 3.948052 |
| new_model | home | 77 | 2.277674 | 1.934670 | 4.504926 | 3.948052 |
| dratings | away | 77 | 2.131688 | 1.919549 | 3.876623 | 4.363636 |
| new_model | away | 77 | 2.180395 | 1.917918 | 4.182335 | 4.363636 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.210390` -> `2.277674`; Poisson deviance `1.872870` -> `1.934670`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.131688` -> `2.180395`; Poisson deviance `1.919549` -> `1.917918`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.097367 | NO | 1.000000 | YES | 6 |
| run_line | 0.212246 | NO | 0.476190 | NO | 8 |
| total | 0.137835 | NO | 0.371429 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **YES**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 77 | 0.652402 |
| new_model | moneyline | home | 77 | 0.679415 |
| dratings | run_line | home | 76 | 0.708543 |
| new_model | run_line | home | 76 | 0.732660 |
| dratings | total | over_resolved | 74 | 0.709670 |
| new_model | total | over_resolved | 74 | 0.721559 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `460`; positive-EV candidates: `187`.
- New-model all-candidate mean predicted EV vs realized return: `-0.047508` vs `-0.050435`.
- New-model positive-EV mean predicted EV vs realized return: `0.182466` vs `-0.166952`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.055743`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.055344` vs `-0.050435`; EV/return Spearman `-0.105850`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994614`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `76`.
- Higher-EV side was `-1.5` in `28` games (`36.84%` of non-ties).
- Higher-EV side was `+1.5` in `48` games (`63.16%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
