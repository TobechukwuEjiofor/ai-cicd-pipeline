import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, average_precision_score)

df = pd.read_csv("cleaned_build_data.csv", low_memory=False)
df = df.dropna(subset=["head_branch", "workflow_id"])
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at"]).sort_values(["created_at", "run_id"]).reset_index(drop=True)

# ---------- Basic features (same as before) ----------
df["hour"] = df["created_at"].dt.hour
df["day_of_week"] = df["created_at"].dt.dayofweek
df["is_default_branch"] = df["head_branch"].isin(["main", "master", "dev", "develop"]).astype(int)
df["is_merge"] = df["is_merge"].astype(str).str.lower().map({"true": 1, "false": 0}).fillna(0)

# ---------- History features ----------
# Every one of these uses ONLY rows that come before the current row.
def add_history(df, key, prefix):
    g = df.groupby(key)["failed"]
    prior_fails = g.cumsum() - df["failed"]      # failures BEFORE this row
    prior_runs = g.cumcount()                     # runs BEFORE this row
    df[f"{prefix}_run_count"] = prior_runs
    df[f"{prefix}_hist_rate"] = prior_fails / prior_runs.replace(0, np.nan)
    df[f"{prefix}_last5_rate"] = g.transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    df[f"{prefix}_prev_failed"] = g.shift(1)

add_history(df, "workflow_id", "wf")
add_history(df, "repo", "repo")

base = ["additions", "deletions", "total_churn", "files_modified", "msg_len",
        "is_merge", "num_parents", "time_since_last_commit",
        "hour", "day_of_week", "is_default_branch"]
hist = ["wf_run_count", "wf_hist_rate", "wf_last5_rate", "wf_prev_failed",
        "repo_run_count", "repo_hist_rate", "repo_last5_rate", "repo_prev_failed"]

split = int(len(df) * 0.8)
global_rate = df["failed"].iloc[:split].mean()   # fill gaps using TRAIN data only
df[hist] = df[hist].astype(float)
for c in hist:
    if c.endswith("run_count"):
        continue
    df[c] = df[c].fillna(global_rate)

y = df["failed"]
print(f"Train: {split:,} rows   Test: {len(df)-split:,} rows   "
      f"Failure rate train {y.iloc[:split].mean():.1%} / test {y.iloc[split:].mean():.1%}")

def evaluate(name, model, X_tr, X_te):
    model.fit(X_tr, y.iloc[:split])
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    yt = y.iloc[split:]
    print(f"\n===== {name} =====")
    print(f"ROC-AUC: {roc_auc_score(yt, proba):.3f}   PR-AUC: {average_precision_score(yt, proba):.3f}   (random ~ {yt.mean():.3f})")
    print(confusion_matrix(yt, pred))
    print(classification_report(yt, pred, target_names=["success", "failure"], zero_division=0))
    return model

# Experiment A: commit metadata + history
feats = base + hist
X = df[feats].astype(float)
gb = evaluate("Gradient Boosting: metadata + history",
              HistGradientBoostingClassifier(class_weight="balanced", random_state=42),
              X.iloc[:split], X.iloc[split:])

# Experiment B: history only (does the commit metadata add anything?)
Xh = df[hist].astype(float)
evaluate("Gradient Boosting: history ONLY",
         HistGradientBoostingClassifier(class_weight="balanced", random_state=42),
         Xh.iloc[:split], Xh.iloc[split:])

# Which features did the model lean on? (permutation importance on the test set)
from sklearn.inspection import permutation_importance
r = permutation_importance(gb, X.iloc[split:], y.iloc[split:], scoring="average_precision",
                           n_repeats=3, random_state=42)
imp = pd.Series(r.importances_mean, index=feats).sort_values(ascending=False)
print("\n--- Feature importance (drop in PR-AUC when shuffled) ---")
print(imp.round(4))
