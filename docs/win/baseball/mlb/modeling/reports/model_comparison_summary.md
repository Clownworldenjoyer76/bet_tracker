# MLB Run Model Comparison

- Generated: `2026-10-04T11:10:48.745467+00:00`
- Untouched chronological test period: `2026-09-04` through `2026-10-03`
- Test games: `85`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.994126 | 2.092419 | NO |
| away | 2.006743 | 2.007135 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 85 | 2.294353 | 1.994126 | 4.303765 | 4.482353 |
| new_model | home | 85 | 2.366982 | 2.092419 | 4.573134 | 4.482353 |
| dratings | away | 85 | 2.218706 | 2.006743 | 4.014235 | 4.658824 |
| new_model | away | 85 | 2.273630 | 2.007135 | 4.054177 | 4.658824 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.294353` -> `2.366982`; Poisson deviance `1.994126` -> `2.092419`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.218706` -> `2.273630`; Poisson deviance `2.006743` -> `2.007135`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.110229 | NO | 0.809524 | NO | 8 |
| run_line | 0.198239 | NO | 0.380952 | NO | 8 |
| total | 0.119074 | NO | -0.285714 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 85 | 0.628937 |
| dratings | run_line | home | 83 | 0.693112 |
| dratings | total | over_resolved | 82 | 0.705035 |
| new_model | moneyline | home | 85 | 0.667127 |
| new_model | run_line | home | 83 | 0.726482 |
| new_model | total | over_resolved | 82 | 0.727596 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `506`; positive-EV candidates: `221`.
- New-model all-candidate mean predicted EV vs realized return: `-0.048323` vs `-0.057885`.
- New-model positive-EV mean predicted EV vs realized return: `0.188359` vs `-0.085385`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.030324`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.056154` vs `-0.057885`; EV/return Spearman `-0.059948`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992270`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `83`.
- Higher-EV side was `-1.5` in `30` games (`36.14%` of non-ties).
- Higher-EV side was `+1.5` in `53` games (`63.86%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
