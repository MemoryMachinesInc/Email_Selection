// Email Selector App

let emails = [];
let selections = {}; // thread_id -> 'kept' | 'discarded' | undefined
let ignoreList = { ignored_senders: [], ignored_domains: [] }; // From static file
let sessionIgnored = []; // Additional ignores added during session
let currentFilter = 'all';
let searchQuery = '';
let focusedIndex = -1;

// Pagination
const PAGE_SIZE = 50;
let currentPage = 0;

// Load emails from JSON
async function loadEmails() {
    try {
        // Load ignore list first
        try {
            const ignoreResponse = await fetch('ignore_list.json');
            ignoreList = await ignoreResponse.json();
            console.log('Loaded ignore list:', ignoreList.ignored_senders.length, 'senders,', ignoreList.ignored_domains.length, 'domains');
        } catch (e) {
            console.warn('Could not load ignore_list.json, using empty list');
            ignoreList = { ignored_senders: [], ignored_domains: [] };
        }
        
        const response = await fetch('emails.json');
        emails = await response.json();
        
        // Load saved selections from localStorage
        const saved = localStorage.getItem('emailSelections');
        if (saved) {
            selections = JSON.parse(saved);
        }
        
        // Load session ignored senders from localStorage
        const savedIgnored = localStorage.getItem('sessionIgnored');
        if (savedIgnored) {
            sessionIgnored = JSON.parse(savedIgnored);
        }
        
        renderEmails();
        updateStats();
        updateIgnoreListUI();
    } catch (error) {
        console.error('Error loading emails:', error);
        document.getElementById('emailList').innerHTML = `
            <div class="empty-state">
                <h2>Error loading emails</h2>
                <p>Make sure emails.json is in the same directory.</p>
                <p style="color: #999; margin-top: 10px;">${error.message}</p>
            </div>
        `;
    }
}

// Save selections to localStorage
function saveSelections() {
    localStorage.setItem('emailSelections', JSON.stringify(selections));
}

// Save session ignored senders to localStorage
function saveSessionIgnored() {
    localStorage.setItem('sessionIgnored', JSON.stringify(sessionIgnored));
    updateIgnoreListUI();
}

// Add sender to session ignore list
function ignoreSender(senderEmail) {
    if (!senderEmail) return;
    // Extract just the email address if it's in "Name <email>" format
    const emailMatch = senderEmail.match(/<([^>]+)>/);
    const email = emailMatch ? emailMatch[1] : senderEmail;
    
    if (!sessionIgnored.includes(email)) {
        sessionIgnored.push(email);
        saveSessionIgnored();
        renderEmails();
        updateStats();
        closeEmailModal(); // Close modal after ignoring
    }
}

// Remove sender from session ignore list
function unignoreSender(sender) {
    sessionIgnored = sessionIgnored.filter(s => s !== sender);
    saveSessionIgnored();
    renderEmails();
    updateStats();
}

// Clear all session ignored senders
function clearIgnoreList() {
    sessionIgnored = [];
    saveSessionIgnored();
    renderEmails();
    updateStats();
}

// Check if email should be ignored (checks both static file and session list)
function isIgnoredSender(email) {
    const fromLower = (email.from || '').toLowerCase();
    const toLower = (email.to || '').toLowerCase();
    const subjectLower = (email.subject || '').toLowerCase();
    const headlinesLower = (email.headlines || '').toLowerCase();
    const contentLower = (email.full_content || email.email_preview || '').toLowerCase().substring(0, 500);
    
    // Check static ignore list - subject patterns (like mailing list tags)
    for (const pattern of ignoreList.ignored_subject_patterns || []) {
        const patternLower = pattern.toLowerCase();
        if (subjectLower.includes(patternLower) || headlinesLower.includes(patternLower) || contentLower.includes(patternLower)) {
            return true;
        }
    }
    
    // Check static ignore list - senders
    for (const sender of ignoreList.ignored_senders || []) {
        const senderLower = sender.toLowerCase();
        if (fromLower.includes(senderLower) || toLower.includes(senderLower)) {
            return true;
        }
    }
    
    // Check static ignore list - domains
    for (const domain of ignoreList.ignored_domains || []) {
        const domainLower = domain.toLowerCase();
        if (fromLower.includes('@' + domainLower) || fromLower.includes('.' + domainLower) ||
            toLower.includes('@' + domainLower) || toLower.includes('.' + domainLower)) {
            return true;
        }
    }
    
    // Check session ignore list
    for (const sender of sessionIgnored) {
        const senderLower = sender.toLowerCase();
        if (fromLower.includes(senderLower) || toLower.includes(senderLower)) {
            return true;
        }
    }
    
    return false;
}

// Update the ignore list UI
function updateIgnoreListUI() {
    const container = document.getElementById('ignoreListContainer');
    if (!container) return;
    
    const staticCount = (ignoreList.ignored_senders?.length || 0) + (ignoreList.ignored_domains?.length || 0);
    const sessionCount = sessionIgnored.length;
    
    let html = '';
    
    // Show static file entries (not removable via UI)
    if (ignoreList.ignored_senders?.length > 0) {
        html += ignoreList.ignored_senders.map(sender => `
            <span class="ignore-tag static" title="From ignore_list.json">
                ${escapeHtml(sender)}
            </span>
        `).join('');
    }
    
    if (ignoreList.ignored_domains?.length > 0) {
        html += ignoreList.ignored_domains.map(domain => `
            <span class="ignore-tag static domain" title="Domain from ignore_list.json">
                @${escapeHtml(domain)}
            </span>
        `).join('');
    }
    
    // Show session entries (removable)
    if (sessionIgnored.length > 0) {
        html += sessionIgnored.map(sender => `
            <span class="ignore-tag session">
                ${escapeHtml(sender)}
                <button onclick="unignoreSender('${escapeHtml(sender)}')" title="Remove">&times;</button>
            </span>
        `).join('');
    }
    
    if (staticCount === 0 && sessionCount === 0) {
        container.innerHTML = '<span class="ignore-empty">No ignored senders</span>';
    } else {
        container.innerHTML = html;
    }
}

// Get filtered emails
function getFilteredEmails() {
    return emails.filter(email => {
        // Ignore list filter - always exclude ignored senders
        if (isIgnoredSender(email)) return false;
        
        // Status filter
        const status = selections[email.thread_id];
        if (currentFilter === 'pending' && status) return false;
        if (currentFilter === 'kept' && status !== 'kept') return false;
        if (currentFilter === 'discarded' && status !== 'discarded') return false;
        if (currentFilter === 'work' && email.personal_or_work !== 'work') return false;
        if (currentFilter === 'personal' && email.personal_or_work !== 'personal') return false;
        
        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            const headline = (email.headline || '').toLowerCase();
            const preview = (email.email_preview || '').toLowerCase();
            if (!headline.includes(query) && !preview.includes(query)) return false;
        }
        
        return true;
    });
}

// Render email list with pagination
function renderEmails() {
    const container = document.getElementById('emailList');
    const filtered = getFilteredEmails();
    
    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h2>No email threads found</h2>
                <p>Try adjusting your filters or search query.</p>
            </div>
        `;
        return;
    }
    
    // Pagination
    const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    currentPage = Math.min(currentPage, totalPages - 1);
    currentPage = Math.max(0, currentPage);
    
    const startIdx = currentPage * PAGE_SIZE;
    const endIdx = Math.min(startIdx + PAGE_SIZE, filtered.length);
    const pageEmails = filtered.slice(startIdx, endIdx);
    
    // Pagination controls
    const paginationHtml = `
        <div class="pagination">
            <button class="page-btn" onclick="goToPage(0)" ${currentPage === 0 ? 'disabled' : ''}>First</button>
            <button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 0 ? 'disabled' : ''}>← Prev</button>
            <span class="page-info">
                Page ${currentPage + 1} of ${totalPages} 
                <span class="page-range">(${startIdx + 1}-${endIdx} of ${filtered.length.toLocaleString()} threads)</span>
            </span>
            <button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>Next →</button>
            <button class="page-btn" onclick="goToPage(${totalPages - 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>Last</button>
        </div>
    `;
    
    const emailsHtml = pageEmails.map((email, index) => {
        const globalIndex = startIdx + index;
        const status = selections[email.thread_id] || '';
        const headline = parseHeadline(email.headlines);
        const fromDisplay = email.from || 'Unknown sender';
        const subjectDisplay = email.subject || headline;
        const timeDisplay = email.time ? formatTime(email.time) : '';
        
        // Thread indicator
        const isThread = email.num_memories > 1;
        const threadIndicator = isThread ? 
            `<span class="thread-indicator" title="${email.num_memories} messages in thread">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                </svg>
                ${email.num_memories}
            </span>` : '';
        
        return `
            <div class="email-item ${status}" data-index="${globalIndex}" data-thread-id="${email.thread_id}">
                <input type="checkbox" class="email-checkbox" ${status === 'kept' ? 'checked' : ''} 
                    onclick="toggleKeep('${email.thread_id}', event)">
                <span class="email-type ${email.personal_or_work}">${email.personal_or_work}</span>
                <button class="email-content" onclick="showDetail('${email.thread_id}')" title="Click to view details">
                    <div class="email-from">
                        ${escapeHtml(fromDisplay.substring(0, 40))}
                        ${threadIndicator}
                    </div>
                    <div class="email-headline">${escapeHtml(subjectDisplay)}</div>
                    <div class="email-preview">${escapeHtml(headline !== subjectDisplay ? headline : '')}</div>
                </button>
                <div class="email-meta">
                    <span class="email-time">${timeDisplay}</span>
                    <span class="email-memories">${email.num_memories} memor${email.num_memories === 1 ? 'y' : 'ies'}</span>
                </div>
                <div class="email-actions">
                    <button class="action-btn keep" onclick="setStatus('${email.thread_id}', 'kept')">Keep</button>
                    <button class="action-btn discard" onclick="setStatus('${email.thread_id}', 'discarded')">Skip</button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = paginationHtml + emailsHtml + paginationHtml;
}

// Go to specific page
function goToPage(page) {
    currentPage = page;
    renderEmails();
    window.scrollTo(0, 0);
}

// Format time for display
function formatTime(timeStr) {
    try {
        const date = new Date(timeStr);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return date.toLocaleDateString('en-US', { weekday: 'short' });
        if (diffDays < 365) return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
    } catch {
        return '';
    }
}

// Parse headline from JSON array string
function parseHeadline(headlines) {
    if (!headlines) return 'No headline';
    try {
        const arr = JSON.parse(headlines);
        return arr[0] || 'No headline';
    } catch {
        return headlines.replace(/[\[\]"]/g, '').split(',')[0] || 'No headline';
    }
}

// Extract preview from email content
function extractPreview(preview) {
    if (!preview) return '';
    // Get just the subject line or first meaningful line
    const lines = preview.split('\n').filter(l => l.trim());
    const subjectLine = lines.find(l => l.startsWith('Subject:'));
    if (subjectLine) {
        return subjectLine.replace('Subject:', '').trim();
    }
    return lines.slice(0, 2).join(' ').substring(0, 100);
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Set email status
function setStatus(threadId, status) {
    if (selections[threadId] === status) {
        delete selections[threadId]; // Toggle off
    } else {
        selections[threadId] = status;
    }
    saveSelections();
    renderEmails();
    updateStats();
}

// Toggle keep status
function toggleKeep(threadId, event) {
    event.stopPropagation();
    if (selections[threadId] === 'kept') {
        delete selections[threadId];
    } else {
        selections[threadId] = 'kept';
    }
    saveSelections();
    renderEmails();
    updateStats();
}

// Update statistics
function updateStats() {
    // Only count non-ignored emails
    const visibleEmails = emails.filter(e => !isIgnoredSender(e));
    
    let kept = 0, discarded = 0;
    for (const email of visibleEmails) {
        const status = selections[email.thread_id];
        if (status === 'kept') kept++;
        if (status === 'discarded') discarded++;
    }
    const pending = visibleEmails.length - kept - discarded;
    
    document.getElementById('totalCount').textContent = visibleEmails.length.toLocaleString();
    document.getElementById('keptCount').textContent = kept;
    document.getElementById('discardedCount').textContent = discarded;
    document.getElementById('pendingCount').textContent = pending.toLocaleString();
}

// Show email detail in modal
let currentDetailThreadId = null;

function showDetail(threadId) {
    const email = emails.find(e => e.thread_id === threadId);
    if (!email) return;
    
    currentDetailThreadId = threadId;
    
    // Parse headlines
    let headlines = [];
    try {
        headlines = JSON.parse(email.headlines);
    } catch {
        headlines = email.headlines ? [email.headlines] : [];
    }
    
    // Update modal content
    document.getElementById('modalType').textContent = email.personal_or_work;
    document.getElementById('modalType').className = 'modal-type ' + email.personal_or_work;
    document.getElementById('modalMemories').textContent = `${email.num_memories} memor${email.num_memories === 1 ? 'y' : 'ies'}`;
    document.getElementById('modalSubject').textContent = email.subject || parseHeadline(email.headlines);
    document.getElementById('modalFrom').textContent = email.from || 'Unknown';
    
    // Parse and display email thread content - use full_content if available
    const emailContent = document.getElementById('modalEmailContent');
    const contentToShow = email.full_content || email.email_preview || 'No email content available';
    emailContent.innerHTML = parseEmailThread(contentToShow);
    
    // Headlines/Memories list
    const headlinesList = document.getElementById('modalHeadlines');
    headlinesList.innerHTML = headlines.length > 0 
        ? headlines.map(h => `<li>${escapeHtml(h)}</li>`).join('')
        : '<li style="color: #999">No memories extracted</li>';
    
    // Reset to first tab
    switchModalTab('emails');
    
    // Update action buttons
    const status = selections[threadId];
    const keepBtn = document.getElementById('modalKeepBtn');
    const skipBtn = document.getElementById('modalSkipBtn');
    const nextBtn = document.getElementById('modalNextBtn');
    
    keepBtn.textContent = status === 'kept' ? '✓ Kept' : 'Keep This Thread';
    keepBtn.style.background = status === 'kept' ? '#81c784' : '#4caf50';
    keepBtn.onclick = () => {
        setStatus(threadId, 'kept');
        keepBtn.textContent = '✓ Kept';
        keepBtn.style.background = '#81c784';
    };
    
    skipBtn.onclick = () => {
        setStatus(threadId, 'discarded');
        moveToNextEmailInModal();
    };
    
    nextBtn.onclick = () => {
        moveToNextEmailInModal();
    };
    
    // Ignore sender button
    const ignoreBtn = document.getElementById('modalIgnoreBtn');
    ignoreBtn.onclick = () => {
        ignoreSender(email.from);
    };
    
    // Show modal
    const modal = document.getElementById('emailModal');
    modal.style.display = 'flex';
    modal.classList.add('active');
}

// Switch between modal tabs
function switchModalTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.modal-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    // Update tab content
    document.getElementById('tabEmails').classList.toggle('active', tabName === 'emails');
    document.getElementById('tabMemories').classList.toggle('active', tabName === 'memories');
}

// Parse email thread content into formatted HTML
function parseEmailThread(preview) {
    if (!preview) return '<div class="email-message"><div class="email-message-body">No email content available</div></div>';
    
    // Split by "Message X" pattern to separate multiple messages
    const messagePattern = /Message\s+\d+\s*\n/gi;
    const parts = preview.split(messagePattern);
    
    if (parts.length <= 1) {
        // Single message or no "Message X" markers
        return `<div class="email-message">${formatSingleMessage(preview)}</div>`;
    }
    
    // Multiple messages
    return parts.filter(p => p.trim()).map((msg, idx) => {
        return `<div class="email-message">
            <div class="email-message-number">Message ${idx + 1}</div>
            ${formatSingleMessage(msg)}
        </div>`;
    }).join('');
}

// Format a single email message
function formatSingleMessage(msg) {
    const lines = msg.split('\n');
    let fromLine = '', toLine = '', timeLine = '', subjectLine = '';
    let bodyStartIdx = 0;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('From:')) {
            fromLine = line.replace('From:', '').trim();
        } else if (line.startsWith('To:')) {
            toLine = line.replace('To:', '').trim();
        } else if (line.startsWith('Time:')) {
            timeLine = line.replace('Time:', '').trim();
        } else if (line.startsWith('Subject:')) {
            subjectLine = line.replace('Subject:', '').trim();
            bodyStartIdx = i + 1;
            // Skip empty lines after subject
            while (bodyStartIdx < lines.length && !lines[bodyStartIdx].trim()) {
                bodyStartIdx++;
            }
            break;
        }
    }
    
    const body = lines.slice(bodyStartIdx).join('\n').trim();
    
    return `
        <div class="email-message-header">
            <span class="email-message-from">${escapeHtml(fromLine || 'Unknown sender')}</span>
            <span class="email-message-date">${escapeHtml(timeLine)}</span>
        </div>
        ${toLine ? `<div class="email-message-to">To: ${escapeHtml(toLine)}</div>` : ''}
        ${subjectLine ? `<div class="email-message-subject">${escapeHtml(subjectLine)}</div>` : ''}
        <div class="email-message-body">${escapeHtml(body)}</div>
    `;
}

function moveToNextEmailInModal() {
    const filtered = getFilteredEmails();
    const currentIdx = filtered.findIndex(e => e.thread_id === currentDetailThreadId);
    if (currentIdx < filtered.length - 1) {
        const nextEmail = filtered[currentIdx + 1];
        if (nextEmail) {
            showDetail(nextEmail.thread_id);
            return;
        }
    }
    // No more emails, close modal
    closeEmailModal();
}

function closeEmailModal() {
    const modal = document.getElementById('emailModal');
    modal.classList.remove('active');
    modal.style.display = 'none';
    currentDetailThreadId = null;
}

// Close email modal on backdrop click
document.getElementById('emailModal').addEventListener('click', (e) => {
    if (e.target.id === 'emailModal') closeEmailModal();
});

// Keyboard shortcut to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeEmailModal();
        closeModal();
    }
});

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;
        
        // Handle type filters (work/personal) separately
        if (filter === 'work' || filter === 'personal') {
            if (currentFilter === filter) {
                currentFilter = 'all';
                btn.classList.remove('active');
            } else {
                document.querySelectorAll('.filter-btn[data-filter="work"], .filter-btn[data-filter="personal"]').forEach(b => b.classList.remove('active'));
                currentFilter = filter;
                btn.classList.add('active');
            }
        } else {
            // Status filters
            document.querySelectorAll('.filter-btn:not([data-filter="work"]):not([data-filter="personal"])').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = filter;
        }
        
        currentPage = 0; // Reset to first page on filter change
        renderEmails();
    });
});

// Search with debounce
let searchTimeout;
document.getElementById('searchBox').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchQuery = e.target.value;
        currentPage = 0; // Reset to first page on search
        renderEmails();
    }, 300);
});

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return; // Don't interfere with search
    
    const items = document.querySelectorAll('.email-item');
    if (items.length === 0) return;
    
    if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        focusedIndex = Math.min(focusedIndex + 1, items.length - 1);
        items[focusedIndex]?.scrollIntoView({ block: 'center' });
        items.forEach((item, i) => item.style.outline = i === focusedIndex ? '2px solid #1a73e8' : 'none');
    } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        focusedIndex = Math.max(focusedIndex - 1, 0);
        items[focusedIndex]?.scrollIntoView({ block: 'center' });
        items.forEach((item, i) => item.style.outline = i === focusedIndex ? '2px solid #1a73e8' : 'none');
    } else if (e.key === 'k' && e.shiftKey === false && focusedIndex >= 0) {
        // Keep is handled above with 'k'
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
        const threadId = items[focusedIndex].dataset.threadId;
        setStatus(threadId, 'kept');
    } else if (e.key === 'd' && focusedIndex >= 0) {
        const threadId = items[focusedIndex].dataset.threadId;
        setStatus(threadId, 'discarded');
    }
});

// Export
document.getElementById('exportBtn').addEventListener('click', () => {
    const keptEmails = emails.filter(e => selections[e.thread_id] === 'kept');
    
    const exportData = {
        total_selected: keptEmails.length,
        exported_at: new Date().toISOString(),
        thread_ids: keptEmails.map(e => e.thread_id),
        emails: keptEmails.map(e => ({
            thread_id: e.thread_id,
            personal_or_work: e.personal_or_work,
            num_memories: e.num_memories,
            from: e.from || '',
            to: e.to || '',
            subject: e.subject || '',
            time: e.time || '',
            headlines: e.headlines,  // Full JSON array of all headlines
            topics: e.topics,        // Topics JSON
            people: e.people,        // People JSON
            anchors: e.anchors || '',  // Anchors JSON (dates, events, entities)
            full_content: e.full_content || e.email_preview || ''  // Full email thread content
        }))
    };
    
    document.getElementById('exportData').textContent = JSON.stringify(exportData, null, 2);
    document.getElementById('exportModal').classList.add('active');
    
    // Also trigger download
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'selected_emails.json';
    a.click();
    URL.revokeObjectURL(url);
});

function closeModal() {
    document.getElementById('exportModal').classList.remove('active');
}

// Close modal on backdrop click
document.getElementById('exportModal').addEventListener('click', (e) => {
    if (e.target.id === 'exportModal') closeModal();
});

// Initialize
loadEmails();
