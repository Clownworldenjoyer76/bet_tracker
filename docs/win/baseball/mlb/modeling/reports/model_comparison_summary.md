# MLB Run Model Comparison

- Generated: `2026-09-01T10:14:29.477725+00:00`
- Untouched chronological test period: `2026-08-06` through `2026-08-31`
- Test games: `161`
- Model fitting/tuning performed by this evaluation script: `NO`
- Promotion status: `candidate_rejected`

## Production promotion gate

Candidate promotion requires mean Poisson deviance <= the DRatings baseline for BOTH home and away models.

| Side | DRatings baseline Poisson | Candidate Poisson | Candidate <= baseline |
| --- | --- | --- | --- |
| home | 2.234467 | 2.306361 | NO |
| away | 2.427501 | 2.420073 | YES |

- Production artifacts changed: **NO**.

## Run prediction metrics

| System | Side | Rows | MAE | Mean Poisson deviance | Mean predicted runs | Mean actual runs |
| --- | --- | --- | --- | --- | --- | --- |
| dratings | home | 161 | 2.342609 | 2.234467 | 4.344224 | 4.465839 |
| new_model | home | 161 | 2.399238 | 2.306361 | 4.244756 | 4.465839 |
| dratings | away | 161 | 2.439876 | 2.427501 | 4.174783 | 4.086957 |
| new_model | away | 161 | 2.471818 | 2.420073 | 4.336186 | 4.086957 |

### Run-prediction questions

- Does the new model improve home-run prediction error? **NO** (MAE `2.342609` -> `2.399238`; Poisson deviance `2.234467` -> `2.306361`).
- Does the new model improve away-run prediction error? **NO** (MAE `2.439876` -> `2.471818`; Poisson deviance `2.427501` -> `2.420073`).

## Probability calibration

Calibration YES/NO uses weighted expected calibration error (ECE) <= `0.05`. Totals use conditional win probability on resolved bets; pushes are excluded from the observed win-rate denominator.

| Market | New-model ECE | Calibrated | Predicted-vs-observed Spearman | Observed rate exactly non-decreasing | Populated bins |
| --- | --- | --- | --- | --- | --- |
| moneyline | 0.108706 | NO | 0.987879 | NO | 10 |
| run_line | 0.081678 | NO | 0.975758 | NO | 10 |
| total | 0.155742 | NO | 0.190476 | NO | 8 |

- Are predicted moneyline probabilities calibrated? **NO**.
- Are predicted run-line probabilities calibrated? **NO**.
- Are predicted total probabilities calibrated? **NO**.
- Does increasing predicted probability correspond to increasing observed win rate? Moneyline **NO**, run line **NO**, total **NO**. See Spearman values above for rank-direction strength.

## Probability log loss

| System | Market | Evaluation side | Rows | Log loss |
| --- | --- | --- | --- | --- |
| dratings | moneyline | home | 161 | 0.668954 |
| dratings | run_line | home | 161 | 0.690138 |
| dratings | total | over_resolved | 159 | 0.717340 |
| new_model | moneyline | home | 161 | 0.688421 |
| new_model | run_line | home | 161 | 0.692752 |
| new_model | total | over_resolved | 159 | 0.735298 |

## EV, realized return, and Kelly

- New-model priced candidates evaluated: `966`; positive-EV candidates: `446`.
- New-model all-candidate mean predicted EV vs realized return: `-0.045462` vs `-0.047422`.
- New-model positive-EV mean predicted EV vs realized return: `0.196621` vs `-0.029283`.
- Does higher predicted EV correspond to higher realized return? EV/return Spearman = `0.026297`. A positive value indicates higher EV tended to correspond to higher realized return in this test sample.
- Is positive EV overstated versus realized return? **YES** (defined here as mean realized return below mean predicted EV among positive-EV candidates).
- DRatings-run baseline all-candidate mean predicted EV vs realized return: `-0.048825` vs `-0.047422`; EV/return Spearman `-0.108654`.
- Does Kelly increase monotonically with actual model edge? Edge/Kelly-raw Spearman = `0.993925`; mean raw Kelly across ordered edge bins is non-decreasing: **YES** across `10` populated edge bins.

## Run-line side preference

- Games with both run-line sides priced/evaluated: `161`.
- Higher-EV side was `-1.5` in `57` games (`35.40%` of non-ties).
- Higher-EV side was `+1.5` in `104` games (`64.60%` of non-ties).
- Exact EV ties: `0`.

## Interpretation constraint

This report evaluates the candidate on the untouched test period only. The script does not refit, retune, or select hyperparameters from these results. Do not tune the model on this final test period after reviewing the report.
