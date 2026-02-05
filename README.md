# Email Selection Tool

A tool for selecting and reviewing email threads for memory system evaluation.

## Setup

1. Clone the repository
2. Place your data files in the `data/` directory:
   - `threads_with_metadata.csv` - Email metadata
   - `threads.csv.gz` - Full email content

3. Prepare the email data:
   ```bash
   cd email_selector_ui
   python3 prepare_data.py
   ```

## Usage

### 1. Email Selection UI

Interactive UI for browsing and selecting emails from the full dataset.

```bash
cd email_selector_ui
python3 -m http.server 8888
```

Open **http://localhost:8888/index.html**

Features:
- Browse all emails with pagination
- Filter by Work/Personal
- Search emails
- Select/deselect emails for export
- Ignore list management (hide spam/newsletters)
- Export selected emails to JSON

### 2. Selected Emails Preview

Preview the final selected emails (after automated selection and cleaning).

```bash
cd email_selector_ui
python3 -m http.server 8888
```

Open **http://localhost:8888/preview.html**

Features:
- View all selected emails
- Filter by Work/Personal
- Filter by message count (1, 2, 3+)
- Search emails
- Click to view full email content in modal
- Navigate with arrow keys (← →)

## Scripts

| Script | Purpose |
|--------|---------|
| `prepare_data.py` | Convert CSV data to `emails.json` for the UI |
| `select_350_emails.py` | Automatically select emails with stratification |
| `clean_emails.py` | Clean email content (remove tracking URLs, etc.) |

## Selection Criteria

The automated selection (`select_350_emails.py`) applies:
- 200 work + 150 personal emails
- Only 2025 emails
- Max 20,000 characters per thread
- Max 10 emails per sender
- Message count stratification (50% 1-msg, 30% 2-msg, 20% 3+)
- Ignore list filtering (spam, newsletters, automated emails)

## Files

| File | Description |
|------|-------------|
| `ignore_list.json` | Senders/domains/patterns to filter out |
| `selected_350_emails.json` | Raw selected emails |
| `selected_350_emails_clean.json` | Cleaned selected emails (final output) |

## Output Format

Each email in the output JSON contains:
- `thread_id` - Unique identifier
- `subject` - Email subject
- `from` / `to` - Sender and recipients
- `time` - Timestamp
- `full_content` - Complete email thread content
- `personal_or_work` - Classification
- `num_memories` - Number of memories generated
- `headlines` - Memory headlines
