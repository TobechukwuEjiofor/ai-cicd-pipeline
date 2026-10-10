import pandas as pd
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, average_precision_score)

# ---------- Load and prepare ----------
df = pd.read_csv("cleaned_build_data.csv", low_memory=False)
df = df.dropna(subset=["head_branch"])

df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at"]).sort_values("created_at").reset_index(drop=True)

# ---------- Feature engineering ----------
# Only things known BEFORE the build runs. No duration, no status, no updated_at.
df["hour"] = df["created_at"].dt.hour
df["day_of_week"] = df["created_at"].dt.dayofweek
df["is_default_branch"] = df["head_branch"].isin(["main", "master", "dev", "develop"]).astype(int)
df["is_merge"] = df["is_merge"].astype(str).str.lower().map({"true": 1, "false": 0}).fillna(0)

features = [
    "additions", "deletions", "total_churn", "files_modified",
    "msg_len", "is_merge", "num_parents", "time_since_last_commit",
    "hour", "day_of_week", "is_default_branch",
]
X = df[features].astype(float)
y = df["failed"]

# ---------- Time-based split ----------
split = int(len(df) * 0.8)
X_train, X_test = X.iloc[:split], X.iloc[split:]
y_train, y_test = y.iloc[:split], y.iloc[split:]

print(f"Train: {len(X_train):,} rows  ({df['created_at'].iloc[0].date()} -> {df['created_at'].iloc[split-1].date()})")
print(f"Test:  {len(X_test):,} rows  ({df['created_at'].iloc[split].date()} -> {df['created_at'].iloc[-1].date()})")
print(f"Failure rate  train: {y_train.mean():.1%}   test: {y_test.mean():.1%}")

def evaluate(name, model, X_te, y_te):
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    print(f"\n===== {name} =====")
    print(f"ROC-AUC: {roc_auc_score(y_te, proba):.3f}   PR-AUC: {average_precision_score(y_te, proba):.3f}   (random guess PR-AUC ~ {y_te.mean():.3f})")
    print("Confusion matrix [rows=actual, cols=predicted] (0=success, 1=failure):")
    print(confusion_matrix(y_te, pred))
    print(classification_report(y_te, pred, target_names=["success", "failure"], zero_division=0))

# ---------- Model 1: dummy baseline ----------
dummy = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
pred = dummy.predict(X_test)
print(f"\n===== Dummy (always predicts success) =====")
print(f"Accuracy: {(pred == y_test).mean():.1%}  <- looks great, catches ZERO failures")

# ---------- Model 2: logistic regression ----------
X_train_lr = X_train.copy(); X_test_lr = X_test.copy()
for col in ["additions", "deletions", "total_churn", "files_modified", "msg_len", "time_since_last_commit"]:
    X_train_lr[col] = np.log1p(X_train_lr[col].clip(lower=0))
    X_test_lr[col] = np.log1p(X_test_lr[col].clip(lower=0))
logreg = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
logreg.fit(X_train_lr, y_train)
evaluate("Logistic Regression", logreg, X_test_lr, y_test)

# ---------- Model 3: gradient boosting ----------
gb = HistGradientBoostingClassifier(class_weight="balanced", random_state=42)
gb.fit(X_train, y_train)
evaluate("Gradient Boosting", gb, X_test, y_test)
