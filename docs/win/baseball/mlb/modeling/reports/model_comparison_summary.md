# MLB Run Model Comparison

- Generated: `2026-09-15T07:41:56.385636+00:00`
- Untouched chronological test period: `2026-08-17` through `2026-09-14`
- Test games: `158`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.267828 | 2.373710 | NO |
| away | 2.549447 | 2.663727 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 158 | 2.375063 | 2.267828 | 4.343291 | 4.639241 |
| new_model | home | 158 | 2.458707 | 2.373710 | 4.300935 | 4.639241 |
| dratings | away | 158 | 2.566392 | 2.549447 | 4.137532 | 4.512658 |
| new_model | away | 158 | 2.627972 | 2.663727 | 3.977007 | 4.512658 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.375063` -> `2.458707`; Poisson deviance `2.267828` -> `2.373710`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.566392` -> `2.627972`; Poisson deviance `2.549447` -> `2.663727`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.108852 | NO | 0.890909 | NO | 10 |
| run_line | 0.146194 | NO | 0.006061 | NO | 10 |
| total | 0.158242 | NO | -0.756620 | NO | 10 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 158 | 0.660163 |
| dratings | run_line | home | 157 | 0.696644 |
| dratings | total | over_resolved | 154 | 0.720806 |
| new_model | moneyline | home | 158 | 0.714166 |
| new_model | run_line | home | 157 | 0.754639 |
| new_model | total | over_resolved | 154 | 0.775581 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `946`; positive-EV candidates: `421`.
- New-model all-candidate mean predicted EV vs realized return: `-0.046764` vs `-0.046987`.
- New-model positive-EV mean predicted EV vs realized return: `0.235532` vs `-0.077007`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.043466`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049600` vs `-0.046987`; EV/return Spearman `-0.110083`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.992679`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `157`.
- Higher-EV side was `-1.5` in `50` games (`31.85%` of non-ties).
- Higher-EV side was `+1.5` in `107` games (`68.15%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
