# MLB Run Model Comparison

- Generated: `2026-09-14T07:44:50.298714+00:00`
- Untouched chronological test period: `2026-08-17` through `2026-09-13`
- Test games: `155`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.284323 | 2.557263 | NO |
| away | 2.579715 | 2.602122 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 155 | 2.370194 | 2.284323 | 4.342710 | 4.593548 |
| new_model | home | 155 | 2.473652 | 2.557263 | 3.984479 | 4.593548 |
| dratings | away | 155 | 2.581226 | 2.579715 | 4.129871 | 4.477419 |
| new_model | away | 155 | 2.602423 | 2.602122 | 4.082697 | 4.477419 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.370194` -> `2.473652`; Poisson deviance `2.284323` -> `2.557263`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.581226` -> `2.602423`; Poisson deviance `2.579715` -> `2.602122`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.099151 | NO | 0.972649 | NO | 10 |
| run_line | 0.141592 | NO | 0.915152 | NO | 10 |
| total | 0.183586 | NO | 0.166667 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 155 | 0.662558 |
| dratings | run_line | home | 154 | 0.701037 |
| dratings | total | over_resolved | 151 | 0.720757 |
| new_model | moneyline | home | 155 | 0.699895 |
| new_model | run_line | home | 154 | 0.742789 |
| new_model | total | over_resolved | 151 | 0.774757 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `928`; positive-EV candidates: `423`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046221` vs `-0.045830`.
- New-model positive-EV mean predicted EV vs realized return: `0.238327` vs `-0.083381`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.017985`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049616` vs `-0.045830`; EV/return Spearman `-0.119858`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992389`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `154`.
- Higher-EV side was `-1.5` in `48` games (`31.17%` of non-ties).
- Higher-EV side was `+1.5` in `106` games (`68.83%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
