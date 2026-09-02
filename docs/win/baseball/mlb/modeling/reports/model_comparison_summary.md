# MLB Run Model Comparison

- Generated: `2026-09-02T07:41:44.625884+00:00`
- Untouched chronological test period: `2026-08-06` through `2026-09-01`
- Test games: `165`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.206038 | 2.255633 | NO |
| away | 2.490621 | 2.480754 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 165 | 2.326485 | 2.206038 | 4.341636 | 4.454545 |
| new_model | home | 165 | 2.346783 | 2.255633 | 4.235444 | 4.454545 |
| dratings | away | 165 | 2.492606 | 2.490621 | 4.185091 | 4.163636 |
| new_model | away | 165 | 2.525216 | 2.480754 | 4.342196 | 4.163636 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.326485` -> `2.346783`; Poisson deviance `2.206038` -> `2.255633`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.492606` -> `2.525216`; Poisson deviance `2.490621` -> `2.480754`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.092691 | NO | 0.963636 | NO | 10 |
| run_line | 0.109674 | NO | 0.963636 | NO | 10 |
| total | 0.142333 | NO | 0.083834 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 165 | 0.671011 |
| dratings | run_line | home | 165 | 0.691240 |
| dratings | total | over_resolved | 163 | 0.715965 |
| new_model | moneyline | home | 165 | 0.684687 |
| new_model | run_line | home | 165 | 0.689977 |
| new_model | total | over_resolved | 163 | 0.736921 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `990`; positive-EV candidates: `443`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045888` vs `-0.046434`.
- New-model positive-EV mean predicted EV vs realized return: `0.197891` vs `-0.011716`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.026634`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.048972` vs `-0.046434`; EV/return Spearman `-0.105705`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994881`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `165`.
- Higher-EV side was `-1.5` in `55` games (`33.33%` of non-ties).
- Higher-EV side was `+1.5` in `110` games (`66.67%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
