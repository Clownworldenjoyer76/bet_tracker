# MLB Run Model Comparison

- Generated: `2026-09-22T07:43:11.166388+00:00`
- Untouched chronological test period: `2026-08-26` through `2026-09-21`
- Test games: `100`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.991923 | 1.978888 | YES |
| away | 2.383199 | 2.481549 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 100 | 2.338600 | 1.991923 | 4.265000 | 4.640000 |
| new_model | home | 100 | 2.343721 | 1.978888 | 4.292504 | 4.640000 |
| dratings | away | 100 | 2.488800 | 2.383199 | 4.097800 | 4.590000 |
| new_model | away | 100 | 2.548767 | 2.481549 | 3.902072 | 4.590000 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.338600` -> `2.343721`; Poisson deviance `1.991923` -> `1.978888`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.488800` -> `2.548767`; Poisson deviance `2.383199` -> `2.481549`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.085768 | NO | 0.951515 | NO | 10 |
| run_line | 0.118225 | NO | 0.954169 | NO | 10 |
| total | 0.186368 | NO | -0.976190 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 100 | 0.642185 |
| dratings | run_line | home | 99 | 0.682788 |
| dratings | total | over_resolved | 96 | 0.708598 |
| new_model | moneyline | home | 100 | 0.642829 |
| new_model | run_line | home | 99 | 0.681433 |
| new_model | total | over_resolved | 96 | 0.783331 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `598`; positive-EV candidates: `263`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045772` vs `-0.049247`.
- New-model positive-EV mean predicted EV vs realized return: `0.198988` vs `-0.052510`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.020834`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.051405` vs `-0.049247`; EV/return Spearman `-0.064221`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993480`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `99`.
- Higher-EV side was `-1.5` in `34` games (`34.34%` of non-ties).
- Higher-EV side was `+1.5` in `65` games (`65.66%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
