# MLB Run Model Comparison

- Generated: `2026-09-03T07:41:32.228022+00:00`
- Untouched chronological test period: `2026-08-07` through `2026-09-02`
- Test games: `166`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.166619 | 2.177862 | NO |
| away | 2.516420 | 2.571575 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 166 | 2.297229 | 2.166619 | 4.331928 | 4.475904 |
| new_model | home | 166 | 2.313742 | 2.177862 | 4.357809 | 4.475904 |
| dratings | away | 166 | 2.517349 | 2.516420 | 4.174337 | 4.192771 |
| new_model | away | 166 | 2.556227 | 2.571575 | 4.275949 | 4.192771 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.297229` -> `2.313742`; Poisson deviance `2.166619` -> `2.177862`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.517349` -> `2.556227`; Poisson deviance `2.516420` -> `2.571575`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.091469 | NO | 0.091465 | NO | 10 |
| run_line | 0.078999 | NO | 0.952381 | NO | 8 |
| total | 0.135209 | NO | -0.845154 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 166 | 0.673382 |
| dratings | run_line | home | 166 | 0.688810 |
| dratings | total | over_resolved | 164 | 0.716065 |
| new_model | moneyline | home | 166 | 0.699194 |
| new_model | run_line | home | 166 | 0.688275 |
| new_model | total | over_resolved | 164 | 0.727503 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `996`; positive-EV candidates: `435`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045635` vs `-0.046416`.
- New-model positive-EV mean predicted EV vs realized return: `0.180875` vs `-0.024230`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.006177`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049121` vs `-0.046416`; EV/return Spearman `-0.108791`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993744`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `166`.
- Higher-EV side was `-1.5` in `49` games (`29.52%` of non-ties).
- Higher-EV side was `+1.5` in `117` games (`70.48%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
