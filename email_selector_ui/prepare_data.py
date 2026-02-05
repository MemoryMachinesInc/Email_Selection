#!/usr/bin/env python3
"""Convert ALL email threads to JSON for the web UI, including FULL email content."""

import pandas as pd
import json
from pathlib import Path

# Paths
script_dir = Path(__file__).parent
data_dir = script_dir.parent / "data"
output_file = script_dir / "emails.json"

# Load metadata
print("Loading threads_with_metadata.csv...")
df_meta = pd.read_csv(data_dir / "threads_with_metadata.csv")
print(f"  Loaded {len(df_meta)} threads with metadata")

# Load full email content from threads.csv.gz
print("Loading threads.csv.gz (full email content)...")
df_content = pd.read_csv(data_dir / "threads.csv.gz", compression='gzip')
print(f"  Loaded {len(df_content)} threads with full content")

# Create a mapping from thread_id to full content
content_map = dict(zip(df_content['Thread ID'], df_content['Content']))
print(f"  Created content map with {len(content_map)} entries")

# Merge the data
print("\nMerging metadata with full content...")
df = df_meta.copy()

print(f"Total threads: {len(df)}")
print(f"  - Work: {(df['personal_or_work'] == 'work').sum()}")
print(f"  - Personal: {(df['personal_or_work'] == 'personal').sum()}")
print(f"  - Unknown: {(df['personal_or_work'] == 'unknown').sum()}")

# Convert to JSON-friendly format
emails = []
matched = 0
for _, row in df.iterrows():
    thread_id = row["thread_id"]
    
    # Get full content from the content map
    full_content = content_map.get(thread_id, "")
    if full_content:
        matched += 1
    
    # Parse headlines to get count
    try:
        headlines_list = json.loads(row["headlines"]) if pd.notna(row["headlines"]) else []
    except:
        headlines_list = []
    
    # Extract sender/recipient info from full content or preview
    content_for_parsing = full_content if full_content else (row.get("email_preview", "") or "")
    from_line = ""
    to_line = ""
    subject_line = ""
    time_line = ""
    
    for line in content_for_parsing.split("\n")[:20]:  # Check first 20 lines
        line = line.strip()
        if line.startswith("From:") and not from_line:
            from_line = line.replace("From:", "").strip()
        elif line.startswith("To:") and not to_line:
            to_line = line.replace("To:", "").strip()
        elif line.startswith("Subject:") and not subject_line:
            subject_line = line.replace("Subject:", "").strip()
        elif line.startswith("Time:") and not time_line:
            time_line = line.replace("Time:", "").strip()
    
    email = {
        "thread_id": thread_id,
        "num_memories": int(row["num_memories"]),
        "num_headlines": len(headlines_list),
        "headlines": row["headlines"],
        "topics": row.get("topics", "") or "",
        "people": row.get("people", "") or "",
        "anchors": row.get("anchors", "") or "",  # Temporal anchors/key entities
        "full_content": full_content,  # FULL EMAIL CONTENT
        "email_preview": row.get("email_preview", "") or "",
        "personal_or_work": row.get("personal_or_work", "unknown") or "unknown",
        "from": from_line,
        "to": to_line,
        "subject": subject_line,
        "time": time_line,
    }
    emails.append(email)

print(f"  Matched full content for {matched}/{len(emails)} threads")

# Sort by num_memories descending (most complex threads first) for easier review
emails.sort(key=lambda x: -x["num_memories"])

# Save to JSON
with open(output_file, "w") as f:
    json.dump(emails, f)

print(f"\nSaved {len(emails)} email threads to {output_file}")
print(f"File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
print("\nTo start the UI, run:")
print(f"  cd '{script_dir}'")
print("  python3 -m http.server 8080")
print("\nThen open: http://localhost:8080")
