# MLB Run Model Comparison

- Generated: `2026-09-13T07:43:16.652619+00:00`
- Untouched chronological test period: `2026-08-16` through `2026-09-12`
- Test games: `155`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.292304 | 2.375657 | NO |
| away | 2.576881 | 2.657937 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 155 | 2.381161 | 2.292304 | 4.345161 | 4.580645 |
| new_model | home | 155 | 2.468381 | 2.375657 | 4.365275 | 4.580645 |
| dratings | away | 155 | 2.574387 | 2.576881 | 4.124452 | 4.458065 |
| new_model | away | 155 | 2.662364 | 2.657937 | 4.021062 | 4.458065 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.381161` -> `2.468381`; Poisson deviance `2.292304` -> `2.375657`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.574387` -> `2.662364`; Poisson deviance `2.576881` -> `2.657937`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.111843 | NO | 0.571431 | NO | 10 |
| run_line | 0.135521 | NO | -0.066667 | NO | 10 |
| total | 0.125541 | NO | -0.393939 | NO | 10 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 155 | 0.665049 |
| dratings | run_line | home | 154 | 0.697724 |
| dratings | total | over_resolved | 151 | 0.721286 |
| new_model | moneyline | home | 155 | 0.709451 |
| new_model | run_line | home | 154 | 0.739118 |
| new_model | total | over_resolved | 151 | 0.759111 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `928`; positive-EV candidates: `396`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046751` vs `-0.045819`.
- New-model positive-EV mean predicted EV vs realized return: `0.203419` vs `-0.023990`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.024298`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049598` vs `-0.045819`; EV/return Spearman `-0.119535`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.994252`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `154`.
- Higher-EV side was `-1.5` in `47` games (`30.52%` of non-ties).
- Higher-EV side was `+1.5` in `107` games (`69.48%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
