#!/usr/bin/env python3
"""
Clean email content for human readability by removing:
- Long tracking URLs (HubSpot, urldefense, etc.)
- Markdown image/link syntax with tracking URLs
- Duplicate content sections (after ---)
- Base64 attachment metadata
- Email signatures and boilerplate
"""

import json
import re

def clean_tracking_urls(text):
    """Replace long tracking URLs with simplified versions or remove them."""
    
    # Remove urldefense wrapped URLs - extract the actual URL if possible
    text = re.sub(
        r'https://urldefense\.com/v3/__([^_]+)__[^)}\s]*',
        r'\1',
        text
    )
    
    # Remove HubSpot tracking URLs entirely (NA and EU regions)
    text = re.sub(
        r'https://[a-zA-Z0-9-]+\.(?:na\d*|eu\d*)\.hubspotlinks\.com/[^\s)\]]+',
        '',
        text
    )
    
    # Remove editorial manager tracking URLs
    text = re.sub(
        r'https?://track\.editorialmanager\.com/[^\s)\]]+',
        '',
        text
    )
    
    # Remove HubSpot email tracking pixels
    text = re.sub(
        r'!\[.*?\]\(https://[^)]*hubspot[^)]*\)',
        '',
        text
    )
    
    # Remove generic tracking pixels
    text = re.sub(
        r'!\[\]\(http[^)]+\)',
        '',
        text
    )
    
    # Remove HubSpot preference center URLs
    text = re.sub(
        r'https://hs-\d+\.s\.hubspotemail\.net/[^\s)\]]+',
        '',
        text
    )
    
    # Remove HubSpot image hosting URLs
    text = re.sub(
        r'https://hs-\d+\.f\.hubspotemail\.net/[^\s)\]]+',
        '',
        text
    )
    
    # Remove airline tracking URLs (United, Delta, etc.)
    text = re.sub(r'https://click\.enews\.united\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https://click\.o\.delta\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https://view\.o\.delta\.com/[^\s)\]]+', '', text)
    
    # Remove generic click tracking URLs with long query strings
    text = re.sub(r'https://click\.[a-zA-Z0-9.-]+/[^\s)\]]*\?qs=[a-f0-9]{40,}[^\s)\]]*', '', text)
    text = re.sub(r'https://view\.[a-zA-Z0-9.-]+/[^\s)\]]*\?qs=[a-f0-9]{40,}[^\s)\]]*', '', text)
    
    # Remove URLs with very long hex/random strings (typical tracking URLs)
    text = re.sub(r'https?://[^\s]+[a-f0-9]{50,}[^\s]*', '', text)
    
    # Remove sendgrid/mailchimp/other email tracking
    text = re.sub(r'https?://[a-zA-Z0-9.-]*sendgrid[^\s)\]]+', '', text)
    text = re.sub(r'https?://[a-zA-Z0-9.-]*mailchimp[^\s)\]]+', '', text)
    text = re.sub(r'https?://[a-zA-Z0-9.-]*campaign-archive[^\s)\]]+', '', text)
    
    # IKEA, loyalty, and other retail tracking
    text = re.sub(r'https?://links\.loyalty\.email\.ikea\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https?://[a-zA-Z0-9.-]*\.email\.[a-zA-Z0-9.-]+/[^\s)\]]*[a-zA-Z0-9_-]{30,}[^\s)\]]*', '', text)
    
    # Generic email tracking patterns (long base64-like strings)
    text = re.sub(r'https?://[^\s]+/[a-zA-Z0-9_-]{40,}[~][^\s]*', '', text)
    
    # Newsletter/email tracking domains
    text = re.sub(r'https?://track\.wordsmarts\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https?://track\.recommendedreads\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https?://click\.mlsend\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https?://click\.hyatt\.com/[^\s)\]]+', '', text)
    text = re.sub(r'https?://mailchi\.mp/[^\s)\]]+', '', text)
    text = re.sub(r'https?://[a-zA-Z0-9.-]+\.list-manage\.com/[^\s)\]]+', '', text)  # Mailchimp list-manage
    text = re.sub(r'https?://click\.[a-zA-Z0-9.-]+\.com/[^\s)\]]+', '', text)  # Generic click.*.com
    text = re.sub(r'https?://track\.[a-zA-Z0-9.-]+\.com/[^\s)\]]+', '', text)  # Generic track.*.com
    text = re.sub(r'https?://ctrk\.[a-zA-Z0-9.-]+\.com/[^\s)\]]+', '', text)  # ctrk tracking
    
    # Clean LinkedIn URLs - remove tracking params but keep the base URL
    text = re.sub(
        r'(https://www\.linkedin\.com/comm/messaging/thread/[^?\s]+)\?[^\s)\]]+',
        r'\1',
        text
    )
    text = re.sub(
        r'(https://www\.linkedin\.com/[^?\s]{1,50})\?[^\s)\]]{80,}',
        r'\1',
        text
    )
    
    # Clean Outlook SafeLinks - these wrap real URLs
    text = re.sub(r'https://nam\d+\.safelinks\.protection\.outlook\.com/[^\s)\]]+', '[link]', text)
    
    return text

def clean_markdown_artifacts(text):
    """Clean up markdown artifacts that look ugly in plain text."""
    
    # Remove markdown images with just [image] or tracking URLs
    text = re.sub(r'!\[.*?\]\([^)]+\)', '', text)
    
    # Simplify markdown links - keep text, remove long URLs
    # [Click here](long-url) -> Click here
    text = re.sub(
        r'\[([^\]]+)\]\([^)]{80,}\)',  # Links with URLs > 80 chars
        r'\1',
        text
    )
    
    # Clean up links that are just [link]
    text = re.sub(r'\[link\]', '', text)
    
    # Remove empty markdown links
    text = re.sub(r'\[\s*\]\([^)]+\)', '', text)
    
    # Remove standalone parentheses with just spaces
    text = re.sub(r'\(\s*\)', '', text)
    
    # Clean up escaped characters
    text = text.replace('\\--', '--')
    text = text.replace('\\[', '[')
    text = text.replace('\\]', ']')
    
    # Clean up markdown headers that are just styling
    text = re.sub(r'^##\s+', '', text, flags=re.MULTILINE)
    
    # Remove CID image references
    text = re.sub(r'\[image: [^\]]+\]', '[Image]', text)
    text = re.sub(r'!\[[^\]]*\]\(cid:[^)]+\)', '[Image]', text)
    text = re.sub(r'\[cid:[^\]]+\]', '[Image]', text)  # Standalone CID refs
    
    return text

def remove_duplicate_content(text):
    """Remove duplicate content after --- separator, but preserve multi-message threads."""
    
    # Split by --- 
    parts = re.split(r'\n---\n', text)
    
    if len(parts) <= 1:
        return text
    
    # First pass: identify all message parts (parts that contain "Message X" headers)
    message_parts = []
    other_parts = []
    
    for i, part in enumerate(parts):
        stripped = part.strip()
        # Check if this part contains a Message header
        if re.search(r'^Message \d+', stripped, re.MULTILINE):
            message_parts.append(part)
        else:
            other_parts.append((i, part))
    
    # If we have message parts, just return those (they are the actual email content)
    if message_parts:
        return '\n\n'.join(message_parts)
    
    # Fallback: if no message headers found, use original logic for single-message emails
    # Keep the first substantive part
    first_part = parts[0].strip()
    return first_part

def remove_attachment_metadata(text):
    """Remove base64 attachment metadata blocks."""
    
    # Remove Content-Type/Content-Disposition blocks
    text = re.sub(
        r'Content-Type:\s*[^\n]+\nContent-Disposition:\s*[^\n]+\n(?:Content-Transfer-Encoding:\s*[^\n]+\n)?(?:Content-ID:\s*[^\n]+\n)?(?:X-Attachment-Id:\s*[^\n]+\n)?',
        '[Attachment]\n',
        text
    )
    
    # Remove standalone attachment metadata
    text = re.sub(r'X-Attachment-Id:\s*[^\n]+\n?', '', text)
    text = re.sub(r'Content-ID:\s*<[^>]+>\n?', '', text)
    
    return text

def clean_boilerplate(text):
    """Remove common email boilerplate."""
    
    # Remove confidentiality notices (keep only first occurrence)
    confidentiality_pattern = r'The information contained in this electronic message may be legally privileged.*?(?=\n\n|\n\*{3,}|\Z)'
    matches = list(re.finditer(confidentiality_pattern, text, flags=re.DOTALL | re.IGNORECASE))
    if len(matches) > 1:
        # Remove all but first
        for match in reversed(matches[1:]):
            text = text[:match.start()] + text[match.end():]
    
    # Remove repeated asterisk dividers
    text = re.sub(r'\n\*{3,}\n', '\n', text)
    
    # Remove "Please consider the environment" lines (keep first only)
    env_pattern = r'Please consider the environment before printing this e-mail'
    env_matches = list(re.finditer(env_pattern, text, flags=re.IGNORECASE))
    if len(env_matches) > 1:
        for match in reversed(env_matches[1:]):
            text = text[:match.start()] + text[match.end():]
    
    # Remove confidentiality notices
    text = re.sub(
        r'_?Notice of confidentiality:.*?(?=\n\n|\Z)',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove "In compliance with data protection" blocks
    text = re.sub(
        r'In compliance with data protection regulations.*?(?=\n\n|\Z)',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove unsubscribe/manage preferences lines
    text = re.sub(r'.*Unsubscribe.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*Manage preferences.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*Email preferences.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*Privacy policy.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*Contact us.*\|.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*View as a web page.*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*Download the latest.*app.*\n?', '', text, flags=re.IGNORECASE)
    
    # Remove Forbes Councils footer
    text = re.sub(r'Forbes Councils,\s*\d+[^\n]+\n?', '', text)
    
    # Remove airline/corporate footers
    text = re.sub(r'\(c\)\s*\d{4}\s+United Airlines.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'United Airlines,?\s+Inc\..*?(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'We do not monitor electronic replies.*?\n', '', text)
    
    # Remove mailto: links
    text = re.sub(r'\(mailto:[^)]+\)', '', text)
    
    # Remove [link] placeholders that are redundant
    text = re.sub(r'\(\[link\]\s*\)', '', text)
    text = re.sub(r'\[link\]\s*\(\[link\]\s*\)', '', text)
    text = re.sub(r'\[link\]\s*\n', '\n', text)
    text = re.sub(r'\[link\]', '', text)
    
    # Remove [image] placeholders
    text = re.sub(r'\[image\]', '', text)
    text = re.sub(r'\[Image\]', '', text)
    
    # Remove horizontal rules made of dashes or asterisks
    text = re.sub(r'\n\s*[-*]{3,}\s*\n', '\n\n', text)
    text = re.sub(r'\n\s*\* \* \*\s*\n', '\n\n', text)
    
    # Clean up HTML entities
    text = text.replace('&reg;', '®')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&rsaquo;', '›')
    text = text.replace('&lsaquo;', '‹')
    text = text.replace('&rsquo;', "'")
    text = text.replace('&lsquo;', "'")
    text = text.replace('&rdquo;', '"')
    text = text.replace('&ldquo;', '"')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('<sup>', '')
    text = text.replace('</sup>', '')
    text = text.replace('&trade;', '™')
    text = text.replace('&copy;', '©')
    text = text.replace('&mdash;', '—')
    text = text.replace('&ndash;', '–')
    text = text.replace('&hellip;', '...')
    text = text.replace('&bull;', '•')
    text = text.replace('&dagger;', '†')
    text = text.replace('&quot;', '"')
    text = text.replace('&apos;', "'")
    text = text.replace('&game;', '')  # remove broken entities
    text = text.replace('&lan;', '')
    text = text.replace('&logout;', '')
    
    return text

def clean_whitespace(text):
    """Clean up excessive whitespace."""
    
    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing whitespace on lines
    text = re.sub(r'[ \t]+\n', '\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove [...] placeholders that are on their own line
    text = re.sub(r'\n\s*\[\.\.\.\]\s*\n', '\n', text)
    
    # Clean up lines with just markdown artifacts
    text = re.sub(r'\n\s*\|?\s*\n', '\n', text)
    
    # Remove lines that are just pipes/tables with no content
    text = re.sub(r'\n\|[^|a-zA-Z0-9]*\|?\n', '\n', text)
    
    # Remove empty brackets and parentheses
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    
    # Remove long base64-like strings (>100 chars of alphanumeric)
    text = re.sub(r'[A-Za-z0-9+/=]{100,}', '[encoded content removed]', text)
    
    # Remove repeated underscores (email dividers)
    text = re.sub(r'_{10,}', '', text)
    
    # Clean up broken markdown link syntax
    text = re.sub(r'\]\(tel:[^)]+\)', '', text)
    text = re.sub(r'\]\(\n[^)]*\)', '', text)
    
    # Remove zero-width spaces and other invisible chars
    text = text.replace('\u200b', '')
    text = text.replace('\u200c', '')  # zero-width non-joiner
    text = text.replace('\u200d', '')  # zero-width joiner
    text = text.replace('\u202f', ' ')
    text = text.replace('\u00ad', '')  # soft hyphen
    text = text.replace('\ufeff', '')  # BOM
    
    # Remove email preview spacers (lines of just spaces/invisible chars)
    text = re.sub(r'\n[\s\u200c\u200b‌]+\n', '\n', text)
    text = re.sub(r'(‌\s*)+', '', text)  # Remove sequences of ‌ (visible entity)
    
    # Clean up \r\n to \n
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    return text

def clean_signatures(text):
    """Remove or simplify repeated email signatures."""
    
    # Common signature patterns to simplify
    # Keep first occurrence, remove duplicates
    
    # Gabriel Kreiman signature block
    sig_pattern = r'Gabriel Kreiman\s*\n(?:Professor\s*\n)?(?:Children\'s Hospital,?\s*)?(?:Harvard Medical School\s*\n)?(?:http://klab\.tch\.harvard\.edu/?\s*\n)?(?:https?://twitter\.com/gkreiman\s*\n)?(?:.*?Check out our new book.*?\n)?(?:.*?cambridge\.org.*?\n)?'
    
    # Find all signature occurrences
    sigs = list(re.finditer(sig_pattern, text, re.IGNORECASE))
    
    if len(sigs) > 1:
        # Keep only the first signature, remove the rest
        for sig in reversed(sigs[1:]):
            text = text[:sig.start()] + '\n-- Gabriel Kreiman\n' + text[sig.end():]
    
    return text

def simplify_quoted_replies(text):
    """Simplify quoted reply chains."""
    
    # Truncate long quote chains - keep first level of quotes
    lines = text.split('\n')
    result = []
    in_deep_quote = False
    quote_depth = 0
    
    for line in lines:
        # Count quote depth
        stripped = line.lstrip()
        current_depth = 0
        while stripped.startswith('>'):
            current_depth += 1
            stripped = stripped[1:].lstrip()
        
        # Keep first level of quotes, summarize deeper ones
        if current_depth <= 1:
            result.append(line)
            in_deep_quote = False
        elif not in_deep_quote:
            result.append('[Previous messages truncated]')
            in_deep_quote = True
    
    return '\n'.join(result)

def clean_html_tags(text):
    """Remove HTML tags and clean up HTML entities."""
    
    # Remove HTML anchor tags but keep link text
    text = re.sub(r'<a\s+[^>]*>([^<]*)</a>', r'\1', text, flags=re.IGNORECASE)
    
    # Remove image tags entirely
    text = re.sub(r'<img\s+[^>]*/?>', '', text, flags=re.IGNORECASE)
    
    # Remove other common HTML tags
    text = re.sub(r'</?(?:div|span|p|br|table|tr|td|th|tbody|thead|b|i|strong|em|u|font|center|style|script)[^>]*/?>', '', text, flags=re.IGNORECASE)
    
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up numeric HTML entities
    text = re.sub(r'&#8209;', '-', text)  # non-breaking hyphen
    text = re.sub(r'&#8211;', '–', text)  # en dash
    text = re.sub(r'&#8212;', '—', text)  # em dash
    text = re.sub(r'&#8217;', "'", text)  # right single quote
    text = re.sub(r'&#8220;', '"', text)  # left double quote
    text = re.sub(r'&#8221;', '"', text)  # right double quote
    text = re.sub(r'&#8230;', '...', text)  # ellipsis
    text = re.sub(r'&#\d+;', '', text)  # remove other numeric entities
    
    return text

def clean_email_content(content):
    """Apply all cleaning functions to email content."""
    
    text = content
    
    # Order matters - do these in sequence
    text = clean_tracking_urls(text)
    text = clean_html_tags(text)
    text = remove_attachment_metadata(text)
    text = clean_markdown_artifacts(text)
    text = remove_duplicate_content(text)
    text = clean_boilerplate(text)
    text = clean_signatures(text)
    text = simplify_quoted_replies(text)
    text = clean_whitespace(text)
    
    return text

def main():
    # Load emails
    print("Loading selected_350_emails.json...")
    with open('selected_350_emails.json', 'r') as f:
        emails = json.load(f)
    
    print(f"Cleaning {len(emails)} emails...")
    
    # Clean each email
    for email in emails:
        if 'full_content' in email:
            email['full_content'] = clean_email_content(email['full_content'])
    
    # Save cleaned emails (ensure_ascii=False keeps non-ASCII chars readable)
    with open('selected_350_emails_clean.json', 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    
    print("Saved to selected_350_emails_clean.json")
    
    # Show sample
    print("\n=== Sample cleaned email ===")
    sample = emails[1]['full_content'][:1000]
    print(sample)
    print("...")

if __name__ == '__main__':
    main()
