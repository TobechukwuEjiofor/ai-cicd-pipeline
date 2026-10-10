# Self-Logging CI Pipeline + Build-Failure Prediction Experiment

A small Node.js API with a GitHub Actions pipeline that **records its own build history** on every push, plus an offline experiment on a public dataset asking: *can CI failures be predicted before a build runs?*

## Project status

| Part | Status |
|---|---|
| Task-manager API with auth, tasks and validation modules | Built |
| 14 automated tests (Jest + Supertest) | Built |
| GitHub Actions pipeline: install, test, report | Built and verified |
| Self-logging: every push appends a row to `build-history/build-log.csv` | Built and verified (pass and fail cases) |
| Failure-prediction experiment on a public dataset | Explored offline, findings below |
| Prediction wired into the pipeline | Not built |
| LLM pull-request summaries, anomaly detection, dashboard | Not built |

I scoped this project down on purpose. The original idea was a fully "AI-augmented" pipeline, but the data showed that the prediction idea was weaker than expected, and I chose to document that honestly rather than build features on top of it.

## How the pipeline works

On every push to `main`, `.github/workflows/ci.yml`:

1. Checks out the code (two commits deep, so a diff is possible) and installs dependencies with `npm ci`.
2. Records a start time, then runs the tests with `continue-on-error`, so a failing build can still be logged.
3. Calculates the build duration and the diff stats (files changed, lines added and deleted) between the commits GitHub reports for the push.
4. Runs `scripts/log-build.js`, which appends one row to the CSV.
5. Commits the CSV back to the repo with `[skip ci]` in the message, so the bot's commit does not trigger another run.
6. Fails the job if the tests failed. Logging happens regardless of the outcome, and the status stays honest.

Pull requests run the tests only. Logging and committing happen on pushes.

### Build log columns

`timestamp, day_of_week, hour_utc, files_changed_count, lines_added, lines_deleted, modules_touched, result, duration_seconds, commit_sha`

## Problems hit and how they were fixed

- **Infinite-loop risk.** A pipeline that commits to its own repo can trigger itself. Fixed with `[skip ci]` in the bot's commit message.
- **Wrong diff stats after merges.** `git diff HEAD~1 HEAD` compares against the wrong commit once merge commits appear, so my own code edits were logged as `other` with one line changed. Fixed by diffing the exact `before` and `after` SHAs from the push event.
- **Failure path untested.** I pushed a deliberately broken test to confirm a failing build is logged as `failure` and the job still shows red, then reverted it.
- **Local and remote history drifting apart.** The bot commits after every push, so a local `git push` is rejected unless you `git pull` first.

## The prediction experiment (`ml/`)

**Data:** GADFPD, a public dataset of GitHub Actions runs (Mendeley Data, DOI 10.17632/mggwn7rj9f.1). 303,079 raw rows across 654 repositories. After keeping push events and collapsing outcomes to pass/fail: **41,944 runs, 9.6% failures**.

**Method:** sorted by time, trained on the oldest 80% and tested on the newest 20%. A random split would let near-identical builds leak between train and test. Columns that are only known after a build finishes (`duration`, `status`, `updated_at`) were excluded.

| Features | Result |
|---|---|
| Commit metadata only (lines changed, files modified, message length, hour, day) | No better than a coin flip. ROC-AUC about 0.5. |
| Plus each workflow's past failure history | PR-AUC about 0.90 (random is 0.096). |
| History rebuilt using only runs that had already finished | PR-AUC 0.903. No hidden leakage found. |

**What this means:**

- Commit content did not predict failures in this data. All of the signal came from how the workflow had behaved before.
- A simple rule, "fail if the previous run of this workflow failed", gets 0.81 precision and 0.81 recall with no machine learning.
- A workflow's past failure rate alone scores PR-AUC 0.894, so the model adds only about 0.01.
- The model flags about 55% of new breakages (failures right after a pass), which the simple rule cannot catch. I did not measure how many false alarms that costs.

**Limits:** the test window is only 11 days. Ten workflows account for 83% of test failures. Results are indicative, not production-grade.

Raw and cleaned data files are not committed (they are about 190 MB). Download the dataset from the DOI above, then run `explore.py` and `clean.py` first.

## Repository layout

```
src/            Express app (routes, middleware)
tests/          Jest test suites
scripts/        log-build.js (appends to the build log)
build-history/  build-log.csv (written by the pipeline)
ml/             exploration, cleaning and training scripts
.github/workflows/ci.yml
```

## Run locally

```bash
npm install
npm test
npm start
```

## What I would do next

Wire a simple history-based risk score into the pipeline, collect more of my own build data first, and measure false alarms before calling it useful.