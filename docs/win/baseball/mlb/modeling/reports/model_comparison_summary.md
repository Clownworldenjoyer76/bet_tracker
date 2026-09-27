# MLB Run Model Comparison

- Generated: `2026-09-27T07:43:10.077649+00:00`
- Untouched chronological test period: `2026-08-31` through `2026-09-26`
- Test games: `77`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.832894 | 2.085595 | NO |
| away | 2.370698 | 2.360136 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 77 | 2.213896 | 1.832894 | 4.303766 | 4.363636 |
| new_model | home | 77 | 2.355306 | 2.085595 | 4.458743 | 4.363636 |
| dratings | away | 77 | 2.650260 | 2.370698 | 4.090260 | 5.376623 |
| new_model | away | 77 | 2.622298 | 2.360136 | 4.016126 | 5.376623 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.213896` -> `2.355306`; Poisson deviance `1.832894` -> `2.085595`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.650260` -> `2.622298`; Poisson deviance `2.370698` -> `2.360136`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.180162 | NO | 0.620064 | NO | 10 |
| run_line | 0.209273 | NO | 0.467074 | NO | 8 |
| total | 0.198342 | NO | -0.826362 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 77 | 0.673977 |
| dratings | run_line | home | 76 | 0.682282 |
| dratings | total | over_resolved | 73 | 0.707923 |
| new_model | moneyline | home | 77 | 0.727773 |
| new_model | run_line | home | 76 | 0.725517 |
| new_model | total | over_resolved | 73 | 0.765794 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `460`; positive-EV candidates: `202`.
- New-model all-candidate mean predicted EV vs realized return: `-0.049352` vs `-0.051283`.
- New-model positive-EV mean predicted EV vs realized return: `0.201107` vs `-0.109604`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.082568`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.057441` vs `-0.051283`; EV/return Spearman `-0.127936`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992947`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `76`.
- Higher-EV side was `-1.5` in `29` games (`38.16%` of non-ties).
- Higher-EV side was `+1.5` in `47` games (`61.84%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
