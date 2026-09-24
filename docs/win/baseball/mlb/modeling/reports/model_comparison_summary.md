# MLB Run Model Comparison

- Generated: `2026-09-24T07:42:17.240510+00:00`
- Untouched chronological test period: `2026-08-28` through `2026-09-23`
- Test games: `90`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.032815 | 2.051602 | NO |
| away | 2.013166 | 2.010768 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 90 | 2.361333 | 2.032815 | 4.315556 | 4.677778 |
| new_model | home | 90 | 2.386334 | 2.051602 | 4.300251 | 4.677778 |
| dratings | away | 90 | 2.307778 | 2.013166 | 4.114444 | 4.588889 |
| new_model | away | 90 | 2.340909 | 2.010768 | 4.078278 | 4.588889 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.361333` -> `2.386334`; Poisson deviance `2.032815` -> `2.051602`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.307778` -> `2.340909`; Poisson deviance `2.013166` -> `2.010768`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.090160 | NO | 0.952381 | NO | 8 |
| run_line | 0.102616 | NO | 0.847577 | NO | 10 |
| total | 0.158763 | NO | -0.714286 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 90 | 0.646704 |
| dratings | run_line | home | 89 | 0.665154 |
| dratings | total | over_resolved | 86 | 0.706618 |
| new_model | moneyline | home | 90 | 0.649610 |
| new_model | run_line | home | 89 | 0.672030 |
| new_model | total | over_resolved | 86 | 0.758724 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `538`; positive-EV candidates: `232`.
- New-model all-candidate mean predicted EV vs realized return: `-0.047792` vs `-0.055186`.
- New-model positive-EV mean predicted EV vs realized return: `0.175205` vs `-0.002414`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.019126`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.053262` vs `-0.055186`; EV/return Spearman `-0.059104`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992589`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `89`.
- Higher-EV side was `-1.5` in `29` games (`32.58%` of non-ties).
- Higher-EV side was `+1.5` in `60` games (`67.42%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
