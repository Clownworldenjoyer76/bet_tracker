# MLB Run Model Comparison

- Generated: `2026-09-20T07:42:57.860090+00:00`
- Untouched chronological test period: `2026-08-25` through `2026-09-19`
- Test games: `113`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.974330 | 1.946629 | YES |
| away | 2.473225 | 2.605839 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 113 | 2.306372 | 1.974330 | 4.275575 | 4.584071 |
| new_model | home | 113 | 2.306231 | 1.946629 | 4.287071 | 4.584071 |
| dratings | away | 113 | 2.577876 | 2.473225 | 4.117168 | 4.610619 |
| new_model | away | 113 | 2.576083 | 2.605839 | 3.630946 | 4.610619 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **YES** (MAE `2.306372` -> `2.306231`; Poisson deviance `1.974330` -> `1.946629`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.577876` -> `2.576083`; Poisson deviance `2.473225` -> `2.605839`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.117951 | NO | 0.939394 | NO | 10 |
| run_line | 0.109106 | NO | 0.927273 | NO | 10 |
| total | 0.201896 | NO | -0.680854 | NO | 10 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 113 | 0.668683 |
| dratings | run_line | home | 112 | 0.666736 |
| dratings | total | over_resolved | 109 | 0.720138 |
| new_model | moneyline | home | 113 | 0.667489 |
| new_model | run_line | home | 112 | 0.674161 |
| new_model | total | over_resolved | 109 | 0.801288 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `676`; positive-EV candidates: `305`.
- New-model all-candidate mean predicted EV vs realized return: `-0.049409` vs `-0.050118`.
- New-model positive-EV mean predicted EV vs realized return: `0.243961` vs `-0.010951`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.046904`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.051189` vs `-0.050118`; EV/return Spearman `-0.104244`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993094`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `112`.
- Higher-EV side was `-1.5` in `38` games (`33.93%` of non-ties).
- Higher-EV side was `+1.5` in `74` games (`66.07%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
