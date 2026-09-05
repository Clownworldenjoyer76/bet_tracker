# MLB Run Model Comparison

- Generated: `2026-09-05T07:42:27.937624+00:00`
- Untouched chronological test period: `2026-08-09` through `2026-09-04`
- Test games: `167`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.139488 | 2.119056 | YES |
| away | 2.528634 | 2.575115 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 167 | 2.278743 | 2.139488 | 4.350000 | 4.520958 |
| new_model | home | 167 | 2.282031 | 2.119056 | 4.279961 | 4.520958 |
| dratings | away | 167 | 2.519820 | 2.528634 | 4.149281 | 4.239521 |
| new_model | away | 167 | 2.584696 | 2.575115 | 4.255223 | 4.239521 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.278743` -> `2.282031`; Poisson deviance `2.139488` -> `2.119056`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.519820` -> `2.584696`; Poisson deviance `2.528634` -> `2.575115`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.080316 | NO | 0.809524 | NO | 8 |
| run_line | 0.088131 | NO | 0.634742 | NO | 8 |
| total | 0.112849 | NO | -0.443122 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 167 | 0.672196 |
| dratings | run_line | home | 167 | 0.694432 |
| dratings | total | over_resolved | 164 | 0.714605 |
| new_model | moneyline | home | 167 | 0.689880 |
| new_model | run_line | home | 167 | 0.692873 |
| new_model | total | over_resolved | 164 | 0.726625 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `1002`; positive-EV candidates: `440`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045677` vs `-0.046617`.
- New-model positive-EV mean predicted EV vs realized return: `0.157478` vs `-0.048364`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.011494`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049524` vs `-0.046617`; EV/return Spearman `-0.116918`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993202`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `167`.
- Higher-EV side was `-1.5` in `45` games (`26.95%` of non-ties).
- Higher-EV side was `+1.5` in `122` games (`73.05%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
