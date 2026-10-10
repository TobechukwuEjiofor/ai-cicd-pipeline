import pandas as pd

print("Loading CSV... this may take a minute given the file size.")
df = pd.read_csv("final_research_dataset_MASTER.csv", low_memory=False)

print(f"\nShape: {df.shape[0]:,} rows, {df.shape[1]} columns")

print("\n--- Unique repos ---")
print(df['repo'].value_counts())

print("\n--- Class balance (conclusion) ---")
print(df['conclusion'].value_counts())
print(df['conclusion'].value_counts(normalize=True) * 100)

print("\n--- Null counts per column ---")
print(df.isnull().sum())

print("\n--- event column values ---")
print(df['event'].value_counts())
