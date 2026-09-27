# MLB Run Model Comparison

- Generated: `2026-09-27T15:13:49.536201+00:00`
- Untouched chronological test period: `2026-08-31` through `2026-09-26`
- Test games: `74`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.836980 | 1.996742 | NO |
| away | 2.351574 | 2.290010 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 74 | 2.223784 | 1.836980 | 4.305676 | 4.445946 |
| new_model | home | 74 | 2.295674 | 1.996742 | 4.428889 | 4.445946 |
| dratings | away | 74 | 2.604865 | 2.351574 | 4.069730 | 5.283784 |
| new_model | away | 74 | 2.560998 | 2.290010 | 3.866311 | 5.283784 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.223784` -> `2.295674`; Poisson deviance `1.836980` -> `1.996742`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.604865` -> `2.560998`; Poisson deviance `2.351574` -> `2.290010`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.189357 | NO | -0.200000 | NO | 10 |
| run_line | 0.226278 | NO | 0.343918 | NO | 10 |
| total | 0.184668 | NO | -0.289886 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 74 | 0.679064 |
| dratings | run_line | home | 72 | 0.684778 |
| dratings | total | over_resolved | 71 | 0.711222 |
| new_model | moneyline | home | 74 | 0.756446 |
| new_model | run_line | home | 72 | 0.747550 |
| new_model | total | over_resolved | 71 | 0.722507 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `440`; positive-EV candidates: `194`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046476` vs `-0.053841`.
- New-model positive-EV mean predicted EV vs realized return: `0.211361` vs `-0.091546`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.064492`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.057490` vs `-0.053841`; EV/return Spearman `-0.175847`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992457`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `72`.
- Higher-EV side was `-1.5` in `25` games (`34.72%` of non-ties).
- Higher-EV side was `+1.5` in `47` games (`65.28%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
