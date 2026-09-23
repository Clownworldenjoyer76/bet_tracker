# MLB Run Model Comparison

- Generated: `2026-09-23T15:28:00.634775+00:00`
- Untouched chronological test period: `2026-08-27` through `2026-09-22`
- Test games: `93`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.008376 | 2.034459 | NO |
| away | 2.241720 | 2.097979 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 93 | 2.343226 | 2.008376 | 4.277849 | 4.623656 |
| new_model | home | 93 | 2.369133 | 2.034459 | 4.287564 | 4.623656 |
| dratings | away | 93 | 2.436559 | 2.241720 | 4.098065 | 4.602151 |
| new_model | away | 93 | 2.415534 | 2.097979 | 4.266706 | 4.602151 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.343226` -> `2.369133`; Poisson deviance `2.008376` -> `2.034459`).
- Does the new model improve away-run prediction error? **YES** (MAE `2.436559` -> `2.415534`; Poisson deviance `2.241720` -> `2.097979`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.089951 | NO | 0.115856 | NO | 10 |
| run_line | 0.081761 | NO | 0.952381 | NO | 8 |
| total | 0.087331 | NO | -0.428571 | NO | 6 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 93 | 0.641990 |
| dratings | run_line | home | 92 | 0.665278 |
| dratings | total | over_resolved | 89 | 0.708222 |
| new_model | moneyline | home | 93 | 0.633109 |
| new_model | run_line | home | 92 | 0.656344 |
| new_model | total | over_resolved | 89 | 0.709480 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `556`; positive-EV candidates: `242`.
- New-model all-candidate mean predicted EV vs realized return: `-0.044859` vs `-0.055306`.
- New-model positive-EV mean predicted EV vs realized return: `0.154309` vs `0.048017`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.119270`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.052916` vs `-0.055306`; EV/return Spearman `-0.061957`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992130`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `92`.
- Higher-EV side was `-1.5` in `22` games (`23.91%` of non-ties).
- Higher-EV side was `+1.5` in `70` games (`76.09%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
