# MLB Run Model Comparison

- Generated: `2026-09-18T07:42:14.522567+00:00`
- Untouched chronological test period: `2026-08-20` through `2026-09-17`
- Test games: `125`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.072462 | 2.130329 | NO |
| away | 2.681971 | 2.988558 | NO |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 125 | 2.331600 | 2.072462 | 4.282960 | 4.424000 |
| new_model | home | 125 | 2.382015 | 2.130329 | 4.277050 | 4.424000 |
| dratings | away | 125 | 2.645760 | 2.681971 | 4.161120 | 4.688000 |
| new_model | away | 125 | 2.765334 | 2.988558 | 3.737167 | 4.688000 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.331600` -> `2.382015`; Poisson deviance `2.072462` -> `2.130329`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.645760` -> `2.765334`; Poisson deviance `2.681971` -> `2.988558`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.150392 | NO | 0.279637 | NO | 10 |
| run_line | 0.113454 | NO | 0.975758 | NO | 10 |
| total | 0.195649 | NO | -0.939394 | NO | 10 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 125 | 0.680859 |
| dratings | run_line | home | 124 | 0.682873 |
| dratings | total | over_resolved | 121 | 0.718361 |
| new_model | moneyline | home | 125 | 0.735708 |
| new_model | run_line | home | 124 | 0.709373 |
| new_model | total | over_resolved | 121 | 0.830298 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `748`; positive-EV candidates: `345`.
- New-model all-candidate mean predicted EV vs realized return: `-0.048635` vs `-0.043222`.
- New-model positive-EV mean predicted EV vs realized return: `0.240667` vs `-0.056841`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `-0.025399`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.049599` vs `-0.043222`; EV/return Spearman `-0.112612`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.991604`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `124`.
- Higher-EV side was `-1.5` in `39` games (`31.45%` of non-ties).
- Higher-EV side was `+1.5` in `85` games (`68.55%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
