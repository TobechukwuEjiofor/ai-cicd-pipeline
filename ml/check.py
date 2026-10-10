import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             precision_score, recall_score)

df = pd.read_csv("cleaned_build_data.csv", low_memory=False)
df = df.dropna(subset=["head_branch", "workflow_id"])
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at"])

# When did each run actually finish?
fallback = df["created_at"] + pd.to_timedelta(df["duration"].fillna(0), unit="s")
df["finished_at"] = df["updated_at"].fillna(fallback)
df["finished_at"] = df[["finished_at", "created_at"]].max(axis=1)
df = df.sort_values(["created_at", "run_id"]).reset_index(drop=True)

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
start_s = (df["created_at"] - EPOCH).dt.total_seconds().values
end_s = (df["finished_at"] - EPOCH).dt.total_seconds().values
failed = df["failed"].values

split = int(len(df) * 0.8)
y = df["failed"]
yt = y.iloc[split:]
train, test = df.iloc[:split], df.iloc[split:]

# ---------- CHECK 1: persistence baseline (no ML) ----------
prev = df.groupby("workflow_id")["failed"].shift(1)
pred_persist = prev.iloc[split:].fillna(0).astype(int)
print("=== CHECK 1: 'fails if the previous run of this workflow failed' (no ML) ===")
print(f"Failure precision: {precision_score(yt, pred_persist):.2f}   recall: {recall_score(yt, pred_persist):.2f}")

# ---------- CHECK 2: how concentrated are the failures? ----------
fails = test[test["failed"] == 1]
by_wf = fails.groupby("workflow_id").size().sort_values(ascending=False)
rate = train.groupby("workflow_id")["failed"].agg(["mean", "size"])
chronic = set(rate[(rate["mean"] > 0.5) & (rate["size"] >= 10)].index)
print("\n=== CHECK 2: concentration of failures ===")
print(f"Test failures: {len(fails)} across {len(by_wf)} workflows ({test['workflow_id'].nunique()} active in test)")
print(f"Top 10 workflows account for {by_wf.head(10).sum() / by_wf.sum():.0%} of test failures")
print(f"'Chronic' workflows (>50% failure rate in training): {len(chronic)}")
print(f"Share of test failures from chronic workflows: {fails['workflow_id'].isin(chronic).mean():.0%}")

# ---------- CHECK 3: completion-aware history ----------
# For each run, only count earlier runs that had FINISHED before this run started.
def completion_aware(key):
    n = len(df)
    cnt = np.zeros(n)
    rt = np.full(n, np.nan)
    l5 = np.full(n, np.nan)
    for _, idx in df.groupby(key).indices.items():
        order = np.argsort(end_s[idx], kind="stable")
        fin_sorted = end_s[idx][order]
        cum = np.concatenate([[0], np.cumsum(failed[idx][order])])
        k = np.searchsorted(fin_sorted, start_s[idx], side="left")
        cnt[idx] = k
        rt[idx] = np.where(k > 0, cum[k] / np.maximum(k, 1), np.nan)
        lo = np.maximum(k - 5, 0)
        n5 = k - lo
        l5[idx] = np.where(n5 > 0, (cum[k] - cum[lo]) / np.maximum(n5, 1), np.nan)
    return cnt, rt, l5

for key, p in [("workflow_id", "wf"), ("repo", "repo")]:
    c, r, l = completion_aware(key)
    df[f"{p}_run_count"], df[f"{p}_hist_rate"], df[f"{p}_last5_rate"] = c, r, l

hist = ["wf_run_count", "wf_hist_rate", "wf_last5_rate",
        "repo_run_count", "repo_hist_rate", "repo_last5_rate"]
global_rate = y.iloc[:split].mean()
for c in hist:
    if not c.endswith("run_count"):
        df[c] = df[c].fillna(global_rate)

df["hour"] = df["created_at"].dt.hour
df["day_of_week"] = df["created_at"].dt.dayofweek
df["is_merge"] = df["is_merge"].astype(str).str.lower().map({"true": 1, "false": 0}).fillna(0)
base = ["additions", "deletions", "total_churn", "files_modified", "msg_len",
        "is_merge", "num_parents", "time_since_last_commit", "hour", "day_of_week"]

def run(name, feats):
    X = df[feats].astype(float)
    m = HistGradientBoostingClassifier(class_weight="balanced", random_state=42)
    m.fit(X.iloc[:split], y.iloc[:split])
    proba = m.predict_proba(X.iloc[split:])[:, 1]
    pred = (proba >= 0.5).astype(int)
    trans = ((yt == 1) & (prev.iloc[split:] == 0)).values
    print(f"\n--- {name} ---")
    print(f"ROC-AUC {roc_auc_score(yt, proba):.3f}   PR-AUC {average_precision_score(yt, proba):.3f}   (random ~ {yt.mean():.3f})")
    print(f"Failure precision {precision_score(yt, pred):.2f}   recall {recall_score(yt, pred):.2f}")
    print(f"Recall on NEW breakages (failure right after a pass): {pred[trans].mean():.2f}   [{trans.sum()} such failures]")

print("\n=== CHECK 3: history rebuilt from FINISHED runs only ===")
run("metadata + completion-aware history", base + hist)
run("completion-aware history only", hist)

print("\n=== CHECK 4: workflow's past failure rate alone, no model ===")
s = df["wf_hist_rate"].iloc[split:]
print(f"ROC-AUC {roc_auc_score(yt, s):.3f}   PR-AUC {average_precision_score(yt, s):.3f}")
