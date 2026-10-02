# MLB Run Model Comparison

- Generated: `2026-10-02T07:41:59.468236+00:00`
- Untouched chronological test period: `2026-09-03` through `2026-10-01`
- Test games: `84`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.907465 | 1.963484 | NO |
| away | 2.110792 | 2.137844 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 84 | 2.277619 | 1.907465 | 4.313095 | 4.535714 |
| new_model | home | 84 | 2.300566 | 1.963484 | 4.561804 | 4.535714 |
| dratings | away | 84 | 2.346786 | 2.110792 | 4.047976 | 4.880952 |
| new_model | away | 84 | 2.425807 | 2.137844 | 4.117280 | 4.880952 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.277619` -> `2.300566`; Poisson deviance `1.907465` -> `1.963484`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.346786` -> `2.425807`; Poisson deviance `2.110792` -> `2.137844`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.108235 | NO | 0.857143 | NO | 8 |
| run_line | 0.146396 | NO | 0.814593 | NO | 10 |
| total | 0.199352 | NO | -0.380952 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 84 | 0.634782 |
| dratings | run_line | home | 82 | 0.690887 |
| dratings | total | over_resolved | 81 | 0.708258 |
| new_model | moneyline | home | 84 | 0.665009 |
| new_model | run_line | home | 82 | 0.706476 |
| new_model | total | over_resolved | 81 | 0.719442 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `500`; positive-EV candidates: `220`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046539` vs `-0.057380`.
- New-model positive-EV mean predicted EV vs realized return: `0.197870` vs `-0.083864`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.008904`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.056765` vs `-0.057380`; EV/return Spearman `-0.067025`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992136`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `82`.
- Higher-EV side was `-1.5` in `27` games (`32.93%` of non-ties).
- Higher-EV side was `+1.5` in `55` games (`67.07%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
