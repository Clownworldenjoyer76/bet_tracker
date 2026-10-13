# MLB Run Model Comparison

- Generated: `2026-10-13T07:47:03.862343+00:00`
- Untouched chronological test period: `2026-09-11` through `2026-10-12`
- Test games: `79`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 1.880630 | 2.005548 | NO |
| away | 2.152126 | 2.119027 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 79 | 2.266835 | 1.880630 | 4.171139 | 4.253165 |
| new_model | home | 79 | 2.369844 | 2.005548 | 4.504571 | 4.253165 |
| dratings | away | 79 | 2.293165 | 2.152126 | 3.998734 | 4.708861 |
| new_model | away | 79 | 2.335778 | 2.119027 | 4.281506 | 4.708861 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.266835` -> `2.369844`; Poisson deviance `1.880630` -> `2.005548`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.293165` -> `2.335778`; Poisson deviance `2.152126` -> `2.119027`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.145073 | NO | 0.904762 | NO | 8 |
| run_line | 0.176170 | NO | 0.437692 | NO | 10 |
| total | 0.165606 | NO | 0.083834 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 79 | 0.631866 |
| dratings | run_line | home | 78 | 0.694337 |
| dratings | total | over_resolved | 76 | 0.709123 |
| new_model | moneyline | home | 79 | 0.680468 |
| new_model | run_line | home | 78 | 0.739259 |
| new_model | total | over_resolved | 76 | 0.729571 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `472`; positive-EV candidates: `200`.
- New-model all-candidate mean predicted EV vs realized return: `-0.044994` vs `-0.053347`.
- New-model positive-EV mean predicted EV vs realized return: `0.197646` vs `-0.033300`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.022762`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.054814` vs `-0.053347`; EV/return Spearman `-0.041591`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993694`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `78`.
- Higher-EV side was `-1.5` in `28` games (`35.90%` of non-ties).
- Higher-EV side was `+1.5` in `50` games (`64.10%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
