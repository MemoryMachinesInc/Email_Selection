#!/usr/bin/env python3
"""
Select 350 emails (150 personal, 200 work) from 2025 with:
- Max 10 emails per sender (contact diversity)
- Max 20K characters per thread
- Stratified by message count (1-msg, 2-msg, 3+msg)
"""

import json
import random
import re
from collections import defaultdict

# Configuration - Message count stratification
# 50% single-message, 30% 2-message, 20% 3+ message
WORK_TARGETS = {
    '1-msg': 100,    # 50% of 200
    '2-msg': 60,     # 30% of 200
    '3+msg': 40,     # 20% of 200
}

PERSONAL_TARGETS = {
    '1-msg': 75,     # 50% of 150
    '2-msg': 45,     # 30% of 150
    '3+msg': 30,     # 20% of 150
}

MAX_PER_SENDER = 10
MAX_CHARS = 20000  # 20K character limit

def load_ignore_list(path):
    """Load ignore list and return filter components."""
    with open(path, 'r') as f:
        ignore_list = json.load(f)
    
    ignored_senders = set(s.lower() for s in ignore_list.get("ignored_senders", []))
    ignored_domains = set(d.lower() for d in ignore_list.get("ignored_domains", []))
    ignored_patterns = [p.lower() for p in ignore_list.get("ignored_subject_patterns", [])]
    
    return ignored_senders, ignored_domains, ignored_patterns

def is_ignored(email, ignored_senders, ignored_domains, ignored_patterns):
    """Check if email should be ignored."""
    from_line = str(email.get('from', '')).lower()
    to_line = str(email.get('to', '')).lower()
    subject = str(email.get('subject', '')).lower()
    headlines = str(email.get('headlines', '')).lower()
    full_content = str(email.get('full_content', '')).lower()
    
    # Check senders
    for sender in ignored_senders:
        if sender in from_line or sender in to_line:
            return True
    
    # Check domains
    for domain in ignored_domains:
        if domain in from_line or domain in to_line:
            return True
    
    # Check subject patterns
    for pattern in ignored_patterns:
        if pattern in subject or pattern in headlines or pattern in full_content:
            return True
    
    return False

def get_year(email):
    """Extract year from email time field."""
    time_str = email.get('time', '')
    if time_str:
        try:
            return int(time_str[:4])
        except:
            pass
    return None

def count_messages(email):
    """Count number of messages in an email thread."""
    content = email.get('full_content', '')
    return len(re.findall(r'^Message \d+', content, re.MULTILINE))

def get_message_bucket(email):
    """Get message count bucket for stratification."""
    msg_count = count_messages(email)
    if msg_count == 1:
        return '1-msg'
    elif msg_count == 2:
        return '2-msg'
    elif msg_count >= 3:
        return '3+msg'
    return '1-msg'  # Default to 1-msg if can't determine

def extract_sender(email):
    """Extract primary sender email address from 'from' field."""
    from_field = str(email.get('from', '')).lower()
    match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
    if match:
        return match.group(0)
    return from_field[:50] if from_field else 'unknown'

def sample_with_global_sender_cap(emails, target_count, max_per_sender, global_sender_counts):
    """
    Sample emails respecting a global sender cap across all buckets.
    Updates global_sender_counts in place.
    """
    # Shuffle for randomness
    shuffled = emails.copy()
    random.shuffle(shuffled)
    
    selected = []
    for email in shuffled:
        if len(selected) >= target_count:
            break
        
        sender = extract_sender(email)
        if global_sender_counts[sender] < max_per_sender:
            selected.append(email)
            global_sender_counts[sender] += 1
    
    return selected

def select_emails_with_global_cap(emails, category, targets, global_sender_counts, total_target):
    """
    Select emails for a category (work/personal) using message count stratification.
    Applies global sender cap across all buckets and categories.
    If unable to fill buckets, fills remaining from 1-msg emails.
    """
    selected = []
    shortfall = 0
    
    for bucket, target in targets.items():
        # Filter to this message bucket
        bucket_emails = [e for e in emails if get_message_bucket(e) == bucket]
        
        # Sample with global sender cap
        sampled = sample_with_global_sender_cap(bucket_emails, target, MAX_PER_SENDER, global_sender_counts)
        selected.extend(sampled)
        
        bucket_shortfall = target - len(sampled)
        if bucket_shortfall > 0:
            shortfall += bucket_shortfall
        
        print(f"  {category} bucket {bucket}: target={target}, available={len(bucket_emails)}, selected={len(sampled)}")
    
    # If there's a shortfall, fill from 1-msg emails
    if shortfall > 0:
        print(f"  {category} shortfall: {shortfall}, filling from 1-msg...")
        # Get 1-msg emails not already selected
        selected_ids = set(e['thread_id'] for e in selected)
        remaining_1msg = [e for e in emails 
                         if get_message_bucket(e) == '1-msg' 
                         and e['thread_id'] not in selected_ids]
        
        # Sample additional 1-msg emails
        additional = sample_with_global_sender_cap(remaining_1msg, shortfall, MAX_PER_SENDER, global_sender_counts)
        selected.extend(additional)
        print(f"  {category} filled {len(additional)} additional 1-msg emails")
    
    return selected

def main():
    random.seed(42)  # For reproducibility
    
    # Load data
    print("Loading emails.json...")
    with open('emails.json', 'r') as f:
        emails = json.load(f)
    print(f"Total emails: {len(emails)}")
    
    # Load ignore list
    print("Loading ignore_list.json...")
    ignored_senders, ignored_domains, ignored_patterns = load_ignore_list('ignore_list.json')
    
    # Filter out ignored emails
    filtered = [e for e in emails if not is_ignored(e, ignored_senders, ignored_domains, ignored_patterns)]
    print(f"After ignore list: {len(filtered)}")
    
    # Filter to 2025 only
    filtered_2025 = [e for e in filtered if get_year(e) == 2025]
    print(f"2025 emails only: {len(filtered_2025)}")
    
    # Filter by max characters
    filtered_2025 = [e for e in filtered_2025 if len(e.get('full_content', '')) <= MAX_CHARS]
    print(f"After excluding >20K chars: {len(filtered_2025)}")
    
    # Split by category
    work_emails = [e for e in filtered_2025 if e.get('personal_or_work') == 'work']
    personal_emails = [e for e in filtered_2025 if e.get('personal_or_work') == 'personal']
    
    print(f"\nWork pool: {len(work_emails)}")
    print(f"Personal pool: {len(personal_emails)}")
    
    # Show message distribution in pool
    print("\nMessage distribution in pool:")
    for category, cat_emails in [("Work", work_emails), ("Personal", personal_emails)]:
        msg_1 = len([e for e in cat_emails if get_message_bucket(e) == '1-msg'])
        msg_2 = len([e for e in cat_emails if get_message_bucket(e) == '2-msg'])
        msg_3 = len([e for e in cat_emails if get_message_bucket(e) == '3+msg'])
        print(f"  {category}: 1-msg={msg_1}, 2-msg={msg_2}, 3+msg={msg_3}")
    
    # Global sender count tracker (shared across work and personal)
    global_sender_counts = defaultdict(int)
    
    # Select emails
    print("\n=== Selecting WORK emails (target: 200) ===")
    selected_work = select_emails_with_global_cap(work_emails, 'work', WORK_TARGETS, global_sender_counts, 200)
    
    print("\n=== Selecting PERSONAL emails (target: 150) ===")
    selected_personal = select_emails_with_global_cap(personal_emails, 'personal', PERSONAL_TARGETS, global_sender_counts, 150)
    
    # Combine
    all_selected = selected_work + selected_personal
    
    print(f"\n=== FINAL SELECTION ===")
    print(f"Work selected: {len(selected_work)}")
    print(f"Personal selected: {len(selected_personal)}")
    print(f"Total: {len(all_selected)}")
    
    # Verify message distribution
    print(f"\nMessage distribution check:")
    msg_1 = len([e for e in all_selected if get_message_bucket(e) == '1-msg'])
    msg_2 = len([e for e in all_selected if get_message_bucket(e) == '2-msg'])
    msg_3 = len([e for e in all_selected if get_message_bucket(e) == '3+msg'])
    print(f"  1-msg: {msg_1} (target: 175)")
    print(f"  2-msg: {msg_2} (target: 105)")
    print(f"  3+msg: {msg_3} (target: 70)")
    
    # Verify sender diversity
    sender_counts = defaultdict(int)
    for e in all_selected:
        sender = extract_sender(e)
        sender_counts[sender] += 1
    
    max_sender = max(sender_counts.values()) if sender_counts else 0
    print(f"\nSender diversity check:")
    print(f"  Unique senders: {len(sender_counts)}")
    print(f"  Max emails from single sender: {max_sender}")
    
    # Verify character limit
    max_chars = max(len(e.get('full_content', '')) for e in all_selected)
    print(f"\nCharacter limit check:")
    print(f"  Max chars in selection: {max_chars:,} (limit: {MAX_CHARS:,})")
    
    # Save thread IDs
    thread_ids = [e['thread_id'] for e in all_selected]
    with open('selected_350_thread_ids.txt', 'w') as f:
        f.write('\n'.join(thread_ids))
    print(f"\nSaved {len(thread_ids)} thread IDs to selected_350_thread_ids.txt")
    
    # Save full email data
    with open('selected_350_emails.json', 'w') as f:
        json.dump(all_selected, f, indent=2)
    print(f"Saved {len(all_selected)} emails to selected_350_emails.json")

if __name__ == '__main__':
    main()
