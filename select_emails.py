#!/usr/bin/env python3
"""
Select 300 emails from Gabriel Kreiman's email data for evaluation.
Strategy: Balanced work/personal mix with diversity across topics and time.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Load the threads data
data_dir = Path(__file__).parent / "data"
print("Loading threads_with_metadata.csv...")
df = pd.read_csv(data_dir / "threads_with_metadata.csv")

print(f"Total threads: {len(df)}")
print(f"\nDistribution by category:")
print(df['personal_or_work'].value_counts())

# Calculate target counts for balanced selection
total_target = 300
work_count = (df['personal_or_work'] == 'work').sum()
personal_count = (df['personal_or_work'] == 'personal').sum()
total_count = work_count + personal_count

print(f"\nWork emails: {work_count} ({100*work_count/total_count:.1f}%)")
print(f"Personal emails: {personal_count} ({100*personal_count/total_count:.1f}%)")

# For balanced selection, aim for 50/50 or proportional
# Let's do 50/50 for true balance in evaluation
work_target = 150
personal_target = 150

print(f"\nTarget selection: {work_target} work, {personal_target} personal")

# Separate by category
work_df = df[df['personal_or_work'] == 'work'].copy()
personal_df = df[df['personal_or_work'] == 'personal'].copy()

# Add diversity score based on num_memories (prefer threads with more content)
# But also include some simpler ones for variety
def sample_with_diversity(category_df, n_samples, category_name):
    """Sample with diversity across num_memories distribution."""
    if len(category_df) <= n_samples:
        return category_df
    
    # Stratify by num_memories: low (1), medium (2-5), high (6+)
    category_df = category_df.copy()
    category_df['mem_bucket'] = pd.cut(
        category_df['num_memories'], 
        bins=[0, 1, 5, float('inf')], 
        labels=['low', 'medium', 'high']
    )
    
    bucket_counts = category_df['mem_bucket'].value_counts()
    print(f"\n{category_name} memory buckets: {dict(bucket_counts)}")
    
    # Sample proportionally from each bucket
    sampled = []
    for bucket in ['low', 'medium', 'high']:
        bucket_df = category_df[category_df['mem_bucket'] == bucket]
        if len(bucket_df) == 0:
            continue
        # Proportional allocation
        bucket_n = max(1, int(n_samples * len(bucket_df) / len(category_df)))
        bucket_n = min(bucket_n, len(bucket_df))
        sampled.append(bucket_df.sample(n=bucket_n, random_state=42))
    
    result = pd.concat(sampled)
    
    # If we need more samples, randomly sample from remaining
    if len(result) < n_samples:
        remaining = category_df[~category_df['thread_id'].isin(result['thread_id'])]
        extra_n = min(n_samples - len(result), len(remaining))
        if extra_n > 0:
            result = pd.concat([result, remaining.sample(n=extra_n, random_state=43)])
    
    # If we have too many, trim
    if len(result) > n_samples:
        result = result.sample(n=n_samples, random_state=44)
    
    return result

# Sample from each category
work_sample = sample_with_diversity(work_df, work_target, "Work")
personal_sample = sample_with_diversity(personal_df, personal_target, "Personal")

# Combine
selected = pd.concat([work_sample, personal_sample])

print(f"\n--- Final Selection ---")
print(f"Total selected: {len(selected)}")
print(f"Work: {len(selected[selected['personal_or_work'] == 'work'])}")
print(f"Personal: {len(selected[selected['personal_or_work'] == 'personal'])}")

# Show distribution of num_memories in selection
print(f"\nNum memories distribution in selection:")
print(selected['num_memories'].describe())

# Save selected thread IDs
output_file = data_dir / "selected_300_threads.csv"
selected.to_csv(output_file, index=False)
print(f"\nSaved selection to: {output_file}")

# Also save just the thread IDs for easy reference
thread_ids_file = data_dir / "selected_300_thread_ids.txt"
selected['thread_id'].to_csv(thread_ids_file, index=False, header=False)
print(f"Saved thread IDs to: {thread_ids_file}")

# Show some example headlines from selection
print("\n--- Sample Headlines from Selection ---")
for idx, row in selected.head(10).iterrows():
    headlines = row['headlines'][:100] + "..." if len(str(row['headlines'])) > 100 else row['headlines']
    print(f"[{row['personal_or_work']}] {headlines}")
