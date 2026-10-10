import pandas as pd

print("Loading CSV...")
df = pd.read_csv("final_research_dataset_MASTER.csv", low_memory=False)
print(f"Starting rows: {len(df):,}")

# Keep only push-triggered runs -- matches what our own pipeline logs,
# and these are the rows with real commit metadata attached.
df = df[df['event'] == 'push'].copy()
print(f"After filtering to push events: {len(df):,}")

# Drop rows with no outcome at all
df = df[df['conclusion'].notna()]
print(f"After dropping null conclusion: {len(df):,}")

# Collapse into a binary label. Ambiguous outcomes (skipped, cancelled,
# action_required) aren't real pass/fail signal, so we drop them rather
# than guess.
success_values = ['success', 'passed']
failure_values = ['failure', 'failed', 'errored', 'startup_failure']

df = df[df['conclusion'].isin(success_values + failure_values)].copy()
df['failed'] = df['conclusion'].isin(failure_values).astype(int)

print(f"After collapsing to binary and dropping ambiguous outcomes: {len(df):,}")
print("\n--- Final class balance ---")
print(df['failed'].value_counts())
print(df['failed'].value_counts(normalize=True) * 100)

print("\n--- Null counts on remaining columns (key features only) ---")
key_cols = ['msg_len', 'is_merge', 'num_parents', 'additions', 'deletions',
            'total_churn', 'files_modified', 'time_since_last_commit', 'head_branch']
print(df[key_cols].isnull().sum())

df.to_csv("cleaned_build_data.csv", index=False)
print("\nSaved cleaned_build_data.csv")
