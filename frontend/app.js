// A API roda em 127.0.0.1:8000. Quando a página é servida pela própria API (porta 8000), usa a mesma origem.
const BASE_URL = (window.location.port === '8000' && window.location.protocol.startsWith('http'))
    ? window.location.origin
    : 'http://127.0.0.1:8000';
const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws');

// Escapa conteúdo coletado das redes antes de inserir em innerHTML (evita XSS)
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

function safeHttpUrl(url, fallback = '#') {
    const value = String(url || '').trim();
    return /^https?:\/\//i.test(value) ? value : fallback;
}

async function readErrorDetail(response, fallback) {
    try {
        const data = await response.json();
        if (typeof data.detail === 'string') return data.detail;
        if (Array.isArray(data.detail) && data.detail.length) {
            return data.detail.map(d => (d.msg || '').replace(/^Value error, /, '')).join(' ');
        }
    } catch (e) {}
    return fallback;
}

async function fetchWithRetry(url, options = {}, maxRetries = 3, delayMs = 400) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, options);
            if (response.ok || attempt === maxRetries) {
                return response;
            }
        } catch (err) {
            if (attempt === maxRetries) {
                throw err;
            }
        }
        await new Promise(res => setTimeout(res, delayMs * attempt));
    }
}

let allBrands = {};
let lastDashboardData = null;
let currentRawFeedData = [];

// SECTION 1 - GLOBALS & THEME MANAGEMENT
function applyTheme(theme) {
    const isDark = theme === 'dark';
    if (isDark) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    try {
        localStorage.setItem('raspTheme', theme);
    } catch (e) {
        console.warn('localStorage indisponível:', e);
    }

    const themeIcon = document.getElementById('themeToggleIcon');
    if (themeIcon) {
        themeIcon.className = isDark ? 'fa-solid fa-sun text-amber-400 text-sm' : 'fa-solid fa-moon text-slate-600 text-sm';
    }

    // Os gráficos leem as cores das variáveis CSS do tema: basta redesenhar se o dashboard estiver aberto
    const dashTab = document.getElementById('tab-dashboard');
    if (dashTab && dashTab.classList.contains('active') && typeof currentRawFeedData !== 'undefined' && currentRawFeedData.length) {
        requestAnimationFrame(() => {
            applyAllDashboardFilters(false);
            renderReportHeader(lastDashboardData);
            renderWordCloud(currentWordCloudData, activeWordCloudFilter);
        });
    }
}

function initTheme() {
    let savedTheme = null;
    try {
        savedTheme = localStorage.getItem('raspTheme');
    } catch (e) {}

    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(prefersDark ? 'dark' : 'light');
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);
}
window.applyTheme = applyTheme;
window.initTheme = initTheme;
window.toggleTheme = toggleTheme;

function switchTab(tabId, el) {
    document.querySelectorAll('.tab-content').forEach(c => {
        c.classList.remove('active');
        c.style.display = 'none';
    });
    const target = document.getElementById(tabId);
    if (target) {
        target.classList.add('active');
        target.style.display = 'block';
    }
    
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.className = 'flex-1 sm:flex-initial flex items-center justify-center px-3.5 py-1.5 text-xs font-medium rounded-md text-slate-600 dark:text-[#A1A1AA] hover:text-slate-900 dark:hover:text-[#F4F4F6] hover:bg-[#E4DFD6]/60 dark:hover:bg-[#1E1E22] transition-all nav-btn whitespace-nowrap';
    });
    const activeBtn = el || document.querySelector(`button[onclick*="'${tabId}'"]`);
    if (activeBtn) {
        activeBtn.className = 'flex-1 sm:flex-initial flex items-center justify-center px-3.5 py-1.5 text-xs font-medium rounded-md bg-[#1D4ED8] dark:bg-[#1D4ED8] text-white shadow-none transition-all nav-btn whitespace-nowrap';
    }
    
    if (tabId === 'tab-dashboard') {
        loadDashboardData('', true);
    } else if (tabId === 'tab-schedule') {
        loadSchedules();
    } else if (tabId === 'tab-brands') {
        loadBrandsList();
    }
}
window.switchTab = switchTab;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    const btnThemeToggle = document.getElementById('btnThemeToggle');
    if (btnThemeToggle) {
        btnThemeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            toggleTheme();
        });
    }

    // Modals
    const btnAccounts = document.getElementById('btnAccounts');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const accountsModal = document.getElementById('accountsModal');

    if (btnAccounts && accountsModal) {
        btnAccounts.addEventListener('click', () => {
            accountsModal.classList.remove('hidden');
        });
    }
    
    if (btnCloseModal && accountsModal) {
        btnCloseModal.addEventListener('click', () => {
            accountsModal.classList.add('hidden');
        });
    }

    // Initialize all sections gracefully on cold start (isInitialLoad = true)
    loadAccounts(true);
    loadSchedules(true);
    loadBrandsList(true);
    setupBooleanEditor('keywordEditor');
    setupBooleanEditor('schKeywordEditor');

    // Initial load for dashboard if it's default
    const dashTab = document.getElementById('tab-dashboard');
    if (dashTab && dashTab.classList.contains('active')) {
        loadDashboardData('', true);
    }

    // Initialize Flatpickr Custom Date Pickers (Clicking icon opens popup; typing allowed directly)
    if (typeof flatpickr !== 'undefined') {
        const flatpickrOptions = {
            locale: "pt",
            dateFormat: "Y-m-d",
            altInput: true,
            altFormat: "d/m/Y",
            allowInput: true,
            clickOpens: false, // Typing is 100% fluid in text field; calendar opens only via icon button
            position: "auto", // Auto-adapts position based on viewport space
            static: false,
            monthSelectorType: "static",
            altInputClass: "bg-white dark:bg-[#161618] border border-slate-300 dark:border-[#323238] text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-[#1D4ED8]/20 focus:border-[#1D4ED8] transition-colors shadow-2xs block w-full text-sm rounded-md p-2.5 pr-20",
            onChange: function() {
                updateClearDateButtonsVisibility();
            },
            onValueUpdate: function() {
                updateClearDateButtonsVisibility();
            }
        };
        window.fpStart = flatpickr("#startDate", flatpickrOptions);
        window.fpEnd = flatpickr("#endDate", flatpickrOptions);

        document.getElementById('btnStartDatePicker')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (window.fpStart) window.fpStart.toggle();
        });

        document.getElementById('btnEndDatePicker')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (window.fpEnd) window.fpEnd.toggle();
        });

        // Listen for direct typing or value changes
        document.getElementById('startDate')?.addEventListener('input', updateClearDateButtonsVisibility);
        document.getElementById('endDate')?.addEventListener('input', updateClearDateButtonsVisibility);
        // Also listen on AltInputs generated by Flatpickr
        setTimeout(() => {
            document.querySelectorAll('.flatpickr-input').forEach(el => {
                el.addEventListener('input', updateClearDateButtonsVisibility);
                el.addEventListener('keyup', updateClearDateButtonsVisibility);
                el.addEventListener('change', updateClearDateButtonsVisibility);
            });
        }, 300);
    }

    document.getElementById('scrapeForm')?.addEventListener('submit', handleScrapeSubmit);
    document.getElementById('directPostForm')?.addEventListener('submit', handleDirectPostSubmit);
    document.getElementById('scheduleForm')?.addEventListener('submit', handleScheduleSubmit);
    document.getElementById('brandForm')?.addEventListener('submit', handleBrandSubmit);

    // Retoma o acompanhamento de uma extração em andamento (ex.: após recarregar a página)
    restoreActiveScrape();
    restoreActiveCommentsJob();
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !document.getElementById('commentsModal')?.classList.contains('hidden')) closeCommentsModal();
    });
});

function updateClearDateButtonsVisibility() {
    const startVal = document.getElementById('startDate')?.value || '';
    const endVal = document.getElementById('endDate')?.value || '';

    const btnClearStart = document.getElementById('btnClearStartDate');
    const btnClearEnd = document.getElementById('btnClearEndDate');
    const btnClearHeader = document.getElementById('btnClearDateHeader');

    if (btnClearStart) {
        if (startVal.trim()) {
            btnClearStart.classList.remove('hidden');
        } else {
            btnClearStart.classList.add('hidden');
        }
    }

    if (btnClearEnd) {
        if (endVal.trim()) {
            btnClearEnd.classList.remove('hidden');
        } else {
            btnClearEnd.classList.add('hidden');
        }
    }

    if (btnClearHeader) {
        if (startVal.trim() || endVal.trim()) {
            btnClearHeader.classList.remove('hidden');
        } else {
            btnClearHeader.classList.add('hidden');
        }
    }
}
window.updateClearDateButtonsVisibility = updateClearDateButtonsVisibility;

function clearSingleDate(id) {
    const el = document.getElementById(id);
    if (el) el.value = '';
    if (id === 'startDate' && window.fpStart) window.fpStart.clear();
    if (id === 'endDate' && window.fpEnd) window.fpEnd.clear();
    updateClearDateButtonsVisibility();
}
window.clearSingleDate = clearSingleDate;

function clearDateFilters(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    clearSingleDate('startDate');
    clearSingleDate('endDate');
    updateClearDateButtonsVisibility();
}
window.clearDateFilters = clearDateFilters;

// SECTION 2 - TOAST SYSTEM
let lastToastMessage = '';
let lastToastTime = 0;

function showToast(message, type = 'info') {
    const now = Date.now();
    // Anti-spam debounce: ignore identical messages within 3.5 seconds
    if (message === lastToastMessage && (now - lastToastTime) < 3500) {
        return;
    }
    lastToastMessage = message;
    lastToastTime = now;

    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    // Clear previous toasts so notifications never stack up
    toastContainer.innerHTML = '';

    const toast = document.createElement('div');
    toast.className = 'p-3.5 px-4 rounded-md shadow-lg text-white transition-all duration-300 flex items-center justify-between gap-3 text-xs font-semibold';
    
    if (type === 'success') {
        toast.classList.add('bg-emerald-600');
    } else if (type === 'error') {
        toast.classList.add('bg-rose-600');
    } else {
        toast.classList.add('bg-[#1D4ED8]');
    }

    toast.innerHTML = `
        <span>${escapeHtml(message)}</span>
        <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white transition-colors p-1">
            <i class="fa-solid fa-xmark text-sm"></i>
        </button>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getCaretCharacterOffsetWithin(element, getEnd = false) {
    let caretOffset = 0;
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
        try {
            const range = sel.getRangeAt(0);
            const preCaretRange = range.cloneRange();
            preCaretRange.selectNodeContents(element);
            const targetContainer = getEnd ? range.endContainer : range.startContainer;
            const targetOffset = getEnd ? range.endOffset : range.startOffset;
            preCaretRange.setEnd(targetContainer, targetOffset);
            caretOffset = preCaretRange.toString().replace(/\u00a0/g, ' ').length;
        } catch (err) {
            caretOffset = 0;
        }
    }
    return caretOffset;
}

// SECTION 3 - SMART BOOLEAN EDITOR
function insertToken(editorId, token) {
    const editor = document.getElementById(editorId);
    if (!editor) return;
    
    editor.focus();
    
    // Get raw plain text of editor (normalizing non-breaking spaces)
    let fullText = (editor.innerText || editor.textContent || '')
        .replace(/\u00a0/g, ' ')
        .replace(/[\r\n]+/g, ' ');

    const isQuoteToken = (token === '""' || token === '"');
    const isParenToken = (token === '()' || token === '(' || token === '( )');

    // 1. Get current selection / caret position in plain text
    let selStart = getCaretCharacterOffsetWithin(editor, false);
    let selEnd = getCaretCharacterOffsetWithin(editor, true);

    let selectedText = fullText.slice(selStart, selEnd);

    // 2. If no text selected, find word boundaries around caret
    if (selStart === selEnd && (isQuoteToken || isParenToken)) {
        const isWordChar = (ch) => ch && /[^\s()"]/.test(ch);
        
        let start = selStart;
        let end = selStart;
        
        // Expand left
        while (start > 0 && isWordChar(fullText[start - 1])) {
            start--;
        }
        // Expand right
        while (end < fullText.length && isWordChar(fullText[end])) {
            end++;
        }
        
        const wordAtCaret = fullText.slice(start, end).trim();
        const upperWord = wordAtCaret.toUpperCase();
        
        if (wordAtCaret.length > 0 && upperWord !== 'AND' && upperWord !== 'OR' && upperWord !== 'NOT') {
            selStart = start;
            selEnd = end;
            selectedText = wordAtCaret;
        }
    }

    // 3. Check if caret or target word is enclosed in quotes or parens in fullText
    let hasOuterQuotes = false;
    let hasOuterParens = false;

    if (selStart > 0 && selEnd < fullText.length) {
        if (fullText[selStart - 1] === '"' && fullText[selEnd] === '"') {
            hasOuterQuotes = true;
        }
        if (fullText[selStart - 1] === '(' && fullText[selEnd] === ')') {
            hasOuterParens = true;
        }
    }

    let replacement = token;
    let newCaretPos = selStart;

    if (isParenToken && hasOuterQuotes) {
        // Parentheses MUST ALWAYS be on the OUTSIDE of double quotes!
        // Expand selection to include the surrounding quotes so parens wrap OUTSIDE!
        selStart--;
        selEnd++;
        let innerText = fullText.slice(selStart + 1, selEnd - 1);
        let cleanWord = innerText.replace(/^"+|"+$/g, '').replace(/^\(|\)$/g, '');
        replacement = '("' + cleanWord + '")';
        newCaretPos = selStart + 2 + cleanWord.length; // Caret inside quotes
    } else if (isQuoteToken && hasOuterParens) {
        // If caret is inside empty () and user presses ", insert "" inside parens: ("")
        replacement = '""';
        newCaretPos = selStart + 1; // Caret inside ""
    } else if (selectedText.length > 0) {
        let cleanWord = selectedText.replace(/^"+|"+$/g, '').replace(/^\(|\)$/g, '');
        
        if (isQuoteToken) {
            replacement = '"' + cleanWord + '"';
            if (hasOuterQuotes) {
                selStart--;
                selEnd++;
            }
            newCaretPos = selStart + replacement.length;
        } else if (isParenToken) {
            replacement = '(' + cleanWord + ')';
            newCaretPos = selStart + replacement.length;
        }
    } else {
        if (isParenToken) {
            replacement = '()';
            newCaretPos = selStart + 1; // Caret inside ()
        } else if (isQuoteToken) {
            replacement = '""';
            newCaretPos = selStart + 1; // Caret inside ""
        } else {
            replacement = token;
            newCaretPos = selStart + replacement.length;
        }
    }

    // 4. Perform clean plain-text replacement
    const updatedText = fullText.slice(0, selStart) + replacement + fullText.slice(selEnd);

    // 5. Update editor innerText, re-highlight syntax, and restore exact caret position!
    editor.innerText = updatedText;
    highlightBooleanSyntax(editor);
    setSelectionRange(editor, newCaretPos);
}
window.insertToken = insertToken;

function setupBooleanEditor(editorId) {
    const editor = document.getElementById(editorId);
    if (!editor) return;

    editor.addEventListener('keydown', (e) => {
        if (e.key === '"') {
            e.preventDefault();
            insertToken(editorId, '""');
        } else if (e.key === '(') {
            e.preventDefault();
            insertToken(editorId, '()');
        }
    });

    editor.addEventListener('input', () => {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) return;
        const range = selection.getRangeAt(0);
        
        let currentPos = 0;
        try {
            const preCaretRange = range.cloneRange();
            preCaretRange.selectNodeContents(editor);
            preCaretRange.setEnd(range.endContainer, range.endOffset);
            currentPos = preCaretRange.toString().length;
        } catch (err) {
            currentPos = 0;
        }

        highlightBooleanSyntax(editor);

        if (currentPos > 0) {
            setSelectionRange(editor, currentPos);
        }
    });
}

function highlightBooleanSyntax(editor) {
    if (!editor) return;
    
    // Extract raw text, normalizing non-breaking spaces (\u00a0) inserted by Chrome/Edge
    let text = (editor.innerText || editor.textContent || '')
        .replace(/\u00a0/g, ' ')
        .replace(/[\r\n]+/g, ' ');

    text = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    let html = text
        .replace(/(?:"|&quot;)/g, '<span class="token-quote">&quot;</span>')
        .replace(/\bAND\b/gi, '<span class="token-and">AND</span>')
        .replace(/\bOR\b/gi, '<span class="token-or">OR</span>')
        .replace(/\bNOT\b/gi, '<span class="token-not">NOT</span>')
        .replace(/\(/g, '<span class="token-paren">(</span>')
        .replace(/\)/g, '<span class="token-paren">)</span>');

    editor.innerHTML = html;

    // Update live status badge and explanation box if available
    const statusEl = document.getElementById(editor.id + 'Status');
    if (statusEl) {
        const rawText = text.trim();
        const openParens = (rawText.match(/\(/g) || []).length;
        const closeParens = (rawText.match(/\)/g) || []).length;

        if (openParens !== closeParens) {
            statusEl.className = "text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1";
            statusEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-[10px]"></i> Parênteses (${openParens}/${closeParens})`;
        } else {
            statusEl.className = "text-[11px] font-semibold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1";
            statusEl.innerHTML = `<i class="fa-solid fa-check text-[10px]"></i> Sintaxe Válida`;
        }
    }

    const expTextEl = document.getElementById(editor.id + 'ExplanationText');
    if (expTextEl) {
        expTextEl.innerHTML = explainBooleanQuery(text);
    }
}

function explainBooleanQuery(rawText) {
    if (!rawText || !rawText.trim()) return "Digite sua busca inteligente. O assistente mostrará a interpretação em tempo real.";
    
    let text = rawText.trim();
    text = text.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ');
    
    const quoteMatches = text.match(/"/g);
    const hasUnclosedQuote = quoteMatches && (quoteMatches.length % 2 !== 0);
    
    const openP = (text.match(/\(/g) || []).length;
    const closeP = (text.match(/\)/g) || []).length;
    const unclosedP = openP !== closeP;
    
    const isAmbiguous = /\bOR\b/i.test(text) && /\bAND\b/i.test(text) && openP === 0;

    if (hasUnclosedQuote) {
        return `<span class="text-amber-700 font-semibold"><i class="fa-solid fa-triangle-exclamation"></i> Aspas não fechadas! Clique em "Auto-Corrigir Lógica" para fechar a frase exata.</span>`;
    }
    
    if (unclosedP) {
        return `<span class="text-amber-700 font-semibold"><i class="fa-solid fa-triangle-exclamation"></i> Parênteses desbalanceados (${openP}/${closeP}). Clique em "Auto-Corrigir Lógica" para ajustar.</span>`;
    }

    if (isAmbiguous) {
        return `<span class="text-[#1D4ED8] dark:text-[#60A5FA] font-semibold"><i class="fa-solid fa-circle-question"></i> Lógica ambígua! Clique em <b>"Auto-Corrigir Lógica"</b> para agrupar em <i>(Tema A OR Tema B) AND (Pessoa C OR Pessoa D)</i>.</span>`;
    }

    let readable = text
        .replace(/\bAND\b/gi, ' <b class="text-emerald-700">E</b> ')
        .replace(/\bOR\b/gi, ' <b class="text-amber-700">OU</b> ')
        .replace(/\bNOT\b/gi, ' <b class="text-rose-700">EXCETO</b> ');
    
    return `Buscando publicações contendo: ${readable}`;
}
window.explainBooleanQuery = explainBooleanQuery;

function autoFixBooleanQuery(editorId) {
    const editor = document.getElementById(editorId);
    if (!editor) return;
    
    let text = (editor.innerText || editor.textContent || '')
        .replace(/\u00a0/g, ' ')
        .replace(/[\r\n]+/g, ' ')
        .trim();
    
    if (!text) {
        showToast('O campo de busca está vazio.', 'info');
        return;
    }

    // 1. Fix unclosed quotes
    const quoteMatches = text.match(/"/g);
    if (quoteMatches && (quoteMatches.length % 2 !== 0)) {
        text += '"';
    }

    // 2. Fix consecutive operators
    text = text
        .replace(/\b(AND|OR|NOT)\s+(AND|OR)/gi, '$2')
        .replace(/\b(AND|OR)\s+(AND|OR)\b/gi, '$1')
        .replace(/\b(NOT)\s+(NOT)\b/gi, 'NOT');

    // 3. Remove leading or trailing operators
    text = text
        .replace(/^(AND|OR)\s+/gi, '')
        .replace(/\s+(AND|OR|NOT)$/gi, '');

    // 4. Fix parens balance
    let openP = (text.match(/\(/g) || []).length;
    let closeP = (text.match(/\)/g) || []).length;
    while (openP > closeP) {
        text += ')';
        closeP++;
    }
    while (closeP > openP && text.endsWith(')')) {
        text = text.slice(0, -1);
        closeP--;
    }

    // 5. Smart Grouping of unparenthesized mixed OR and AND (e.g. "publicidade OR agencia AND chagas OR vieira")
    const hasUnparenthesizedOr = /\bOR\b/i.test(text);
    const hasUnparenthesizedAnd = /\bAND\b/i.test(text);
    const hasNoParens = !/\(/.test(text) && !/\)/.test(text);

    if (hasUnparenthesizedOr && hasUnparenthesizedAnd && hasNoParens) {
        const andParts = text.split(/\bAND\b/i);
        const fixedParts = andParts.map(part => {
            const pTrim = part.trim();
            if (/\bOR\b/i.test(pTrim) && !pTrim.startsWith('(')) {
                return `(${pTrim})`;
            }
            return pTrim;
        });
        text = fixedParts.join(' AND ');
    }

    editor.innerText = text;
    highlightBooleanSyntax(editor);
    showToast('Lógica booleana corrigida e agrupada com sucesso!', 'success');
}
window.autoFixBooleanQuery = autoFixBooleanQuery;

// Helper to set caret position or text selection range in contenteditable smoothly
function setSelectionRange(el, startPos, endPos) {
    if (startPos < 0) return;
    if (endPos === undefined) endPos = startPos;
    
    const selection = window.getSelection();
    const range = document.createRange();
    
    let charIndex = 0;
    let nodeStack = [el];
    let node;
    let foundStart = false;
    let foundEnd = false;

    while ((!foundStart || !foundEnd) && (node = nodeStack.pop())) {
        if (node.nodeType === 3) { // Text node
            const nextCharIndex = charIndex + node.length;
            
            if (!foundStart && startPos >= charIndex && startPos <= nextCharIndex) {
                range.setStart(node, startPos - charIndex);
                foundStart = true;
            }
            if (!foundEnd && endPos >= charIndex && endPos <= nextCharIndex) {
                range.setEnd(node, endPos - charIndex);
                foundEnd = true;
            }
            charIndex = nextCharIndex;
        } else if (node.nodeType === 1) { // Element node
            for (let i = node.childNodes.length - 1; i >= 0; i--) {
                nodeStack.push(node.childNodes[i]);
            }
        }
    }
    
    if (foundStart) {
        if (!foundEnd) {
            range.setEnd(el, el.childNodes.length);
        }
        selection.removeAllRanges();
        selection.addRange(range);
    }
}

// SECTION 4 - LOCATION AUTOCOMPLETE (REMOVED)
function getNetworkIcon(network) {
    const icons = {
        'twitter': 'fa-x-twitter',
        'x': 'fa-x-twitter',
        'instagram': 'fa-instagram',
        'facebook': 'fa-facebook',
        'linkedin': 'fa-linkedin',
        'tiktok': 'fa-tiktok',
        'youtube': 'fa-youtube'
    };
    return icons[network] || 'fa-hashtag';
}

function getNetworkName(network) {
    const names = {
        'twitter': 'X (Twitter)',
        'x': 'X (Twitter)',
        'instagram': 'Instagram',
        'facebook': 'Facebook',
        'linkedin': 'LinkedIn',
        'tiktok': 'TikTok',
        'youtube': 'YouTube'
    };
    return names[network] || network;
}

async function loadAccounts(isInitialLoad = false) {
    try {
        let response;
        try {
            response = await fetchWithRetry(`${BASE_URL}/api/accounts`, {}, isInitialLoad ? 4 : 2, 350);
        } catch (fetchError) {
            console.warn('Falha de conexão com o servidor:', fetchError);
            if (!isInitialLoad) {
                showToast('O servidor backend parece estar offline ou inacessível.', 'error');
            }
            return;
        }

        if (!response.ok) {
            if (!isInitialLoad) {
                showToast(`Erro do servidor: ${response.status} ${response.statusText}`, 'error');
            }
            return;
        }

        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('Erro ao decodificar resposta JSON:', jsonError);
            if (!isInitialLoad) {
                showToast('Erro interno: O servidor enviou dados inválidos.', 'error');
            }
            return;
        }
        
        const accountsList = document.getElementById('accountList');
        if (!accountsList) {
            console.warn('Elemento accountList não encontrado no DOM.');
            return;
        }
        
        accountsList.innerHTML = '';
        
        if (!data || Object.keys(data).length === 0) {
            accountsList.innerHTML = '<div class="col-span-2 text-center text-gray-500 py-4">Nenhuma conta configurada.</div>';
            return;
        }

        for (const [network, info] of Object.entries(data)) {
            const card = document.createElement('div');
            card.className = 'border border-slate-200 dark:border-[#323238] rounded-md p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white dark:bg-[#161618]/90 shadow-2xs hover:border-slate-300 dark:hover:border-slate-700 transition-all';
            
            const isConnected = info.logged_in === true;
            const badgeColor = isConnected 
                ? 'bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border-emerald-200/80 dark:border-emerald-800' 
                : 'bg-rose-50 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border-rose-200/80 dark:border-rose-800';
            let badgeText = isConnected ? 'Conectado' : 'Desconectado';
            if (isConnected && info.expires_at) badgeText += ` • expira ${info.expires_at}`;
            if (info.login_window_open) badgeText += ' • janela aberta';
            
            let netIconClass = getNetworkIcon(network);
            let netIconColor = "text-[#1D4ED8] dark:text-[#60A5FA] bg-[#1D4ED8]/10 dark:bg-[#1D4ED8]/20";
            if (network === 'instagram') netIconColor = "text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-950/80";
            else if (network === 'tiktok') netIconColor = "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/80";
            else if (network === 'youtube') netIconColor = "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/80";
            else if (network === 'facebook') netIconColor = "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/80";
            else if (network === 'x' || network === 'twitter') netIconColor = "text-slate-900 dark:text-slate-100 bg-slate-200 dark:bg-[#1E1E22]";

            card.innerHTML = `
                <div class="flex items-center gap-3.5">
                    <div class="w-10 h-10 rounded-md ${netIconColor} flex items-center justify-center text-lg shadow-2xs">
                        <i class="fa-brands ${netIconClass}"></i>
                    </div>
                    <div>
                        <div class="font-bold text-slate-900 dark:text-slate-100 text-sm">${getNetworkName(network)}</div>
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold border ${badgeColor} mt-0.5">
                            <i class="fa-solid ${isConnected ? 'fa-check' : 'fa-xmark'} text-[10px]"></i> ${badgeText}
                        </span>
                    </div>
                </div>
                <div class="flex items-center gap-2 justify-end w-full sm:w-auto">
                    <button onclick="doLogin('${escapeHtml(network)}')" class="px-3 py-1.5 border border-slate-200 dark:border-[#323238] text-xs font-bold rounded-lg text-slate-700 dark:text-slate-200 bg-white dark:bg-[#1E1E22] hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none transition-colors flex items-center gap-1.5" title="Abre uma janela do Chrome com o perfil desta rede. Faça login (ou confira a sessão) e feche a janela.">
                        <i class="fa-solid ${isConnected ? 'fa-eye' : 'fa-right-to-bracket'} text-[11px] text-slate-400"></i> ${isConnected ? 'Abrir / Renovar' : 'Conectar'}
                    </button>
                </div>
            `;
            accountsList.appendChild(card);
        }
    } catch (error) {
        console.error('Erro inesperado em loadAccounts:', error);
        showToast('Erro interno ao processar contas no navegador.', 'error');
    }
}

let isLoginInProgress = false;
let accountsPollTimer = null;

// Enquanto o modal de contas estiver aberto, atualiza o status para refletir o login feito na janela do Chrome
function startAccountsPolling() {
    clearInterval(accountsPollTimer);
    let ticks = 0;
    accountsPollTimer = setInterval(() => {
        ticks++;
        const modalOpen = !document.getElementById('accountsModal')?.classList.contains('hidden');
        if (!modalOpen || ticks > 60) {
            clearInterval(accountsPollTimer);
            return;
        }
        loadAccounts(true);
    }, 5000);
}

async function doLogin(network) {
    if (isLoginInProgress) return;
    isLoginInProgress = true;
    
    try {
        let response;
        try {
            response = await fetch(`${BASE_URL}/api/accounts/${network}/login`, {
                method: 'POST'
            });
        } catch (fetchError) {
            console.error('Falha de conexão no login:', fetchError);
            showToast('O servidor backend parece estar offline ou inacessível.', 'error');
            return;
        }
        
        if (!response.ok) {
            let errorMsg = 'Erro na autenticação';
            try {
                const errData = await response.json();
                if (errData.detail) errorMsg = errData.detail;
            } catch(e) {}
            showToast(`Falha no servidor: ${errorMsg}`, 'error');
            return;
        }
        
        showToast(`Janela do ${getNetworkName(network)} aberta. Faça login e feche a janela ao terminar.`, 'success');
        await loadAccounts();
        startAccountsPolling();
    } catch (error) {
        console.error('Erro inesperado em doLogin:', error);
        showToast(`Erro interno ao processar login para ${getNetworkName(network)}`, 'error');
    } finally {
        setTimeout(() => { isLoginInProgress = false; }, 2000);
    }
}

// SECTION 6 - SCRAPING (extração em segundo plano + logs ao vivo via WebSocket)
let ws = null;
let wsReconnectTimer = null;
let activeScrapeJob = null;
let activeJobPollTimer = null;
const FINISHED_JOB_STATUSES = ['done', 'cancelled', 'error'];

function generateUUID() {
    if (window.crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

// O client_id fica salvo na aba: uma extração em andamento continua enviando logs após recarregar a página
const clientId = (() => {
    try {
        const saved = sessionStorage.getItem('raspClientId');
        if (saved) return saved;
        const id = generateUUID();
        sessionStorage.setItem('raspClientId', id);
        return id;
    } catch (e) {
        return generateUUID();
    }
})();

const LOG_TAG_STYLES = {
    START: 'text-blue-400',
    INFO: 'text-cyan-400',
    SUCCESS: 'text-green-400 font-bold',
    WARN: 'text-yellow-400',
    ERROR: 'text-red-400',
    DONE: 'text-purple-400 font-bold',
    SYSTEM: 'text-gray-500'
};

function appendTerminalLog(msg) {
    const terminalLogs = document.getElementById('terminalLogs');
    const directTerminalLogs = document.getElementById('directTerminalLogs');
    if (!terminalLogs && !directTerminalLogs) return;

    const text = String(msg ?? '');
    const match = text.match(/^\[(\w+)\]\s?([\s\S]*)$/);

    const appendTo = (el) => {
        if (!el) return;
        const div = document.createElement('div');
        if (match && LOG_TAG_STYLES[match[1]]) {
            div.innerHTML = `<span class="${LOG_TAG_STYLES[match[1]]}">[${match[1]}]</span> ${escapeHtml(match[2])}`;
        } else {
            div.textContent = text;
        }
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        el.appendChild(div);
        while (el.childElementCount > 500) el.removeChild(el.firstChild);
        if (nearBottom) el.scrollTop = el.scrollHeight;
    };

    appendTo(terminalLogs);
    appendTo(directTerminalLogs);

    const progress = text.match(/([\w ]+):\s*(\d+)\/(\d+) posts coletados/);
    const status = document.getElementById('scrapeStatusText');
    if (status && progress) status.textContent = `${progress[1].trim()}: ${progress[2]}/${progress[3]} posts`;
    const directStatus = document.getElementById('directScrapeStatusText');
    if (directStatus && progress) directStatus.textContent = `${progress[1].trim()}: ${progress[2]}/${progress[3]} posts`;
}

function connectWebSocket() {
    return new Promise((resolve, reject) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            resolve(ws);
            return;
        }
        if (ws && ws.readyState === WebSocket.CONNECTING) {
            ws.addEventListener('open', () => resolve(ws), { once: true });
            ws.addEventListener('error', reject, { once: true });
            return;
        }
        ws = new WebSocket(`${WS_BASE_URL}/ws/scrape/${encodeURIComponent(clientId)}`);
        ws.onopen = () => resolve(ws);
        ws.onerror = (err) => {
            console.warn('WebSocket Error:', err);
            reject(err);
        };
        ws.onclose = () => {
            if ((activeScrapeJob || activeCommentsJob) && !wsReconnectTimer) {
                wsReconnectTimer = setTimeout(() => {
                    wsReconnectTimer = null;
                    connectWebSocket().catch(() => {});
                }, 2000);
            }
        };
        ws.onmessage = (event) => {
            const msg = String(event.data || '');
            if (msg.startsWith('[JOB] ')) {
                try {
                    const job = JSON.parse(msg.slice(6));
                    if (job.kind === 'comments') handleCommentsJobUpdate(job);
                    else handleJobUpdate(job);
                } catch (e) {
                    console.warn('Atualização de job inválida', e);
                }
                return;
            }
            // Logs da coleta de comentários chegam pela consulta periódica do painel (não poluem o console da extração)
            if (msg.startsWith('[CLOG] ')) return;
            appendTerminalLog(msg);
        };
    });
}

function collectScrapeKeywords() {
    const searchType = document.querySelector('input[name="search_type"]:checked')?.value || 'keyword';
    if (searchType === 'profile') {
        const brand = document.getElementById('scrapeBrandSelect')?.value || '';
        const typed = (document.getElementById('scrapeProfileInput')?.value || '')
            .split(',').map(s => s.trim()).filter(Boolean);
        return { searchType, keywords: brand ? [brand, ...typed] : typed };
    }
    const text = (document.getElementById('keywordEditor')?.innerText || '').replace(/ /g, ' ').trim();
    return { searchType, keywords: text ? text.split(',').map(k => k.trim()).filter(Boolean) : [] };
}

// Lê a data do campo; se o usuário digitou direto no campo visual (dd/mm/aaaa), converte para AAAA-MM-DD
function readDateInput(inputId, picker) {
    let value = document.getElementById(inputId)?.value || '';
    if (!value && picker && picker.altInput && picker.altInput.value) {
        const m = picker.altInput.value.trim().match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
        if (m) {
            value = `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
            try { picker.setDate(value, false); } catch (e) {}
        }
    }
    return value;
}

function setScrapeRunning(isRunning) {
    const btn = document.getElementById('btnScrape');
    const cancelBtn = document.getElementById('btnCancelScrape');
    if (btn) {
        btn.disabled = isRunning;
        btn.innerHTML = isRunning
            ? '<i class="fa-solid fa-circle-notch fa-spin"></i> Coletando...'
            : '<i class="fa-solid fa-satellite-dish"></i> Iniciar Varredura';
    }
    if (cancelBtn) {
        cancelBtn.classList.toggle('hidden', !isRunning);
        cancelBtn.classList.toggle('inline-flex', isRunning);
        cancelBtn.disabled = false;
    }
}

function updateScrapeProgress(job) {
    if (!job) return;
    const bar = document.getElementById('scrapeProgressBar');
    const directBar = document.getElementById('directProgressBar');
    const status = document.getElementById('scrapeStatusText');
    const directStatus = document.getElementById('directScrapeStatusText');
    const total = job.progress?.total || 0;
    const done = job.progress?.done || 0;
    let pct = total ? Math.round((done / total) * 100) : 0;
    if (job.status === 'running' && pct < 4) pct = 4;
    if (FINISHED_JOB_STATUSES.includes(job.status)) pct = 100;
    if (bar) bar.style.width = `${pct}%`;
    if (directBar) directBar.style.width = `${pct}%`;
    const label = `${done}/${total} etapas • ${Number(job.total_posts || 0).toLocaleString('pt-BR')} posts`;
    if (status && (FINISHED_JOB_STATUSES.includes(job.status) || done > 0)) {
        status.textContent = label;
    }
    if (directStatus && (FINISHED_JOB_STATUSES.includes(job.status) || done > 0)) {
        directStatus.textContent = label;
    }
}

function setDirectScrapeRunning(isRunning) {
    const btn = document.getElementById('btnDirectScrape');
    if (!btn) return;
    btn.disabled = isRunning;
    btn.innerHTML = isRunning
        ? '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Extraindo...'
        : '<i class="fa-solid fa-bolt mr-1.5"></i> Extrair Publicação';
}

function updateDirectNetworkSelection(val) {
    const radio = document.querySelector(`input[name="direct_network"][value="${val}"]`);
    if (radio && !radio.checked) {
        radio.checked = true;
    }
}
window.updateDirectNetworkSelection = updateDirectNetworkSelection;

function extractValidUrls(rawText) {
    if (!rawText) return [];
    return rawText
        .split('\n')
        .map(l => l.trim())
        .filter(l => l.length > 0)
        .map(l => {
            if (/^https?:\/\//i.test(l)) return l;
            if (l.includes('.') && (l.includes('/') || l.includes('?') || l.length > 6)) {
                return `https://${l}`;
            }
            return null;
        })
        .filter(Boolean);
}
window.extractValidUrls = extractValidUrls;

function updateDirectUrlsCount() {
    const text = document.getElementById('directPostUrls')?.value || '';
    const urls = extractValidUrls(text);
    const count = urls.length;
    const badge = document.getElementById('directUrlsCountBadge');
    if (badge) {
        badge.textContent = `${count} ${count === 1 ? 'link inserido' : 'links inseridos'}`;
        badge.className = count > 0 
            ? 'text-[11px] text-[#1D4ED8] dark:text-[#60A5FA] font-semibold font-mono'
            : 'text-[11px] text-slate-500 dark:text-[#A1A1AA] font-mono';
    }
}
window.updateDirectUrlsCount = updateDirectUrlsCount;

function toggleDirectCommentsLimit(checked) {
    const container = document.getElementById('directCommentsLimitContainer');
    if (container) {
        container.classList.toggle('hidden', !checked);
    }
}
window.toggleDirectCommentsLimit = toggleDirectCommentsLimit;

function clearDirectPostForm() {
    const input = document.getElementById('directPostUrls');
    if (input) input.value = '';
    const autoRadio = document.querySelector('input[name="direct_network"][value="auto"]');
    if (autoRadio) {
        autoRadio.checked = true;
        updateDirectNetworkSelection('auto');
    }
    const chkComments = document.getElementById('directScrapeComments');
    if (chkComments) {
        chkComments.checked = false;
        toggleDirectCommentsLimit(false);
    }
    const directMaxComments = document.getElementById('directMaxComments');
    if (directMaxComments) directMaxComments.value = 100;
    const directLimitValue = document.getElementById('directLimitValue');
    if (directLimitValue) directLimitValue.innerText = '100';

    updateDirectUrlsCount();
    document.getElementById('directTerminalContainer')?.classList.add('hidden');
    document.getElementById('directResultsSection')?.classList.add('hidden');
}
window.clearDirectPostForm = clearDirectPostForm;

async function handleDirectPostSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (activeScrapeJob) {
        showToast('Já existe uma extração em andamento nesta aba.', 'info');
        return;
    }

    const textarea = document.getElementById('directPostUrls');
    const text = textarea?.value || '';
    const urls = extractValidUrls(text);

    if (urls.length === 0) {
        if (textarea) {
            textarea.focus();
            textarea.classList.add('ring-2', 'ring-rose-500', 'border-rose-500');
            setTimeout(() => {
                textarea.classList.remove('ring-2', 'ring-rose-500', 'border-rose-500');
            }, 3000);
        }
        showToast('Cole ao menos um link válido de publicação (ex: instagram.com/p/... ou tiktok.com/@...).', 'error');
        return;
    }

    if (textarea) textarea.value = urls.join('\n');
    updateDirectUrlsCount();

    const network = document.querySelector('input[name="direct_network"]:checked')?.value || 'auto';
    const scrapeComments = document.getElementById('directScrapeComments')?.checked || false;
    const maxComments = parseInt(document.getElementById('directMaxComments')?.value || '100', 10);

    const payload = {
        client_id: CLIENT_ID,
        keywords: urls,
        networks: [network],
        search_type: 'url',
        limit: urls.length,
        scrape_comments: scrapeComments,
        max_comments: maxComments,
        enrich_media: document.getElementById('directEnrichMedia')?.checked || false,
        generate_contact_sheet: document.getElementById('directGenerateContactSheet')?.checked || false,
        transcribe_audio: document.getElementById('directTranscribeAudio')?.checked || false,
        detect_scenes: document.getElementById('directDetectScenes')?.checked || false
    };

    document.getElementById('directTerminalContainer')?.classList.remove('hidden');
    const directTerminalLogs = document.getElementById('directTerminalLogs');
    if (directTerminalLogs) directTerminalLogs.innerHTML = '';
    const status = document.getElementById('directScrapeStatusText');
    if (status) status.textContent = 'Iniciando extração do post...';
    appendTerminalLog('[SYSTEM] Conectando ao servidor para extração de posts específicos...');
    document.getElementById('directResultsSection')?.classList.add('hidden');
    setDirectScrapeRunning(true);
    updateScrapeProgress({ status: 'running', progress: { done: 0, total: urls.length }, total_posts: 0 });

    try {
        try {
            await connectWebSocket();
        } catch (wsErr) {
            appendTerminalLog('[WARN] Logs ao vivo indisponíveis; o andamento será atualizado pelo status da extração.');
        }

        const response = await fetch(`${BASE_URL}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Erro ao iniciar extração por link'));

        const data = await response.json();
        startTrackingJob(data.data);
    } catch (error) {
        console.error(error);
        appendTerminalLog(`[ERROR] ${error.message || error}`);
        showToast(error.message || 'Falha ao iniciar extração do post', 'error');
        setDirectScrapeRunning(false);
    }
}
window.handleDirectPostSubmit = handleDirectPostSubmit;

async function handleScrapeSubmit(e) {
    e.preventDefault();
    if (activeScrapeJob) {
        showToast('Já existe uma extração em andamento nesta aba.', 'info');
        return;
    }

    const { searchType, keywords } = collectScrapeKeywords();
    if (keywords.length === 0) {
        showToast(searchType === 'profile' ? 'Selecione uma marca ou digite um perfil' : 'Digite os termos de busca', 'error');
        return;
    }

    const networks = Array.from(document.querySelectorAll('input[name="network"]:checked')).map(cb => cb.value);
    if (networks.length === 0) {
        showToast('Selecione pelo menos uma rede social', 'error');
        return;
    }

    const startVal = readDateInput('startDate', window.fpStart);
    const endVal = readDateInput('endDate', window.fpEnd);
    if (startVal && endVal && startVal > endVal) {
        showToast('A data inicial não pode ser posterior à data final', 'error');
        return;
    }

    const payload = {
        client_id: clientId,
        keywords: keywords,
        networks: networks,
        search_type: searchType,
        limit: parseInt(document.getElementById('limit').value, 10) || 50,
        start_date: startVal || null,
        end_date: endVal || null,
        enrich_media: document.getElementById('enrichMedia')?.checked || false,
        generate_contact_sheet: document.getElementById('generateContactSheet')?.checked || false,
        transcribe_audio: document.getElementById('transcribeAudio')?.checked || false,
        detect_scenes: document.getElementById('detectScenes')?.checked || false
    };

    if (searchType === 'keyword') {
        saveToHistory(keywords.join(', '), payload.limit, startVal, endVal, networks);
    }

    document.getElementById('terminalContainer')?.classList.remove('hidden');
    const terminalLogs = document.getElementById('terminalLogs');
    if (terminalLogs) terminalLogs.innerHTML = '';
    const status = document.getElementById('scrapeStatusText');
    if (status) status.textContent = 'Iniciando...';
    appendTerminalLog('[SYSTEM] Conectando ao servidor backend...');
    document.getElementById('resultsSection')?.classList.add('hidden');
    setScrapeRunning(true);
    updateScrapeProgress({ status: 'running', progress: { done: 0, total: networks.length * keywords.length }, total_posts: 0 });

    try {
        try {
            await connectWebSocket();
        } catch (wsErr) {
            appendTerminalLog('[WARN] Logs ao vivo indisponíveis; o andamento será atualizado pelo status da extração.');
        }

        const response = await fetch(`${BASE_URL}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Erro ao iniciar coleta'));

        const data = await response.json();
        startTrackingJob(data.data);
    } catch (error) {
        console.error(error);
        appendTerminalLog(`[ERROR] ${error.message || error}`);
        showToast(error.message || 'Falha ao iniciar coleta', 'error');
        setScrapeRunning(false);
    }
}

function startTrackingJob(job) {
    activeScrapeJob = job;
    try { sessionStorage.setItem('raspActiveJob', job.job_id); } catch (e) {}
    setScrapeRunning(true);
    updateScrapeProgress(job);
    clearInterval(activeJobPollTimer);
    // Consulta periódica de segurança caso o WebSocket caia
    activeJobPollTimer = setInterval(async () => {
        if (!activeScrapeJob) return;
        try {
            const r = await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(activeScrapeJob.job_id)}?logs=false`);
            if (r.status === 404) {
                finishScrape({ ...activeScrapeJob, status: 'error', error: 'O servidor foi reiniciado durante a extração.' });
                return;
            }
            if (r.ok) handleJobUpdate(await r.json());
        } catch (e) {}
    }, 5000);
}

function handleJobUpdate(job) {
    if (!job || !activeScrapeJob || job.job_id !== activeScrapeJob.job_id) return;
    activeScrapeJob = job;
    updateScrapeProgress(job);
    if (FINISHED_JOB_STATUSES.includes(job.status)) finishScrape(job);
}

function finishScrape(job) {
    clearInterval(activeJobPollTimer);
    activeJobPollTimer = null;
    activeScrapeJob = null;
    try { sessionStorage.removeItem('raspActiveJob'); } catch (e) {}
    setScrapeRunning(false);
    setDirectScrapeRunning(false);
    updateScrapeProgress(job);

    if (job.status === 'error' && !job.total_posts) {
        showToast(job.error || 'Falha ao executar coleta', 'error');
        return;
    }

    if (job.search_type === 'url') {
        const directResults = document.getElementById('directResultsSection');
        if (directResults) directResults.classList.remove('hidden');
        const dtTitle = document.getElementById('directResultsTitle');
        if (dtTitle) {
            dtTitle.textContent = job.status === 'cancelled'
                ? 'Extração cancelada'
                : (job.total_posts ? 'Publicação Extraída com Sucesso!' : 'Extração concluída sem resultados');
        }
        const dtText = document.getElementById('directResultsText');
        if (dtText) {
            dtText.textContent = `Foram coletados ${Number(job.total_posts || 0).toLocaleString('pt-BR')} posts.`;
        }
        const dtComments = document.getElementById('directResultsCommentsText');
        if (dtComments) {
            dtComments.textContent = job.total_comments ? `Total de ${Number(job.total_comments).toLocaleString('pt-BR')} comentários salvos.` : '';
        }
        const dtFolder = document.getElementById('directResultsSavedFolder');
        if (dtFolder) {
            dtFolder.textContent = job.saved_folder ? `Salva em: ${job.saved_folder}` : '';
            dtFolder.classList.toggle('hidden', !job.saved_folder);
        }
        const btnXlsx = document.getElementById('btnDirectExportXlsx');
        if (btnXlsx) {
            if (job.download_url) {
                btnXlsx.onclick = () => { window.location.href = BASE_URL + job.download_url; };
                btnXlsx.classList.remove('hidden');
                btnXlsx.classList.add('flex');
            } else {
                btnXlsx.classList.add('hidden');
                btnXlsx.classList.remove('flex');
            }
        }
    } else {
        document.getElementById('resultsSection')?.classList.remove('hidden');
        const title = document.getElementById('resultsTitle');
        if (title) {
            title.textContent = job.status === 'cancelled'
                ? 'Extração cancelada'
                : (job.total_posts ? 'Extração Concluída com Sucesso!' : 'Extração concluída sem resultados');
        }
        const resultsText = document.getElementById('resultsText');
        if (resultsText) resultsText.textContent = `Foram coletados ${Number(job.total_posts || 0).toLocaleString('pt-BR')} posts.`;
        const breakdown = document.getElementById('resultsBreakdown');
        if (breakdown) {
            breakdown.textContent = Object.entries(job.network_results || {})
                .map(([net, count]) => `${getNetworkName(net)}: ${count}`)
                .join(' • ');
        }
        const savedFolder = document.getElementById('resultsSavedFolder');
        if (savedFolder) {
            savedFolder.textContent = job.saved_folder ? `Salva em: ${job.saved_folder}` : '';
            savedFolder.classList.toggle('hidden', !job.saved_folder);
        }

        const exportBtn = document.getElementById('btnExportXlsx');
        if (exportBtn) {
            if (job.download_url) {
                exportBtn.onclick = () => { window.location.href = BASE_URL + job.download_url; };
                exportBtn.classList.remove('hidden');
                exportBtn.classList.add('flex');
            } else {
                exportBtn.classList.add('hidden');
                exportBtn.classList.remove('flex');
            }
        }
    }

    if (job.status === 'cancelled') {
        showToast('Extração cancelada — os posts coletados foram salvos', 'info');
    } else {
        showToast('Coleta finalizada com sucesso', 'success');
    }
    if (job.total_posts) loadDashboardData(job.run_id || '', true);
}

async function cancelActiveScrape() {
    if (!activeScrapeJob) return;
    if (!confirm('Cancelar a extração em andamento? Os posts já coletados serão mantidos.')) return;
    const btn = document.getElementById('btnCancelScrape');
    if (btn) btn.disabled = true;
    try {
        await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(activeScrapeJob.job_id)}/cancel`, { method: 'POST' });
        appendTerminalLog('[WARN] Cancelamento solicitado. Finalizando a etapa atual...');
    } catch (e) {
        showToast('Não foi possível cancelar a extração', 'error');
        if (btn) btn.disabled = false;
    }
}
window.cancelActiveScrape = cancelActiveScrape;

async function restoreActiveScrape() {
    let jobId = null;
    try { jobId = sessionStorage.getItem('raspActiveJob'); } catch (e) {}
    if (!jobId) return;
    try {
        const r = await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}?logs=true`);
        if (!r.ok) {
            sessionStorage.removeItem('raspActiveJob');
            return;
        }
        const job = await r.json();
        if (FINISHED_JOB_STATUSES.includes(job.status)) {
            sessionStorage.removeItem('raspActiveJob');
            return;
        }
        document.getElementById('terminalContainer')?.classList.remove('hidden');
        const terminalLogs = document.getElementById('terminalLogs');
        if (terminalLogs) terminalLogs.innerHTML = '';
        (job.logs || []).forEach(appendTerminalLog);
        appendTerminalLog('[SYSTEM] Acompanhamento da extração retomado.');
        connectWebSocket().catch(() => {});
        startTrackingJob(job);
    } catch (e) {
        console.warn('Não foi possível retomar a extração:', e);
    }
}

// SECTION 7 - DASHBOARD
async function loadRunsHistory(selectedRunId = '', isInitialLoad = false) {
    try {
        const response = await fetchWithRetry(`${BASE_URL}/api/history/runs`, {}, isInitialLoad ? 4 : 2, 350);
        if (!response.ok) return;
        const runs = await response.json();
        const select = document.getElementById('runHistorySelect');
        if (!select) return;

        if (!runs || runs.length === 0) {
            select.innerHTML = '<option value="">Sem histórico de extrações</option>';
            return;
        }

        const describe = (r, idx) => {
            const query = (r.query || 'Extração').replace(/\s+/g, ' ');
            const shortQuery = query.length > 42 ? `${query.slice(0, 40)}…` : query;
            const status = r.status === 'running' ? ' (em andamento)' : r.status === 'cancelled' ? ' (cancelada)' : r.status === 'error' ? ' (com erro)' : '';
            const origin = r.origin === 'agendamento' ? ' • agendada' : '';
            return `#${runs.length - idx} • ${r.date} • ${shortQuery} — ${r.total} posts${status}${origin}`;
        };

        select.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = `Mais recente: ${describe(runs[0], 0)}`;
        select.appendChild(defaultOpt);

        runs.forEach((r, idx) => {
            const opt = document.createElement('option');
            opt.value = r.run_id;
            opt.textContent = describe(r, idx);
            opt.title = r.query || '';
            select.appendChild(opt);
        });

        select.value = runs.some(r => r.run_id === selectedRunId) ? selectedRunId : '';
    } catch (e) {
        console.warn('Erro ao carregar histórico de runs:', e);
    }
}

// Números compactos no padrão brasileiro: 46,4 mil · 2,9 mi · 1,2 bi
function formatEngagementNumber(val) {
    const num = Number(val) || 0;
    const compact = (value, suffix) => `${value.toLocaleString('pt-BR', { maximumFractionDigits: value < 10 ? 1 : 0 })} ${suffix}`;
    if (Math.abs(num) >= 1e9) return compact(num / 1e9, 'bi');
    if (Math.abs(num) >= 1e6) return compact(num / 1e6, 'mi');
    if (Math.abs(num) >= 1e4) return compact(num / 1e3, 'mil');
    return Math.round(num).toLocaleString('pt-BR');
}

// DASHBOARD STATE
let currentChartMetric = 'engagement'; // 'engagement' | 'volume'
let currentDashboardFilter = {
    network: 'ALL',
    term: 'ALL'
};

const NETWORK_ORDER = ['X', 'TIKTOK', 'INSTAGRAM', 'YOUTUBE', 'FACEBOOK'];
const NETWORK_LABELS = { X: 'X', TIKTOK: 'TikTok', INSTAGRAM: 'Instagram', YOUTUBE: 'YouTube', FACEBOOK: 'Facebook' };
const dashCharts = {};

// Cores e tinta vêm das variáveis CSS do dashboard (claro/escuro), então os gráficos seguem o tema
function dashToken(name) {
    const root = document.getElementById('tab-dashboard') || document.documentElement;
    return getComputedStyle(root).getPropertyValue(name).trim();
}

function networkColor(key) {
    return dashToken(`--net-${String(key || '').toLowerCase()}`) || dashToken('--rp-accent');
}

function destroyDashChart(id) {
    if (dashCharts[id]) {
        dashCharts[id].destroy();
        delete dashCharts[id];
    }
}

function setupChartDefaults() {
    if (typeof Chart === 'undefined' || setupChartDefaults.done) return;
    setupChartDefaults.done = true;
    if (typeof ChartDataLabels !== 'undefined') {
        Chart.register(ChartDataLabels);
        Chart.defaults.set('plugins.datalabels', { display: false });
    }
    Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.animation.duration = 350;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
    Chart.defaults.plugins.tooltip.titleFont = { weight: '600' };
}

function setChartMetric(metric) {
    currentChartMetric = metric;
    document.getElementById('btnChartMetricEng')?.classList.toggle('active', metric === 'engagement');
    document.getElementById('btnChartMetricVol')?.classList.toggle('active', metric === 'volume');
    const title = document.getElementById('mainChartTitle');
    const subtitle = document.getElementById('mainChartSubtitle');
    if (title) title.textContent = metric === 'engagement' ? 'Interações por rede' : 'Publicações por rede';
    if (subtitle) subtitle.textContent = metric === 'engagement' ? 'Curtidas + comentários somados' : 'Quantidade de publicações coletadas';
    applyAllDashboardFilters(false);
}
window.setChartMetric = setChartMetric;

function setDashboardNetworkFilter(net) {
    currentDashboardFilter.network = (net || 'ALL').toUpperCase();
    
    // Update active pill UI
    document.querySelectorAll('#dashNetworkPills .dash-net-pill').forEach(pill => {
        if ((pill.getAttribute('data-net') || '').toUpperCase() === currentDashboardFilter.network) {
            pill.classList.add('active');
        } else {
            pill.classList.remove('active');
        }
    });

    // Keep feedNetworkFilter select in sync
    const feedNetSelect = document.getElementById('feedNetworkFilter');
    if (feedNetSelect) {
        feedNetSelect.value = currentDashboardFilter.network;
    }

    applyAllDashboardFilters();
}
window.setDashboardNetworkFilter = setDashboardNetworkFilter;

function resetAllDashboardFilters(showNotice = true) {
    currentDashboardFilter = {
        network: 'ALL',
        term: 'ALL'
    };

    document.querySelectorAll('#dashNetworkPills .dash-net-pill').forEach(pill => {
        pill.classList.toggle('active', pill.getAttribute('data-net') === 'ALL');
    });

    const termSelect = document.getElementById('dashTermFilter');
    if (termSelect) termSelect.value = 'ALL';
    const feedNetSelect = document.getElementById('feedNetworkFilter');
    if (feedNetSelect) feedNetSelect.value = 'ALL';
    const searchInput = document.getElementById('feedSearchInput');
    if (searchInput) searchInput.value = '';

    activeWordCloudFilter = null;
    renderWordCloud(currentWordCloudData, null);

    applyAllDashboardFilters();
    if (showNotice) showToast('Filtros do dashboard redefinidos', 'info');
}
window.resetAllDashboardFilters = resetAllDashboardFilters;

function normalizeNetKey(network) {
    const n = String(network || '').toUpperCase();
    if (n.includes('TIKTOK')) return 'TIKTOK';
    if (n.includes('INSTAGRAM')) return 'INSTAGRAM';
    if (n.includes('YOUTUBE')) return 'YOUTUBE';
    if (n.includes('FACEBOOK')) return 'FACEBOOK';
    if (n.includes('TWITTER') || n === 'X') return 'X';
    return n || 'OUTROS';
}

function aggregateByNetwork(posts) {
    const map = {};
    posts.forEach(it => {
        const key = normalizeNetKey(it.network);
        const agg = map[key] || (map[key] = { key, posts: 0, engagement: 0, likes: 0, comments: 0, views: 0 });
        agg.posts += 1;
        agg.engagement += Number(it.engagement) || 0;
        agg.likes += Number(it.likes) || 0;
        agg.comments += Number(it.comments) || 0;
        agg.views += Number(it.views) || 0;
    });
    return Object.values(map);
}

// Barras horizontais por rede com o valor escrito na ponta de cada barra
function renderNetworkBars(rows) {
    const canvas = document.getElementById('engagementChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyDashChart('network');
    const isVolume = currentChartMetric === 'volume';
    const sorted = [...rows].sort((a, b) => (isVolume ? b.posts - a.posts : b.engagement - a.engagement));
    const values = sorted.map(r => (isVolume ? r.posts : r.engagement));
    const totalPosts = rows.reduce((s, r) => s + r.posts, 0) || 1;

    const wrap = document.getElementById('engagementChartWrap');
    if (wrap) wrap.style.height = `${Math.max(150, sorted.length * 46 + 36)}px`;

    dashCharts.network = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: sorted.map(r => NETWORK_LABELS[r.key] || r.key),
            datasets: [{
                data: values,
                backgroundColor: sorted.map(r => networkColor(r.key)),
                borderRadius: 4,
                borderSkipped: 'start',
                barThickness: 22
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { right: 72 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const row = sorted[ctx.dataIndex];
                            return isVolume
                                ? ` ${row.posts.toLocaleString('pt-BR')} publicações (${Math.round(row.posts / totalPosts * 100)}%)`
                                : ` ${row.engagement.toLocaleString('pt-BR')} interações · ${row.posts.toLocaleString('pt-BR')} posts`;
                        }
                    }
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'end',
                    offset: 6,
                    clamp: true,
                    color: dashToken('--rp-ink'),
                    font: { weight: '600', size: 12 },
                    formatter: (value, ctx) => isVolume
                        ? `${value.toLocaleString('pt-BR')} · ${Math.round(sorted[ctx.dataIndex].posts / totalPosts * 100)}%`
                        : formatEngagementNumber(value)
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: dashToken('--rp-grid'), drawTicks: false },
                    border: { display: false },
                    ticks: { color: dashToken('--rp-muted'), maxTicksLimit: 5, padding: 6, callback: v => formatEngagementNumber(v) }
                },
                y: {
                    grid: { display: false },
                    border: { color: dashToken('--rp-axis') },
                    ticks: { color: dashToken('--rp-ink'), font: { weight: '600', size: 12.5 } }
                }
            }
        }
    });
}

// Rosca de participação no volume + legenda com nome, quantidade e %
function renderVolumeDonut(rows) {
    const canvas = document.getElementById('volumeChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyDashChart('volume');
    const sorted = NETWORK_ORDER.map(k => rows.find(r => r.key === k)).filter(Boolean)
        .concat(rows.filter(r => !NETWORK_ORDER.includes(r.key)));
    const total = sorted.reduce((s, r) => s + r.posts, 0);

    dashCharts.volume = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: sorted.map(r => NETWORK_LABELS[r.key] || r.key),
            datasets: [{
                data: sorted.map(r => r.posts),
                backgroundColor: sorted.map(r => networkColor(r.key)),
                borderColor: dashToken('--rp-surface'),
                borderWidth: 2,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${ctx.raw.toLocaleString('pt-BR')} (${total ? Math.round(ctx.raw / total * 100) : 0}%)`
                    }
                }
            }
        }
    });

    const center = document.getElementById('volumeCenter');
    if (center) {
        center.innerHTML = `<span style="font-size:24px;font-weight:650;letter-spacing:-0.02em;color:var(--rp-ink)">${total.toLocaleString('pt-BR')}</span>
            <span style="font-size:11.5px;color:var(--rp-muted)">publicações</span>`;
    }
    const legend = document.getElementById('volumeLegend');
    if (legend) {
        legend.innerHTML = sorted.length ? sorted.map(r => `
            <li class="rp-legend-row">
                <span class="rp-swatch" style="background:${networkColor(r.key)}"></span>
                <span class="name">${escapeHtml(NETWORK_LABELS[r.key] || r.key)}</span>
                <span class="value">${r.posts.toLocaleString('pt-BR')}</span>
                <span class="pct">${total ? (r.posts / total * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : 0}%</span>
            </li>`).join('') : '<li class="rp-muted-text">Sem dados</li>';
    }
}

// Publicações por dia (ou por semana em períodos longos), rotulando o pico
function renderTimeline(posts) {
    const canvas = document.getElementById('timelineChart');
    if (!canvas || typeof Chart === 'undefined') return;
    destroyDashChart('timeline');
    const empty = document.getElementById('timelineEmpty');
    const subtitle = document.getElementById('timelineSubtitle');

    const dated = posts.map(p => (p.date_iso ? new Date(p.date_iso) : null)).filter(d => d && !isNaN(d));
    const undated = posts.length - dated.length;
    if (dated.length === 0) {
        empty?.classList.remove('hidden');
        canvas.classList.add('hidden');
        if (subtitle) subtitle.textContent = 'Por data de publicação';
        return;
    }
    empty?.classList.add('hidden');
    canvas.classList.remove('hidden');

    const dayMs = 86400000;
    const startOfDay = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const min = startOfDay(new Date(Math.min(...dated)));
    const max = startOfDay(new Date(Math.max(...dated)));
    const spanDays = Math.round((max - min) / dayMs) + 1;
    const weekly = spanDays > 60;
    const bucketStart = d => {
        const day = startOfDay(d);
        if (!weekly) return day;
        const offset = (day.getDay() + 6) % 7; // semana começando na segunda
        return new Date(day.getTime() - offset * dayMs);
    };

    const counts = new Map();
    dated.forEach(d => {
        const key = bucketStart(d).getTime();
        counts.set(key, (counts.get(key) || 0) + 1);
    });
    const step = weekly ? 7 * dayMs : dayMs;
    const keys = [];
    if (spanDays <= 400) {
        for (let t = bucketStart(min).getTime(); t <= max.getTime(); t += step) keys.push(t);
    } else {
        keys.push(...[...counts.keys()].sort((a, b) => a - b));
    }
    const values = keys.map(k => counts.get(k) || 0);
    const peak = values.indexOf(Math.max(...values));
    const fmtDay = t => new Date(t).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });

    if (subtitle) {
        const parts = [weekly ? 'Por semana' : 'Por dia'];
        parts.push(`${fmtDay(min.getTime())} a ${fmtDay(max.getTime())}`);
        if (undated > 0) parts.push(`${undated.toLocaleString('pt-BR')} sem data não aparecem`);
        subtitle.textContent = parts.join(' • ');
    }

    dashCharts.timeline = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: keys.map(fmtDay),
            datasets: [{
                data: values,
                backgroundColor: dashToken('--rp-accent'),
                hoverBackgroundColor: dashToken('--rp-accent'),
                borderRadius: 4,
                borderSkipped: 'start',
                maxBarThickness: 24,
                categoryPercentage: 0.8,
                barPercentage: 0.9
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 22 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: items => weekly ? `Semana de ${items[0].label}` : items[0].label,
                        label: ctx => ` ${ctx.raw.toLocaleString('pt-BR')} publicações`
                    }
                },
                datalabels: {
                    display: ctx => ctx.dataIndex === peak && values[peak] > 0,
                    anchor: 'end',
                    align: 'end',
                    offset: 2,
                    color: dashToken('--rp-ink'),
                    font: { weight: '600', size: 12 },
                    formatter: v => `pico: ${v.toLocaleString('pt-BR')}`
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    border: { color: dashToken('--rp-axis') },
                    ticks: { color: dashToken('--rp-muted'), autoSkip: true, maxTicksLimit: 12, maxRotation: 0 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: dashToken('--rp-grid'), drawTicks: false },
                    border: { display: false },
                    ticks: { color: dashToken('--rp-muted'), precision: 0, maxTicksLimit: 5, padding: 6 }
                }
            }
        }
    });
}

const PLACEHOLDER_AUTHORS = ['@perfil_instagram', '@facebook_user', '@desconhecido', '@canal_youtube', '@instagram_user'];

function renderTopAuthors(posts) {
    const list = document.getElementById('topAuthorsList');
    if (!list) return;
    const map = {};
    posts.forEach(p => {
        const author = (p.author || '').trim();
        if (!author || PLACEHOLDER_AUTHORS.includes(author.toLowerCase())) return;
        const key = `${author}|${normalizeNetKey(p.network)}`;
        const agg = map[key] || (map[key] = { author, net: normalizeNetKey(p.network), posts: 0, engagement: 0, views: 0 });
        agg.posts += 1;
        agg.engagement += Number(p.engagement) || 0;
        agg.views += Number(p.views) || 0;
    });
    const top = Object.values(map).sort((a, b) => b.engagement - a.engagement || b.views - a.views).slice(0, 8);
    if (!top.length) {
        list.innerHTML = '<li class="rp-muted-text py-6 text-center">Sem autores neste filtro</li>';
        return;
    }
    const maxEng = top[0].engagement || 1;
    list.innerHTML = top.map((a, i) => `
        <li class="rp-author" data-author="${escapeHtml(a.author)}" onclick="filterByAuthor(this.dataset.author)" title="Filtrar publicações de ${escapeHtml(a.author)}">
            <span class="rank">${i + 1}</span>
            <div class="min-w-0">
                <div class="flex items-center gap-2 min-w-0">
                    <span class="rp-dot" style="background:${networkColor(a.net)}"></span>
                    <span class="handle">${escapeHtml(a.author)}</span>
                </div>
                <div class="meta">${escapeHtml(NETWORK_LABELS[a.net] || a.net)} • ${a.posts} ${a.posts === 1 ? 'publicação' : 'publicações'}</div>
                <div class="track"><div class="fill" style="width:${Math.max(2, a.engagement / maxEng * 100)}%"></div></div>
            </div>
            <span class="value">${formatEngagementNumber(a.engagement)}</span>
        </li>`).join('');
}

function filterByAuthor(author) {
    const input = document.getElementById('feedSearchInput');
    if (!input) return;
    input.value = author;
    filterDashboardFeedTable();
    document.getElementById('feedTableBody')?.closest('section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
window.filterByAuthor = filterByAuthor;

function renderReportHeader(data) {
    const run = data?.run;
    const title = document.getElementById('reportTitle');
    const meta = document.getElementById('reportMeta');
    if (!title || !meta) return;
    if (!run) {
        title.textContent = 'Nenhuma extração ainda';
        meta.innerHTML = '<span>Execute uma busca na aba Nova Extração para gerar o relatório.</span>';
        return;
    }
    const query = String(run.query || '').replace(/\s*\|\s*/g, ', ');
    const terms = query.replace(/["“”()]/g, ' ').replace(/\b(AND|OR|NOT)\b/gi, '·').replace(/\s+/g, ' ')
        .replace(/(\s*·\s*)+/g, ' · ').replace(/^\s*·\s*|\s*·\s*$/g, '').trim();
    title.textContent = terms || 'Extração';
    title.title = query;

    const nets = aggregateByNetwork(currentRawFeedData).map(r => r.key);
    const netHtml = NETWORK_ORDER.filter(k => nets.includes(k))
        .map(k => `<span class="inline-flex items-center gap-1.5"><span class="rp-dot" style="background:${networkColor(k)}"></span>${NETWORK_LABELS[k]}</span>`)
        .join('<span style="color:var(--rp-axis)">/</span>');
    meta.innerHTML = [
        `<span><i class="fa-regular fa-calendar"></i>${escapeHtml(run.date || '')}</span>`,
        `<span><i class="fa-regular fa-file-lines"></i>${currentRawFeedData.length.toLocaleString('pt-BR')} publicações</span>`,
        netHtml ? `<span class="inline-flex items-center gap-2">${netHtml}</span>` : '',
        run.origin === 'agendamento' ? '<span><i class="fa-regular fa-clock"></i>Agendada</span>' : '',
        query && query !== terms ? `<span title="${escapeHtml(query)}"><i class="fa-solid fa-code"></i>${escapeHtml(query.length > 70 ? query.slice(0, 68) + '…' : query)}</span>` : ''
    ].filter(Boolean).join('');
}

function getFilteredFeed() {
    const netVal = currentDashboardFilter.network || 'ALL';
    const termVal = document.getElementById('dashTermFilter')?.value || 'ALL';
    const searchVal = (document.getElementById('feedSearchInput')?.value || '').trim().toLowerCase();
    return (currentRawFeedData || []).filter(item => {
        if (netVal !== 'ALL' && normalizeNetKey(item.network) !== netVal) return false;
        if (termVal !== 'ALL' && (item.specific_term || item.keyword || '').trim() !== termVal) return false;
        if (searchVal) {
            const txt = (item.text || '').toLowerCase();
            const author = (item.author || '').toLowerCase();
            if (!txt.includes(searchVal) && !author.includes(searchVal)) return false;
        }
        return true;
    });
}

function applyAllDashboardFilters(updateFeedTable = true) {
    setupChartDefaults();
    const netVal = currentDashboardFilter.network || 'ALL';
    const termVal = document.getElementById('dashTermFilter')?.value || 'ALL';
    const rawSearch = (document.getElementById('feedSearchInput')?.value || '').trim();
    currentDashboardFilter.term = termVal;

    const allPosts = currentRawFeedData || [];
    const filtered = getFilteredFeed();
    const totals = filtered.reduce((acc, it) => {
        acc.engagement += Number(it.engagement) || 0;
        acc.likes += Number(it.likes) || 0;
        acc.comments += Number(it.comments) || 0;
        acc.views += Number(it.views) || 0;
        return acc;
    }, { engagement: 0, likes: 0, comments: 0, views: 0 });
    const totalPosts = filtered.length;
    const setText = (id, value, title) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value;
        if (title !== undefined) el.title = title;
    };
    const share = (part, whole) => (whole ? `${Math.round(part / whole * 100)}% das interações` : '');

    setText('dashTotalPosts', totalPosts.toLocaleString('pt-BR'));
    setText('dashTotalPostsSub', totalPosts < allPosts.length ? `de ${allPosts.length.toLocaleString('pt-BR')} no total` : 'no período coletado');
    setText('dashTotalEngagement', formatEngagementNumber(totals.engagement), totals.engagement.toLocaleString('pt-BR'));
    setText('dashAvgEngagement', formatEngagementNumber(totalPosts ? totals.engagement / totalPosts : 0));
    setText('dashTotalLikes', formatEngagementNumber(totals.likes), totals.likes.toLocaleString('pt-BR'));
    setText('dashTotalLikesSub', share(totals.likes, totals.engagement));
    setText('dashTotalComments', formatEngagementNumber(totals.comments), totals.comments.toLocaleString('pt-BR'));
    setText('dashTotalCommentsSub', share(totals.comments, totals.engagement));
    setText('dashTotalViews', formatEngagementNumber(totals.views), totals.views.toLocaleString('pt-BR'));

    const hasFilter = netVal !== 'ALL' || termVal !== 'ALL' || rawSearch;
    setText('dashFilterActiveBadge', hasFilter ? `Mostrando ${totalPosts.toLocaleString('pt-BR')} de ${allPosts.length.toLocaleString('pt-BR')} publicações` : '');
    document.getElementById('btnClearFilter')?.classList.toggle('hidden', !hasFilter);

    const rows = aggregateByNetwork(filtered);
    renderNetworkBars(rows);
    renderVolumeDonut(rows);
    renderTimeline(filtered);
    renderTopAuthors(filtered);

    if (updateFeedTable) renderFeed(filtered);
    setText('feedCountBadge', `${filtered.length.toLocaleString('pt-BR')} de ${allPosts.length.toLocaleString('pt-BR')} publicações`);
}
window.applyAllDashboardFilters = applyAllDashboardFilters;

async function loadDashboardData(runId = '', isInitialLoad = false) {
    try {
        await loadRunsHistory(runId, isInitialLoad);
        const url = runId ? `${BASE_URL}/api/dashboard?run_id=${encodeURIComponent(runId)}` : `${BASE_URL}/api/dashboard`;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        const response = await fetchWithRetry(url, { signal: controller.signal }, isInitialLoad ? 5 : 3, 500);
        clearTimeout(timeoutId);

        if (!response || !response.ok) {
            if (!isInitialLoad) console.warn('Dashboard: resposta não-ok do servidor');
            return;
        }
        const data = await response.json();
        lastDashboardData = data;
        currentRawFeedData = data.feed || [];

        // Ao trocar de extração, sempre começa pela visão consolidada
        currentDashboardFilter = { network: 'ALL', term: 'ALL' };
        document.querySelectorAll('#dashNetworkPills .dash-net-pill').forEach(pill => {
            pill.classList.toggle('active', pill.getAttribute('data-net') === 'ALL');
        });
        const feedNetworkFilter = document.getElementById('feedNetworkFilter');
        if (feedNetworkFilter) feedNetworkFilter.value = 'ALL';
        const feedSearchInput = document.getElementById('feedSearchInput');
        if (feedSearchInput) feedSearchInput.value = '';
        activeWordCloudFilter = null;

        const netCounts = { ALL: currentRawFeedData.length, INSTAGRAM: 0, TIKTOK: 0, X: 0, YOUTUBE: 0, FACEBOOK: 0 };
        const termCounts = {};
        currentRawFeedData.forEach(item => {
            const key = normalizeNetKey(item.network);
            if (key in netCounts) netCounts[key]++;
            const term = (item.specific_term || item.keyword || '').trim();
            if (term) termCounts[term] = (termCounts[term] || 0) + 1;
        });

        const pillIds = { ALL: 'pillCountAll', INSTAGRAM: 'pillCountInsta', TIKTOK: 'pillCountTikTok', X: 'pillCountX', YOUTUBE: 'pillCountYT', FACEBOOK: 'pillCountFB' };
        Object.entries(pillIds).forEach(([key, id]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = netCounts[key];
        });

        const termSelect = document.getElementById('dashTermFilter');
        if (termSelect) {
            termSelect.innerHTML = '';
            const allOpt = document.createElement('option');
            allOpt.value = 'ALL';
            allOpt.textContent = `Todos os termos (${currentRawFeedData.length})`;
            termSelect.appendChild(allOpt);
            Object.keys(termCounts).sort((a, b) => termCounts[b] - termCounts[a]).forEach(term => {
                const opt = document.createElement('option');
                opt.value = term;
                opt.textContent = `${term} (${termCounts[term]})`;
                termSelect.appendChild(opt);
            });
            termSelect.value = 'ALL';
        }

        renderReportHeader(data);
        renderWordCloud(data.wordcloud, null);
        applyAllDashboardFilters(true);
        loadCommentsSummary(data.run?.run_id || '');
    } catch (error) {
        if (error.name === 'AbortError') {
            console.warn('Dashboard: timeout ao carregar dados (servidor pode estar ocupado com extração)');
        } else {
            console.error('Dashboard load error:', error);
        }
        if (!isInitialLoad && error.name !== 'AbortError') {
            showToast('Erro ao carregar dados do dashboard', 'error');
        }
    }
}

let activeWordCloudFilter = null;
let currentWordCloudData = [];

function renderWordCloud(words, selectedWord = activeWordCloudFilter) {
    activeWordCloudFilter = selectedWord;
    if (words) {
        currentWordCloudData = words;
    } else {
        words = currentWordCloudData;
    }

    const canvas = document.getElementById('wordCloudCanvas');
    const placeholder = document.getElementById('wordCloudPlaceholder');
    const img = document.getElementById('wordCloudImg');
    if (!canvas) return;

    if (!words || words.length === 0) {
        if (placeholder) placeholder.style.display = 'flex';
        if (img) {
            img.classList.add('hidden');
            img.style.display = 'none';
        }
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    if (placeholder) placeholder.style.display = 'none';

    // 1. Calculate responsive dimensions based on container
    const container = document.getElementById('wordCloudContainer');
    const containerRect = container ? container.getBoundingClientRect() : null;
    const clientW = container ? container.clientWidth - 16 : 800;
    const width = Math.max(300, Math.floor(containerRect && containerRect.width > 50 ? (containerRect.width - 20) : clientW));
    const height = 185;

    // HiDPI / Retina Crisp rendering (scale by devicePixelRatio, capped at 2 for optimal performance)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    // 2. TRANSPARENT BACKGROUND (Fundo 100% transparente para permitir uso em qualquer layout/slide)
    ctx.clearRect(0, 0, width, height);

    const isDark = document.documentElement.classList.contains('dark');
    // Escala de cores: usa paleta customizada se definida no Estúdio, ou degradê institucional Cobalto EBM
    let ramp = isDark
        ? ['#60A5FA', '#93C5FD', '#3B82F6', '#BFDBFE', '#38BDF8']
        : ['#1D4ED8', '#2563EB', '#3B82F6', '#60A5FA', '#1E3A8A'];
    if (activeDashboardWordCloudConfig && activeDashboardWordCloudConfig.paletteName) {
        const palName = activeDashboardWordCloudConfig.paletteName;
        if (palName === 'custom' && Array.isArray(activeDashboardWordCloudConfig.customColors) && activeDashboardWordCloudConfig.customColors.length > 0) {
            ramp = activeDashboardWordCloudConfig.customColors;
        } else {
            ramp = isDark
                ? (STUDIO_PALETTES_DARK[palName] || STUDIO_PALETTES_DARK.cobalt)
                : (STUDIO_PALETTES[palName] || STUDIO_PALETTES.cobalt);
        }
    }

    const maxWeight = Math.max(...words.map(w => w.weight || 1));
    const minWeight = Math.min(...words.map(w => w.weight || 1));

    // Sort words by weight descending (biggest words first in center)
    const sortedWords = [...words].sort((a, b) => (b.weight || 1) - (a.weight || 1));

    const centerX = width / 2;
    const centerY = height / 2;
    
    // Track occupied bounding boxes to prevent overlapping
    const placedBoxes = [];
    const wordHitboxes = [];

    sortedWords.forEach((item, index) => {
        const count = item.weight || 1;
        
        let fontSize;
        let scaleRatio;
        if (maxWeight === minWeight) {
            fontSize = 24;
            scaleRatio = 0.5;
        } else {
            // Escala logarítmica com amortecimento para garantir legibilidade dos termos secundários
            const logMin = Math.log(minWeight + 1);
            const logMax = Math.log(maxWeight + 1);
            scaleRatio = (Math.log(count + 1) - logMin) / (logMax - logMin || 1);
            fontSize = Math.round(14 + scaleRatio * 32);
        }

        let color = ramp[Math.min(ramp.length - 1, Math.floor(scaleRatio * ramp.length))];

        // Palavra selecionada em destaque; demais esmaecidas
        if (selectedWord) {
            const isSelected = item.text.toLowerCase() === selectedWord.toLowerCase();
            color = isSelected ? (isDark ? '#c7cdfd' : '#3730a3') : 'rgba(100, 116, 139, 0.35)';
        }

        const fontFamily = (activeDashboardWordCloudConfig && activeDashboardWordCloudConfig.fontFamily)
            ? activeDashboardWordCloudConfig.fontFamily
            : "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif";
        const isSelected = selectedWord && item.text.toLowerCase() === selectedWord.toLowerCase();
        const fontWeight = (activeDashboardWordCloudConfig && activeDashboardWordCloudConfig.fontWeight)
            ? activeDashboardWordCloudConfig.fontWeight
            : (isSelected ? "900" : (fontSize > 28 ? "800" : (fontSize > 18 ? "700" : "600")));

        const angle = activeDashboardWordCloudConfig
            ? getWordStudioAngle(activeDashboardWordCloudConfig.angleMode, index, activeDashboardWordCloudConfig.seed || 1)
            : 0;

        ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
        const metrics = ctx.measureText(item.text);
        const textW = metrics.width;
        const textH = fontSize * 1.1;

        let boxW = textW;
        let boxH = textH;
        if (Math.abs(angle - Math.PI / 2) < 0.01) {
            boxW = textH;
            boxH = textW;
        } else if (Math.abs(angle) > 0.01) {
            const diag = (textW + textH) * 0.7071;
            boxW = diag;
            boxH = diag;
        }

        // Concentric Elliptical Archimedean Spiral packing adaptada à proporção do card
        const aspect = Math.max(1.2, Math.min(3.2, width / (height || 1)));
        const pad = (activeDashboardWordCloudConfig && activeDashboardWordCloudConfig.padding) || 3;

        let placed = false;
        let spiralAngle = (index * 137.5) * (Math.PI / 180);
        let radius = 0;
        let step = 0;
        const maxSteps = 550;

        while (!placed && step < maxSteps) {
            const posX = centerX + (radius * aspect * 0.88) * Math.cos(spiralAngle);
            const posY = centerY + radius * Math.sin(spiralAngle);

            const testBox = {
                left: posX - boxW / 2 - pad,
                right: posX + boxW / 2 + pad,
                top: posY - boxH / 2 - pad,
                bottom: posY + boxH / 2 + pad
            };

            let fitsCanvas = testBox.left >= 0 && testBox.right <= width && testBox.top >= 0 && testBox.bottom <= height;
            if (fitsCanvas && activeDashboardWordCloudConfig) {
                fitsCanvas = doesBoxFitStudioShape(testBox, width, height, activeDashboardWordCloudConfig.shape, activeDashboardWordCloudConfig.invertShape);
            }
            
            let overlaps = false;
            if (fitsCanvas) {
                for (let b of placedBoxes) {
                    if (!(testBox.right < b.left || testBox.left > b.right || testBox.bottom < b.top || testBox.top > b.bottom)) {
                        overlaps = true;
                        break;
                    }
                }
            } else {
                overlaps = true;
            }

            if (!overlaps) {
                placedBoxes.push(testBox);
                wordHitboxes.push({
                    text: item.text,
                    count: count,
                    box: testBox
                });

                ctx.save();
                ctx.translate(posX, posY);
                if (angle !== 0) ctx.rotate(angle);
                ctx.fillStyle = color;
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillText(item.text, 0, 0);
                ctx.restore();
                placed = true;
            }

            spiralAngle += 0.26;
            radius += 1.15;
            step++;
        }
    });

    // 3. Sync to <img> element with transparent PNG source
    // When the user right-clicks on <img> and clicks "Copiar imagem", the browser copies the true transparent PNG data
    // without the blank/empty bugs that happen when copying raw <canvas>!
    if (img) {
        img.src = canvas.toDataURL('image/png');
        img.style.width = `${width}px`;
        img.style.height = `${height}px`;
        img.classList.remove('hidden');
        img.style.display = 'block';

        // Add interactivity directly on image (hover cursor & click to toggle filter)
        img.onmousemove = (e) => {
            const rect = img.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            let hovering = false;
            for (let item of wordHitboxes) {
                if (mouseX >= item.box.left && mouseX <= item.box.right && mouseY >= item.box.top && mouseY <= item.box.bottom) {
                    img.style.cursor = 'pointer';
                    hovering = true;
                    break;
                }
            }
            if (!hovering) {
                img.style.cursor = 'default';
            }
        };

        img.onclick = (e) => {
            const rect = img.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            for (let item of wordHitboxes) {
                if (mouseX >= item.box.left && mouseX <= item.box.right && mouseY >= item.box.top && mouseY <= item.box.bottom) {
                    const feedSearch = document.getElementById('feedSearchInput');
                    if (feedSearch) {
                        if (activeWordCloudFilter && activeWordCloudFilter.toLowerCase() === item.text.toLowerCase()) {
                            // TOGGLE OFF: Clicked active word again -> reset filter and colors to normal
                            activeWordCloudFilter = null;
                            feedSearch.value = '';
                            filterDashboardFeedTable();
                            renderWordCloud(currentWordCloudData, null);
                            showToast('Filtro por palavra removido', 'info');
                        } else {
                            // TOGGLE ON: Clicked new word -> highlight word, dim others, and filter feed
                            activeWordCloudFilter = item.text;
                            feedSearch.value = item.text;
                            filterDashboardFeedTable();
                            renderWordCloud(currentWordCloudData, item.text);
                            showToast(`Filtrando feed por "${item.text}" (${item.count} menções)`, 'info');
                        }
                    }
                    break;
                }
            }
        };
    }
}

// --- WORD CLOUD EXPORT & CLIPBOARD TOOLS ---
async function copyWordCloudImage(mode = 'transparent') {
    const canvas = document.getElementById('wordCloudCanvas');
    if (!canvas) {
        showToast('Nuvem de palavras não encontrada', 'error');
        return;
    }

    const copyBtn = mode === 'whatsapp'
        ? document.getElementById('btnCopyWordCloudCard')
        : document.getElementById('btnCopyWordCloud');
    const originalHtml = copyBtn ? copyBtn.innerHTML : '';

    try {
        if (copyBtn) {
            copyBtn.disabled = true;
            copyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Copiando...</span>';
        }

        // Target canvas to export
        let exportCanvas = canvas;

        if (mode === 'whatsapp') {
            // Create an offscreen canvas with a clean, executive background card
            // So pasting directly into WhatsApp (Ctrl+V) displays a beautiful, professional card
            const offscreen = document.createElement('canvas');
            offscreen.width = canvas.width;
            offscreen.height = canvas.height;
            const offCtx = offscreen.getContext('2d');

            const isDark = document.documentElement.classList.contains('dark');
            offCtx.fillStyle = isDark ? '#161618' : '#ffffff';
            offCtx.fillRect(0, 0, offscreen.width, offscreen.height);

            // Draw subtle card border
            offCtx.strokeStyle = isDark ? '#323238' : '#e2e8f0';
            offCtx.lineWidth = 4;
            offCtx.strokeRect(2, 2, offscreen.width - 4, offscreen.height - 4);

            // Draw the word cloud
            offCtx.drawImage(canvas, 0, 0);
            exportCanvas = offscreen;
        }

        // Use modern Clipboard API to copy high-res PNG
        if (navigator.clipboard && window.ClipboardItem) {
            exportCanvas.toBlob(async (blob) => {
                if (!blob) {
                    if (copyBtn) {
                        copyBtn.disabled = false;
                        copyBtn.innerHTML = originalHtml;
                    }
                    showToast('Erro ao capturar imagem da nuvem', 'error');
                    return;
                }
                try {
                    await navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': blob })
                    ]);
                    if (copyBtn) {
                        copyBtn.innerHTML = '<i class="fa-solid fa-check text-emerald-600"></i> <span>Copiado!</span>';
                        setTimeout(() => {
                            copyBtn.disabled = false;
                            copyBtn.innerHTML = originalHtml;
                        }, 2200);
                    }
                    const msg = mode === 'whatsapp'
                        ? 'Card para WhatsApp copiado. Cole com Ctrl+V'
                        : 'Nuvem copiada com fundo transparente. Cole com Ctrl+V';
                    showToast(msg, 'success');
                } catch (clipErr) {
                    console.warn('Clipboard write failed, fallback to download:', clipErr);
                    downloadWordCloudImage();
                    if (copyBtn) {
                        copyBtn.disabled = false;
                        copyBtn.innerHTML = originalHtml;
                    }
                    showToast('Imagem baixada em PNG', 'info');
                }
            }, 'image/png');
        } else {
            // Fallback for older browsers
            downloadWordCloudImage();
            if (copyBtn) {
                copyBtn.disabled = false;
                copyBtn.innerHTML = originalHtml;
            }
            showToast('Imagem baixada em PNG', 'info');
        }
    } catch (err) {
        console.error('Error copying word cloud:', err);
        if (copyBtn) {
            copyBtn.disabled = false;
            copyBtn.innerHTML = originalHtml;
        }
        showToast('Não foi possível copiar a imagem', 'error');
    }
}
window.copyWordCloudImage = copyWordCloudImage;

function downloadWordCloudImage() {
    const canvas = document.getElementById('wordCloudCanvas');
    if (!canvas) return;

    try {
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `nuvem_de_palavras_transparente_${timestamp}.png`;
        link.href = canvas.toDataURL('image/png');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast('Download da imagem PNG iniciado', 'success');
    } catch (e) {
        console.error('Error downloading word cloud:', e);
        showToast('Erro ao baixar imagem da nuvem', 'error');
    }
}
window.downloadWordCloudImage = downloadWordCloudImage;

function toggleWordCloudExportMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('wordCloudExportMenu');
    if (!menu) return;
    const isHidden = menu.classList.contains('hidden');
    document.querySelectorAll('[id$="ExportMenu"]').forEach(m => m.classList.add('hidden'));
    if (isHidden) {
        menu.classList.remove('hidden');
    } else {
        menu.classList.add('hidden');
    }
}
window.toggleWordCloudExportMenu = toggleWordCloudExportMenu;

function closeWordCloudExportMenu() {
    const menu = document.getElementById('wordCloudExportMenu');
    if (menu) menu.classList.add('hidden');
}
window.closeWordCloudExportMenu = closeWordCloudExportMenu;

document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('wordCloudExportDropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        closeWordCloudExportMenu();
    }
});


// =========================================================================
// WORD CLOUD STUDIO (ESTÚDIO DA NUVEM DE PALAVRAS)
// =========================================================================

const COMMON_MULTILINGUAL_STOPWORDS = new Set([
    // Português
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma',
    'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele',
    'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já',
    'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era',
    'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas', 'me', 'esse', 'eles',
    'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha',
    'têm', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe',
    'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos',
    'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas',
    'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas',
    'isto', 'aquilo', 'estou', 'estamos', 'estive', 'esteve', 'estivemos', 'estiveram',
    'estava', 'estávamos', 'estavam', 'pra', 'pro', 'vc', 'vcs', 'q', 'tb', 'tbm', 'pq',
    'ne', 'ta', 'eh', 'ja', 'so', 'sobre', 'sob', 'aqui', 'la', 'hj', 'hoje', 'agora',
    'tudo', 'todo', 'toda', 'todos', 'todas', 'fazer', 'vai', 'vou', 'dar', 'ver', 'ter',
    'bom', 'bem', 'muita', 'muitos', 'muitas', 'nada', 'cada', 'outro', 'outra', 'outros',
    'outras', 'onde', 'quais', 'enquanto', 'assim', 'entao', 'ainda', 'sempre', 'nunca',
    'desde', 'sim', 'nao', 'dia', 'dias', 'vez', 'vezes', 'parte', 'forma', 'modo',
    'gente', 'vida', 'coisa', 'coisas', 'tempo', 'amigo', 'amiga', 'amigos', 'amigas',
    'valeu', 'legal', 'verdade', 'obrigado', 'obrigada', 'novo', 'nova', 'novos', 'novas',
    'foto', 'video', 'vídeo', 'reel', 'reels', 'post', 'feed', 'story', 'stories', 'fyp',

    // Espanhol
    'los', 'las', 'del', 'una', 'uno', 'unos', 'unas', 'con', 'por', 'para', 'sin', 'sobre',
    'tras', 'hasta', 'desde', 'hacia', 'entre', 'contra', 'según', 'segun', 'durante',
    'que', 'qué', 'pero', 'mas', 'más', 'porque', 'pues', 'como', 'cómo', 'cuando', 'cuándo',
    'donde', 'dónde', 'quien', 'quién', 'quienes', 'quiénes', 'cual', 'cuál', 'cuales', 'cuáles',
    'les', 'nos', 'ellos', 'ellas', 'usted', 'ustedes', 'nosotros', 'nosotras', 'vosotros', 'vosotras',
    'mio', 'mía', 'mia', 'míos', 'mios', 'mías', 'mias', 'tuyo', 'tuya', 'tuyos', 'tuyas',
    'suyo', 'suya', 'suyos', 'suyas', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
    'son', 'soy', 'somos', 'era', 'eran', 'fue', 'fueron', 'sido', 'siendo', 'sea', 'sean',
    'estoy', 'está', 'esta', 'están', 'estan', 'estaba', 'estaban', 'estuvo', 'estuvieron',
    'estado', 'estando', 'esté', 'este', 'estén', 'esten', 'estamos',
    'tiene', 'tienen', 'tenía', 'tenia', 'tenían', 'tenian', 'tuvo', 'tuvieron', 'tenido',
    'teniendo', 'tengo', 'tenemos', 'tenga', 'tengan',
    'hay', 'había', 'habia', 'habían', 'habian', 'hubo', 'hubieron', 'habido', 'habiendo',
    'han', 'has', 'hemos', 'haya', 'hayan',
    'hace', 'hacen', 'hacía', 'hacia', 'hacían', 'hacian', 'hizo', 'hicieron', 'hecho', 'haciendo',
    'haga', 'hagan', 'hago', 'hacemos',
    'dice', 'dicen', 'decía', 'decia', 'decían', 'decian', 'dijo', 'dijeron', 'dicho', 'diciendo',
    'diga', 'digan', 'digo', 'decimos',
    'puede', 'pueden', 'podía', 'podia', 'podían', 'podian', 'pudo', 'pudieron', 'podido',
    'puedo', 'podemos', 'pueda', 'puedan',
    'van', 'iba', 'iban', 'ido', 'yendo', 'voy', 'vamos', 'vaya', 'vayan',
    'veo', 've', 'ven', 'veía', 'veia', 'veían', 'veian', 'vio', 'vieron', 'visto', 'viendo',
    'vea', 'vean', 'vemos',
    'dan', 'daba', 'daban', 'dio', 'dieron', 'dado', 'dando', 'doy', 'damos', 'den',
    'sabe', 'saben', 'sabía', 'sabia', 'sabían', 'sabian', 'supo', 'supieron', 'sabido', 'sabiendo',
    'sepa', 'sepan', 'sabemos',
    'quiere', 'quieren', 'quería', 'queria', 'querían', 'querian', 'quiso', 'quisieron',
    'querido', 'queriendo', 'quiero', 'queremos', 'quiera', 'quieran',
    'gusta', 'gustan', 'gustar', 'gustaba',
    'bien', 'mal', 'muy', 'mucho', 'mucha', 'muchos', 'muchas', 'poco', 'poca', 'pocos', 'pocas',
    'tanto', 'tanta', 'tantos', 'tantas', 'tan', 'solo', 'sólo', 'solamente', 'sola', 'solos', 'solas',
    'también', 'tambien', 'tampoco', 'jamás', 'jamas', 'nunca', 'siempre', 'aún', 'aun',
    'todavía', 'todavia', 'hoy', 'ayer', 'mañana', 'manana', 'ahora', 'antes', 'después', 'despues',
    'luego', 'pronto', 'tarde', 'temprano', 'aquí', 'aqui', 'acá', 'aca', 'ahí', 'ahi',
    'allí', 'alli', 'allá', 'alla', 'cerca', 'lejos',
    'todo', 'toda', 'todos', 'todas', 'nada', 'algo', 'alguien', 'nadie',
    'algún', 'algun', 'alguna', 'algunos', 'algunas', 'ningún', 'ningun', 'ninguna',
    'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas', 'cada',
    'cualquier', 'cualquiera',
    'día', 'dias', 'gracias', 'favor', 'porfa',
    'hola', 'adios', 'adiós', 'bueno', 'buena', 'buenos', 'buenas',

    // Inglês
    'the', 'and', 'to', 'of', 'in', 'for', 'on', 'with', 'is', 'by', 'at', 'this', 'that', 'from',
    'you', 'are', 'was', 'be', 'it', 'not', 'your', 'have', 'has', 'had', 'having',
    'they', 'them', 'their', 'theirs', 'one', 'two', 'three',
    'what', 'who', 'whom', 'whose', 'which', 'when', 'where', 'why', 'how',
    'all', 'any', 'some', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'such', 'no', 'nor', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'can', 'will', 'just', 'should', 'now', 'could', 'would', 'may', 'might', 'must',
    'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'under',
    'again', 'further', 'then', 'once', 'here', 'there', 'out', 'off', 'over', 'down',
    'been', 'being', 'were', 'does', 'did', 'doing',
    'like', 'get', 'got', 'getting', 'make', 'made', 'know', 'think', 'see', 'look', 'come', 'came',
    'take', 'took', 'want', 'give', 'good', 'well', 'much', 'many', 'people', 'time',
    'really', 'actually', 'even', 'back', 'way', 'also', 'please', 'thanks', 'thank',
    'dont', 'wont', 'cant', 'didnt', 'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent'
]);

const COMMON_PORTUGUESE_STOPWORDS = COMMON_MULTILINGUAL_STOPWORDS;


const STUDIO_PALETTES = {
    cobalt: ['#1D4ED8', '#2563EB', '#3B82F6', '#60A5FA', '#1E3A8A'],
    quintto_gold: ['#1D4ED8', '#C2410C', '#D97706', '#B45309', '#1E3A8A'],
    slate: ['#0F172A', '#334155', '#475569', '#64748B', '#94A3B8'],
    sunset: ['#BE123C', '#E11D48', '#F97316', '#FBBF24', '#881337'],
    forest: ['#065F46', '#047857', '#10B981', '#34D399', '#064E3B'],
    terracotta: ['#9A3412', '#C2410C', '#D97706', '#B45309', '#78350F'],
    wine: ['#9A3412', '#C2410C', '#D97706', '#B45309', '#78350F'], // alias de compatibilidade com tons neutros
    cyber: ['#0284C7', '#0EA5E9', '#06B6D4', '#14B8A6', '#0369A1'],
    mono: ['#111827', '#1F2937', '#374151', '#4B5563', '#6B7280']
};

const STUDIO_PALETTES_DARK = {
    cobalt: ['#60A5FA', '#93C5FD', '#3B82F6', '#BFDBFE', '#38BDF8'],
    quintto_gold: ['#60A5FA', '#FB923C', '#FBBF24', '#F59E0B', '#93C5FD'],
    slate: ['#E2E8F0', '#CBD5E1', '#94A3B8', '#64748B', '#F1F5F9'],
    sunset: ['#FB7185', '#FDA4AF', '#F43F5E', '#FB923C', '#FDE047'],
    forest: ['#34D399', '#6EE7B7', '#10B981', '#A7F3D0', '#4ADE80'],
    terracotta: ['#F97316', '#FB923C', '#FBBF24', '#EA580C', '#FED7AA'],
    wine: ['#F97316', '#FB923C', '#FBBF24', '#EA580C', '#FED7AA'], // alias
    cyber: ['#38BDF8', '#22D3EE', '#2DD4BF', '#7DD3FC', '#67E8F9'],
    mono: ['#F8FAFC', '#E2E8F0', '#CBD5E1', '#94A3B8', '#64748B']
};

const STUDIO_PRESETS = {
    executive_deck: {
        name: 'Apresentação Executiva',
        shape: '16x9',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        fontWeight: '800',
        minFontSize: 14,
        maxFontSize: 48,
        scaleCurve: 'linear',
        angleMode: 'horizontal',
        paletteName: 'cobalt',
        colorMode: 'frequency',
        bgMode: 'transparent',
        padding: 4,
        maxWords: 50
    },
    whatsapp_card: {
        name: 'Card Social & WhatsApp',
        shape: '1x1',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        fontWeight: '900',
        minFontSize: 14,
        maxFontSize: 44,
        scaleCurve: 'log',
        angleMode: 'pred_horiz',
        paletteName: 'cobalt',
        colorMode: 'top1_highlight',
        bgMode: 'alabaster',
        padding: 3,
        maxWords: 40
    },
    social_buzz: {
        name: 'Social Listening & Depoimentos',
        shape: 'speech',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'Inter', system-ui, sans-serif",
        fontWeight: '800',
        minFontSize: 13,
        maxFontSize: 46,
        scaleCurve: 'linear',
        angleMode: 'crossed',
        paletteName: 'sunset',
        colorMode: 'frequency',
        bgMode: 'transparent',
        padding: 4,
        maxWords: 45
    },
    awards_star: {
        name: 'Top Destaques & Premiações',
        shape: 'star',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'Montserrat', system-ui, sans-serif",
        fontWeight: '800',
        minFontSize: 12,
        maxFontSize: 40,
        scaleCurve: 'linear',
        angleMode: 'pred_horiz',
        paletteName: 'quintto_gold',
        colorMode: 'frequency',
        bgMode: 'dark',
        padding: 3,
        maxWords: 35
    },
    editorial_serif: {
        name: 'Serifado Editorial',
        shape: 'cloud',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'Newsreader', Georgia, serif",
        fontWeight: '600',
        minFontSize: 15,
        maxFontSize: 48,
        scaleCurve: 'linear',
        angleMode: 'horizontal',
        paletteName: 'mono',
        colorMode: 'frequency',
        bgMode: 'ivory',
        padding: 5,
        maxWords: 40
    },
    tech_data: {
        name: 'Tech & Governança',
        shape: 'hexagon',
        invertShape: false,
        drawShapeOutline: false,
        fontFamily: "'JetBrains Mono', monospace",
        fontWeight: '800',
        minFontSize: 13,
        maxFontSize: 44,
        scaleCurve: 'linear',
        angleMode: 'crossed',
        paletteName: 'slate',
        colorMode: 'frequency',
        bgMode: 'dark',
        padding: 3,
        maxWords: 50
    }
};

const DEFAULT_STUDIO_WORDS = [
    { text: 'Fortaleza', weight: 85, enabled: true },
    { text: 'Inovação', weight: 64, enabled: true },
    { text: 'Comunidade', weight: 58, enabled: true },
    { text: 'Saúde', weight: 52, enabled: true },
    { text: 'Cultura', weight: 46, enabled: true },
    { text: 'Tecnologia', weight: 43, enabled: true },
    { text: 'Qualidade', weight: 39, enabled: true },
    { text: 'Atendimento', weight: 37, enabled: true },
    { text: 'Comércio', weight: 34, enabled: true },
    { text: 'Eventos', weight: 32, enabled: true },
    { text: 'Segurança', weight: 30, enabled: true },
    { text: 'Futuro', weight: 28, enabled: true },
    { text: 'Gestão', weight: 27, enabled: true },
    { text: 'Projetos', weight: 25, enabled: true },
    { text: 'Turismo', weight: 24, enabled: true },
    { text: 'Educação', weight: 22, enabled: true },
    { text: 'Sustentabilidade', weight: 20, enabled: true },
    { text: 'Transformação', weight: 19, enabled: true },
    { text: 'Resultados', weight: 18, enabled: true },
    { text: 'Conexão', weight: 17, enabled: true },
    { text: 'Desenvolvimento', weight: 16, enabled: true }
];

let wordCloudStudioState = {
    words: [],
    shape: '16x9',
    invertShape: false,
    drawShapeOutline: false,
    fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
    fontWeight: '800',
    minFontSize: 14,
    maxFontSize: 46,
    scaleCurve: 'linear',
    angleMode: 'horizontal',
    padding: 4,
    maxWords: 50,
    paletteName: 'cobalt',
    customColors: ['#1D4ED8', '#2563EB', '#3B82F6', '#60A5FA', '#93C5FD'],
    colorMode: 'frequency',
    bgMode: 'transparent',
    seed: 1,
    zoom: 1.0,
    previewBgCycle: 'adaptive', // 'adaptive' | 'dark' | 'light' | 'solid_white' | 'solid_dark'
    filterQuery: '',
    sortKey: 'weight',
    sortAsc: false
};

let studioLastRenderedBoxes = [];
let studioLastPlacedWordTexts = new Set();
let studioInteractivitySetup = false;
let studioKeyboardListenerSetup = false;
let activeDashboardWordCloudConfig = null;
let studioPanX = 0;
let studioPanY = 0;
let studioIsDragging = false;
let studioDragStartX = 0;
let studioDragStartY = 0;
let studioDragDistance = 0;
let studioTextInputDebounce = null;

function isPointInsideStudioShape(x, y, w, h, shape, invert) {
    const nx = (x - w / 2) / (w / 2);
    const ny = (y - h / 2) / (h / 2);
    let inside = true;

    if (shape === '16x9') {
        inside = Math.abs(nx) <= 0.94 && Math.abs(ny) <= 0.94;
    } else if (shape === '1x1') {
        const minSide = Math.min(w, h);
        inside = Math.abs(x - w / 2) <= (minSide * 0.46) && Math.abs(y - h / 2) <= (minSide * 0.46);
    } else if (shape === '9x16') {
        inside = Math.abs(nx) <= 0.92 && Math.abs(ny) <= 0.94;
    } else if (shape === 'circle') {
        inside = (nx * nx + ny * ny) <= 0.90;
    } else if (shape === 'speech') {
        const body = Math.abs(nx) <= 0.88 && ny >= -0.85 && ny <= 0.52;
        const tail = (nx >= -0.65 && nx <= -0.15 && ny >= 0.52 && ny <= 0.92 && (ny - 0.52) <= (0.40) * (1 - (nx + 0.65) / 0.50));
        inside = body || tail;
    } else if (shape === 'heart') {
        const px = nx * 1.15;
        const py = -ny * 1.15 + 0.25;
        inside = ((px * px + py * py - 1) ** 3 - px * px * py * py * py) <= 0;
    } else if (shape === 'cloud') {
        const b1 = (nx / 0.85) ** 2 + ((ny - 0.1) / 0.45) ** 2 <= 1;
        const c1 = (nx / 0.45) ** 2 + ((ny + 0.2) / 0.45) ** 2 <= 1;
        const c2 = ((nx + 0.4) / 0.35) ** 2 + ((ny + 0.05) / 0.35) ** 2 <= 1;
        const c3 = ((nx - 0.45) / 0.38) ** 2 + ((ny + 0.08) / 0.38) ** 2 <= 1;
        inside = b1 || c1 || c2 || c3;
    } else if (shape === 'star') {
        const pts = [];
        for (let i = 0; i < 10; i++) {
            const ang = i * (Math.PI / 5) - Math.PI / 2;
            const r = (i % 2 === 0) ? 0.94 : 0.60;
            pts.push({ x: r * Math.cos(ang), y: r * Math.sin(ang) });
        }
        let c = false;
        let j = pts.length - 1;
        for (let i = 0; i < pts.length; i++) {
            if (((pts[i].y > ny) !== (pts[j].y > ny)) &&
                (nx < (pts[j].x - pts[i].x) * (ny - pts[i].y) / (pts[j].y - pts[i].y) + pts[i].x)) {
                c = !c;
            }
            j = i;
        }
        inside = c;
    } else if (shape === 'shield') {
        if (ny < -0.88 || ny > 0.92 || Math.abs(nx) > 0.85) {
            inside = false;
        } else if (ny <= 0.1) {
            inside = true;
        } else {
            const limit = 0.85 * (1.0 - Math.pow((ny - 0.1) / 0.82, 1.8));
            inside = Math.abs(nx) <= limit;
        }
    } else if (shape === 'trophy') {
        const cup = Math.abs(nx) <= 0.62 && ny >= -0.85 && ny <= 0.05;
        const handles = Math.abs(nx) >= 0.50 && Math.abs(nx) <= 0.88 && ny >= -0.75 && ny <= -0.15 &&
                        !(Math.abs(nx) >= 0.62 && Math.abs(nx) <= 0.76 && ny >= -0.65 && ny <= -0.25);
        const stem = Math.abs(nx) <= 0.18 && ny > 0.05 && ny <= 0.55;
        const base = Math.abs(nx) <= 0.70 && ny > 0.55 && ny <= 0.88;
        inside = cup || handles || stem || base;
    } else if (shape === 'hexagon') {
        inside = Math.abs(nx) <= 0.85 && (Math.abs(nx) * 0.5 + Math.abs(ny) * 0.866) <= 0.82;
    }

    if (invert) return !inside;
    return inside;
}

function doesBoxFitStudioShape(box, w, h, shape, invert) {
    const pts = [
        { x: box.left, y: box.top },
        { x: box.right, y: box.top },
        { x: box.left, y: box.bottom },
        { x: box.right, y: box.bottom },
        { x: (box.left + box.right) / 2, y: (box.top + box.bottom) / 2 },
        { x: (box.left + box.right) / 2, y: box.top },
        { x: (box.left + box.right) / 2, y: box.bottom },
        { x: box.left, y: (box.top + box.bottom) / 2 },
        { x: box.right, y: (box.top + box.bottom) / 2 }
    ];
    for (let p of pts) {
        if (p.x < 2 || p.x > w - 2 || p.y < 2 || p.y > h - 2) return false;
        if (!isPointInsideStudioShape(p.x, p.y, w, h, shape, invert)) return false;
    }
    return true;
}

function getWordStudioAngle(angleMode, index, seed) {
    if (index === 0) return 0; // Termo líder sempre horizontal para legibilidade executiva
    if (angleMode === 'horizontal') return 0;
    if (angleMode === 'pred_horiz') {
        // ~85% horizontal, 15% vertical com multiplicador coprimo
        const r = (index * 5 + (seed || 1)) % 7;
        return (r === 1) ? (Math.PI / 2) : 0;
    }
    if (angleMode === 'mixed') return (index % 4 === 1) ? (Math.PI / 2) : 0;
    if (angleMode === 'crossed') {
        const r = (index * 5 + (seed || 1)) % 5;
        if (r === 1) return Math.PI / 4;
        if (r === 2) return Math.PI / 2;
        return 0;
    }
    if (angleMode === 'free') {
        const r = (index * 5 + (seed || 1)) % 6;
        if (r === 1) return -Math.PI / 4;
        if (r === 2) return Math.PI / 4;
        return 0;
    }
    return 0;
}

function drawStudioShapeOutline(ctx, width, height, shape, scale = 1, isDarkBg = false, outlineColor = null) {
    ctx.save();
    ctx.lineWidth = Math.max(1.5, 2 * scale);
    ctx.strokeStyle = outlineColor || (isDarkBg ? 'rgba(96, 165, 250, 0.40)' : 'rgba(29, 78, 216, 0.35)');
    ctx.setLineDash([6 * scale, 4 * scale]);

    const w = width;
    const h = height;
    const cx = w / 2;
    const cy = h / 2;

    ctx.beginPath();
    if (shape === '16x9') {
        const rw = w * 0.94;
        const rh = h * 0.94;
        if (typeof ctx.roundRect === 'function') ctx.roundRect(cx - rw / 2, cy - rh / 2, rw, rh, 12 * scale);
        else ctx.rect(cx - rw / 2, cy - rh / 2, rw, rh);
    } else if (shape === '1x1') {
        const side = Math.min(w, h) * 0.92;
        if (typeof ctx.roundRect === 'function') ctx.roundRect(cx - side / 2, cy - side / 2, side, side, 12 * scale);
        else ctx.rect(cx - side / 2, cy - side / 2, side, side);
    } else if (shape === '9x16') {
        const rw = w * 0.92;
        const rh = h * 0.94;
        if (typeof ctx.roundRect === 'function') ctx.roundRect(cx - rw / 2, cy - rh / 2, rw, rh, 12 * scale);
        else ctx.rect(cx - rw / 2, cy - rh / 2, rw, rh);
    } else if (shape === 'circle') {
        ctx.arc(cx, cy, Math.min(w, h) * 0.46, 0, Math.PI * 2);
    } else if (shape === 'speech') {
        const bw = w * 0.88;
        const bh = h * 0.68;
        const bx = cx - bw / 2;
        const by = cy - bh / 2 - h * 0.08;
        if (typeof ctx.roundRect === 'function') ctx.roundRect(bx, by, bw, bh, 14 * scale);
        else ctx.rect(bx, by, bw, bh);
        ctx.moveTo(cx - w * 0.25, by + bh);
        ctx.lineTo(cx - w * 0.45, by + bh + h * 0.22);
        ctx.lineTo(cx - w * 0.05, by + bh);
    } else if (shape === 'heart') {
        const topY = cy - h * 0.35;
        ctx.moveTo(cx, cy + h * 0.40);
        ctx.bezierCurveTo(cx - w * 0.45, cy + h * 0.10, cx - w * 0.48, topY, cx - w * 0.24, topY);
        ctx.bezierCurveTo(cx - w * 0.05, topY, cx, cy - h * 0.15, cx, cy - h * 0.15);
        ctx.bezierCurveTo(cx, cy - h * 0.15, cx + w * 0.05, topY, cx + w * 0.24, topY);
        ctx.bezierCurveTo(cx + w * 0.48, topY, cx + w * 0.45, cy + h * 0.10, cx, cy + h * 0.40);
    } else if (shape === 'cloud') {
        ctx.arc(cx, cy + h * 0.08, w * 0.38, 0, Math.PI * 2);
        ctx.arc(cx - w * 0.20, cy - h * 0.04, w * 0.22, 0, Math.PI * 2);
        ctx.arc(cx + w * 0.20, cy - h * 0.04, w * 0.24, 0, Math.PI * 2);
        ctx.arc(cx, cy - h * 0.15, w * 0.25, 0, Math.PI * 2);
    } else if (shape === 'star') {
        const minSide = Math.min(w, h);
        for (let i = 0; i < 10; i++) {
            const ang = i * (Math.PI / 5) - Math.PI / 2;
            const r = (i % 2 === 0) ? (minSide * 0.47) : (minSide * 0.30);
            const px = cx + r * Math.cos(ang);
            const py = cy + r * Math.sin(ang);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();
    } else if (shape === 'shield') {
        const top = cy - h * 0.44;
        const bottom = cy + h * 0.46;
        const left = cx - w * 0.42;
        const right = cx + w * 0.42;
        const midY = cy + h * 0.05;
        ctx.moveTo(left, top);
        ctx.lineTo(right, top);
        ctx.lineTo(right, midY);
        ctx.bezierCurveTo(right, bottom - h * 0.15, cx + w * 0.15, bottom, cx, bottom);
        ctx.bezierCurveTo(cx - w * 0.15, bottom, left, bottom - h * 0.15, left, midY);
        ctx.closePath();
    } else if (shape === 'trophy') {
        ctx.moveTo(cx - w * 0.30, cy - h * 0.42);
        ctx.lineTo(cx + w * 0.30, cy - h * 0.42);
        ctx.lineTo(cx + w * 0.24, cy);
        ctx.bezierCurveTo(cx + w * 0.18, cy + h * 0.15, cx - w * 0.18, cy + h * 0.15, cx - w * 0.24, cy);
        ctx.closePath();
        ctx.rect(cx - w * 0.32, cy + h * 0.30, w * 0.64, h * 0.14);
    } else if (shape === 'hexagon') {
        const r = Math.min(w, h) * 0.46;
        for (let i = 0; i < 6; i++) {
            const ang = i * (Math.PI / 3);
            const px = cx + r * Math.cos(ang);
            const py = cy + r * Math.sin(ang);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();
    }

    ctx.stroke();
    ctx.restore();
}

function drawWordCloudToCanvas(canvas, wordsList, config, scale = 1, captureHitboxes = false) {
    if (!canvas) return { placedCount: 0, hitboxes: [], topWord: null, placedSet: new Set() };
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Fundo sólido se especificado (neutro conforme DIRETRIZES_UI_UX_ANTI_VIBE_CODE)
    if (config.bgMode === 'alabaster') {
        ctx.fillStyle = '#FAF8F5';
        ctx.fillRect(0, 0, width, height);
    } else if (config.bgMode === 'ivory') {
        ctx.fillStyle = '#F4F1EA';
        ctx.fillRect(0, 0, width, height);
    } else if (config.bgMode === 'dark') {
        ctx.fillStyle = '#161618';
        ctx.fillRect(0, 0, width, height);
    } else if (config.bgMode === 'slate_dark' || config.bgMode === 'navy') {
        ctx.fillStyle = '#26262B';
        ctx.fillRect(0, 0, width, height);
    } else if (config.bgMode === 'white') {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, width, height);
    }

    if (!wordsList || wordsList.length === 0) return { placedCount: 0, hitboxes: [], topWord: null, placedSet: new Set() };

    const isDarkBg = config.bgMode === 'dark' || config.bgMode === 'slate_dark' || config.bgMode === 'navy' || 
        (config.bgMode === 'transparent' && document.documentElement.classList.contains('dark'));
    let palette;
    if (config.paletteName === 'custom' && Array.isArray(config.customColors) && config.customColors.length > 0) {
        palette = config.customColors;
    } else {
        palette = isDarkBg 
            ? (STUDIO_PALETTES_DARK[config.paletteName] || STUDIO_PALETTES_DARK.cobalt)
            : (STUDIO_PALETTES[config.paletteName] || STUDIO_PALETTES.cobalt);
    }

    // Desenhar contorno sutil se habilitado
    if (config.drawShapeOutline) {
        drawStudioShapeOutline(ctx, width, height, config.shape, scale, isDarkBg, palette[0]);
    }

    const activeWords = wordsList
        .filter(w => w.enabled !== false && w.text && w.text.trim())
        .slice(0, config.maxWords || 50);

    if (activeWords.length === 0) return { placedCount: 0, hitboxes: [], topWord: null, placedSet: new Set() };

    const maxWeight = Math.max(...activeWords.map(w => w.weight || 1));
    const minWeight = Math.min(...activeWords.map(w => w.weight || 1));
    const sortedWords = [...activeWords].sort((a, b) => (b.weight || 1) - (a.weight || 1));
    const topWord = sortedWords[0] ? `${sortedWords[0].text} (${sortedWords[0].weight})` : null;

    const centerX = width / 2;
    const centerY = height / 2;
    const placedBoxes = [];
    const hitboxes = [];
    const placedSet = new Set();
    let placedCount = 0;

    const baseMinFont = (config.minFontSize || 14) * scale;
    const baseMaxFont = (config.maxFontSize || (config.shape === '1x1' ? 40 : 46)) * scale;
    const padding = (config.padding || 4) * scale;

    sortedWords.forEach((item, index) => {
        const count = item.weight || 1;
        let fontSize;
        if (maxWeight === minWeight) {
            fontSize = Math.round(24 * scale);
        } else {
            let ratio;
            if (config.scaleCurve === 'log') {
                const logMin = Math.log(minWeight + 1);
                const logMax = Math.log(maxWeight + 1);
                ratio = (Math.log(count + 1) - logMin) / (logMax - logMin || 1);
            } else {
                ratio = (count - minWeight) / (maxWeight - minWeight);
            }
            fontSize = Math.round(baseMinFont + ratio * (baseMaxFont - baseMinFont));
        }

        // Determinação de Cor
        let color;
        if (config.colorMode === 'top1_highlight') {
            if (index === 0) {
                color = isDarkBg ? '#60A5FA' : '#1D4ED8';
            } else {
                color = isDarkBg ? 'rgba(226, 232, 240, 0.75)' : 'rgba(71, 85, 105, 0.85)';
            }
        } else if (config.colorMode === 'cyclic') {
            color = palette[index % palette.length];
        } else {
            // frequency mode (hierárquico)
            const ratio = maxWeight === minWeight ? 0 : (count - minWeight) / (maxWeight - minWeight);
            const pIdx = Math.min(palette.length - 1, Math.floor((1 - ratio) * palette.length));
            color = palette[pIdx];
        }

        const angle = getWordStudioAngle(config.angleMode, index, config.seed || 1);

        let placed = false;
        let curFont = fontSize;
        let curPadding = padding;

        for (let pass = 0; pass < 3 && !placed; pass++) {
            if (pass === 1) {
                curFont = Math.max(Math.round(baseMinFont * 0.82), Math.round(fontSize * 0.80));
                curPadding = Math.max(1, padding - 1);
            } else if (pass === 2) {
                curFont = Math.max(Math.round(baseMinFont * 0.70), Math.round(fontSize * 0.64));
                curPadding = Math.max(1, padding - 2);
            }

            ctx.font = `${config.fontWeight || '800'} ${curFont}px ${config.fontFamily || "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"}`;
            const metrics = ctx.measureText(item.text);
            const textW = metrics.width;
            const textH = curFont * 1.1;

            let boxW = textW;
            let boxH = textH;
            if (Math.abs(angle - Math.PI / 2) < 0.01) {
                boxW = textH;
                boxH = textW;
            } else if (Math.abs(angle) > 0.01) {
                const diag = (textW + textH) * 0.7071;
                boxW = diag;
                boxH = diag;
            }

            let spiralAngle = (index * 137.5 + ((config.seed || 1) * 23) + pass * 35) * (Math.PI / 180);
            let radius = 0;
            let step = 0;
            const maxSteps = pass === 0 ? 700 : (pass === 1 ? 650 : 950);
            const stepAng = pass === 2 ? 0.16 : (pass === 1 ? 0.22 : 0.24);
            const aspect = (config.shape === '1x1') ? 1.0 : (width / height);

            while (!placed && step < maxSteps) {
                const posX = centerX + radius * aspect * Math.cos(spiralAngle);
                const posY = centerY + radius * Math.sin(spiralAngle);

                const testBox = {
                    left: posX - boxW / 2 - curPadding,
                    right: posX + boxW / 2 + curPadding,
                    top: posY - boxH / 2 - curPadding,
                    bottom: posY + boxH / 2 + curPadding
                };

                if (doesBoxFitStudioShape(testBox, width, height, config.shape, config.invertShape)) {
                    let overlaps = false;
                    for (let b of placedBoxes) {
                        if (!(testBox.right < b.left || testBox.left > b.right || testBox.bottom < b.top || testBox.top > b.bottom)) {
                            overlaps = true;
                            break;
                        }
                    }

                    if (!overlaps) {
                        placedBoxes.push(testBox);
                        placedSet.add(item.text);
                        if (captureHitboxes) {
                            hitboxes.push({
                                text: item.text,
                                weight: item.weight || 1,
                                rank: index + 1,
                                box: testBox,
                                scale: scale
                            });
                        }

                        ctx.save();
                        ctx.translate(posX, posY);
                        if (angle !== 0) ctx.rotate(angle);
                        ctx.fillStyle = color;
                        ctx.textBaseline = 'middle';
                        ctx.textAlign = 'center';
                        ctx.fillText(item.text, 0, 0);
                        ctx.restore();
                        placed = true;
                        placedCount++;
                    }
                }

                spiralAngle += stepAng;
                radius += (1.0 + step * 0.0019) * scale;
                step++;
            }
        }
    });

    return { placedCount, hitboxes, topWord, placedSet };
}

function openWordCloudStudio() {
    if (!wordCloudStudioState.words || wordCloudStudioState.words.length === 0) {
        if (currentWordCloudData && currentWordCloudData.length > 0) {
            wordCloudStudioState.words = currentWordCloudData.map(w => ({
                text: w.text || w.name,
                weight: w.weight || w.value || 1,
                enabled: true
            }));
        } else {
            wordCloudStudioState.words = JSON.parse(JSON.stringify(DEFAULT_STUDIO_WORDS));
        }
    }

    clearStudioWordSearch();
    resetStudioCanvasPanAndZoom();
    syncStudioControlsFromState();

    const modal = document.getElementById('wordCloudStudioModal');
    if (modal) modal.classList.remove('hidden');

    setupStudioInteractivity();
    renderStudioPreview();
    renderStudioWordsTable();

    setTimeout(() => {
        renderStudioPreview();
    }, 60);
}
window.openWordCloudStudio = openWordCloudStudio;

function closeWordCloudStudio() {
    const modal = document.getElementById('wordCloudStudioModal');
    if (modal) modal.classList.add('hidden');
    const tooltip = document.getElementById('studioWordTooltip');
    if (tooltip) tooltip.classList.add('hidden');
}
window.closeWordCloudStudio = closeWordCloudStudio;

function applyStudioCanvasTransform() {
    const canvas = document.getElementById('studioPreviewCanvas');
    const zoomVal = document.getElementById('studioZoomVal');
    const panHint = document.getElementById('studioPanHint');
    if (!canvas) return;

    canvas.style.transform = `translate(${studioPanX}px, ${studioPanY}px) scale(${studioCanvasZoom})`;
    canvas.style.transformOrigin = 'center center';

    if (zoomVal) {
        zoomVal.textContent = `${Math.round(studioCanvasZoom * 100)}%`;
    }
    if (panHint) {
        if (studioPanX !== 0 || studioPanY !== 0 || studioCanvasZoom !== 1) {
            panHint.classList.remove('hidden');
        } else {
            panHint.classList.add('hidden');
        }
    }
}

function zoomStudioCanvas(factor) {
    if (factor > 1) {
        studioCanvasZoom = Math.min(3.0, +(studioCanvasZoom * factor).toFixed(2));
    } else {
        studioCanvasZoom = Math.max(0.4, +(studioCanvasZoom * factor).toFixed(2));
    }
    applyStudioCanvasTransform();
}
window.zoomStudioCanvas = zoomStudioCanvas;

function resetStudioCanvasPanAndZoom() {
    studioCanvasZoom = 1;
    studioPanX = 0;
    studioPanY = 0;
    applyStudioCanvasTransform();
}
window.resetStudioCanvasPanAndZoom = resetStudioCanvasPanAndZoom;
window.resetStudioCanvasZoom = resetStudioCanvasPanAndZoom;

function setupStudioInteractivity() {
    if (!studioKeyboardListenerSetup) {
        document.addEventListener('keydown', (e) => {
            const modal = document.getElementById('wordCloudStudioModal');
            if (!modal || modal.classList.contains('hidden')) return;

            const activeEl = document.activeElement;
            const isTyping = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');

            if (e.key === 'Escape') {
                closeWordCloudStudio();
            } else if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                applyStudioToDashboard();
            } else if (!isTyping) {
                if (e.key === 'r' || e.key === 'R') {
                    recalculateStudioPreview();
                } else if (e.key === '+' || e.key === '=') {
                    zoomStudioCanvas(1.15);
                } else if (e.key === '-' || e.key === '_') {
                    zoomStudioCanvas(0.85);
                } else if (e.key === '0') {
                    resetStudioCanvasPanAndZoom();
                }
            }
        });
        studioKeyboardListenerSetup = true;
    }

    const canvas = document.getElementById('studioPreviewCanvas');
    const wrapper = document.getElementById('studioCanvasWrapper');
    const tooltip = document.getElementById('studioWordTooltip');

    if (canvas && wrapper && tooltip && !studioInteractivitySetup) {
        wrapper.addEventListener('mousedown', (e) => {
            if (e.target.closest('button') || e.target.closest('input')) return;
            studioIsDragging = true;
            studioDragStartX = e.clientX - studioPanX;
            studioDragStartY = e.clientY - studioPanY;
            studioDragDistance = 0;
            wrapper.style.cursor = 'grabbing';
            canvas.style.cursor = 'grabbing';
            tooltip.classList.add('hidden');
        });

        window.addEventListener('mousemove', (e) => {
            if (!studioIsDragging) return;
            const newX = Math.round(e.clientX - studioDragStartX);
            const newY = Math.round(e.clientY - studioDragStartY);
            const dx = newX - studioPanX;
            const dy = newY - studioPanY;
            studioDragDistance += Math.abs(dx) + Math.abs(dy);
            studioPanX = newX;
            studioPanY = newY;
            applyStudioCanvasTransform();
        });

        window.addEventListener('mouseup', () => {
            if (studioIsDragging) {
                studioIsDragging = false;
                if (wrapper) wrapper.style.cursor = 'default';
                if (canvas) canvas.style.cursor = 'default';
            }
        });

        wrapper.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY < 0 ? 1.15 : 0.85;
            zoomStudioCanvas(factor);
        }, { passive: false });

        canvas.addEventListener('mousemove', (e) => {
            if (studioIsDragging) return;

            const rect = canvas.getBoundingClientRect();
            const clientX = e.clientX - rect.left;
            const clientY = e.clientY - rect.top;

            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const canvasX = clientX * scaleX;
            const canvasY = clientY * scaleY;

            let hovered = null;
            for (let item of studioLastRenderedBoxes) {
                if (canvasX >= item.box.left && canvasX <= item.box.right &&
                    canvasY >= item.box.top && canvasY <= item.box.bottom) {
                    hovered = item;
                    break;
                }
            }

            if (hovered) {
                canvas.style.cursor = 'pointer';
                const wrapRect = wrapper.getBoundingClientRect();
                const tipX = e.clientX - wrapRect.left + 14;
                const tipY = e.clientY - wrapRect.top - 20;

                tooltip.style.left = `${Math.min(tipX, wrapRect.width - 170)}px`;
                tooltip.style.top = `${Math.max(10, tipY)}px`;

                const wordEl = document.getElementById('studioTooltipWord');
                const rankEl = document.getElementById('studioTooltipRank');
                const weightEl = document.getElementById('studioTooltipWeight');

                if (wordEl) wordEl.textContent = hovered.text;
                if (rankEl) rankEl.textContent = `#${hovered.rank}`;
                if (weightEl) weightEl.textContent = hovered.weight;

                tooltip.classList.remove('hidden');
            } else {
                canvas.style.cursor = 'default';
                tooltip.classList.add('hidden');
            }
        });

        canvas.addEventListener('mouseleave', () => {
            canvas.style.cursor = 'default';
            tooltip.classList.add('hidden');
        });

        canvas.addEventListener('click', (e) => {
            if (studioDragDistance > 6) return;

            const rect = canvas.getBoundingClientRect();
            const clientX = e.clientX - rect.left;
            const clientY = e.clientY - rect.top;

            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const canvasX = clientX * scaleX;
            const canvasY = clientY * scaleY;

            for (let item of studioLastRenderedBoxes) {
                if (canvasX >= item.box.left && canvasX <= item.box.right &&
                    canvasY >= item.box.top && canvasY <= item.box.bottom) {
                    switchStudioTab('words');
                    const searchInput = document.getElementById('studioWordSearchInput');
                    if (searchInput) {
                        searchInput.value = item.text;
                        filterStudioWordsTable(item.text);
                    }
                    showToast(`Editando termo "${item.text}" (#${item.rank})`, 'info');
                    break;
                }
            }
        });

        studioInteractivitySetup = true;
    }
}

function switchStudioTab(tabId) {
    const tabs = ['presets', 'words', 'shape', 'type', 'colors'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tabStudio${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
        const panel = document.getElementById(`tabStudio${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (t === tabId) {
            btn?.classList.add('active', 'border-[#1D4ED8]', 'text-[#1D4ED8]', 'dark:text-[#60A5FA]', 'font-semibold');
            btn?.classList.remove('border-transparent', 'text-slate-500', 'dark:text-[#A1A1AA]');
            panel?.classList.remove('hidden');
        } else {
            btn?.classList.remove('active', 'border-[#1D4ED8]', 'text-[#1D4ED8]', 'dark:text-[#60A5FA]', 'font-semibold');
            btn?.classList.add('border-transparent', 'text-slate-500', 'dark:text-[#A1A1AA]');
            panel?.classList.add('hidden');
        }
    });
}
window.switchStudioTab = switchStudioTab;

function syncStudioControlsFromState() {
    const padRange = document.getElementById('studioPaddingRange');
    const padVal = document.getElementById('studioPaddingVal');
    if (padRange) {
        padRange.value = wordCloudStudioState.padding !== undefined ? wordCloudStudioState.padding : 4;
        if (padVal) padVal.textContent = `${padRange.value}px`;
    }

    const maxWordsRange = document.getElementById('studioMaxWordsRange');
    const maxWordsVal = document.getElementById('studioMaxWordsVal');
    if (maxWordsRange) {
        maxWordsRange.value = wordCloudStudioState.maxWords !== undefined ? wordCloudStudioState.maxWords : 50;
        if (maxWordsVal) maxWordsVal.textContent = maxWordsRange.value;
    }

    const invertCheck = document.getElementById('studioInvertShape');
    if (invertCheck) invertCheck.checked = !!wordCloudStudioState.invertShape;

    const outlineCheck = document.getElementById('studioDrawShapeOutline');
    if (outlineCheck) outlineCheck.checked = !!wordCloudStudioState.drawShapeOutline;

    updateStudioShapeUI();
    updateStudioAngleUI();
    updateStudioPaletteUI();
    updateStudioBgUI();
    updateStudioColorModeUI();
    updateStudioTypographyUI();
}
window.syncStudioControlsFromState = syncStudioControlsFromState;

function applyStudioPreset(presetKey) {
    const preset = STUDIO_PRESETS[presetKey];
    if (!preset) return;

    wordCloudStudioState = {
        ...wordCloudStudioState,
        shape: preset.shape,
        invertShape: preset.invertShape || false,
        drawShapeOutline: preset.drawShapeOutline || false,
        fontFamily: preset.fontFamily,
        fontWeight: preset.fontWeight,
        minFontSize: preset.minFontSize || 14,
        maxFontSize: preset.maxFontSize || 46,
        scaleCurve: preset.scaleCurve || 'linear',
        angleMode: preset.angleMode,
        paletteName: preset.paletteName,
        colorMode: preset.colorMode || 'frequency',
        bgMode: preset.bgMode || 'transparent',
        padding: preset.padding !== undefined ? preset.padding : 4,
        maxWords: preset.maxWords !== undefined ? preset.maxWords : 50
    };

    syncStudioControlsFromState();
    renderStudioPreview();
    showToast(`Preset "${preset.name}" aplicado!`, 'success');
}
window.applyStudioPreset = applyStudioPreset;

let studioInputDebounceTimer = null;
function onStudioWordTextInput(index, val) {
    clearTimeout(studioInputDebounceTimer);
    studioInputDebounceTimer = setTimeout(() => {
        if (wordCloudStudioState.words && wordCloudStudioState.words[index]) {
            wordCloudStudioState.words[index].text = val.trim();
            renderStudioPreview();
        }
    }, 250);
}
window.onStudioWordTextInput = onStudioWordTextInput;

function onStudioWordWeightInput(index, val) {
    clearTimeout(studioInputDebounceTimer);
    studioInputDebounceTimer = setTimeout(() => {
        if (wordCloudStudioState.words && wordCloudStudioState.words[index]) {
            wordCloudStudioState.words[index].weight = Math.max(1, parseInt(val, 10) || 1);
            renderStudioPreview();
        }
    }, 250);
}
window.onStudioWordWeightInput = onStudioWordWeightInput;

function adjustStudioWordWeight(index, delta) {
    const word = wordCloudStudioState.words && wordCloudStudioState.words[index];
    if (!word) return;
    const current = parseInt(word.weight, 10) || 1;
    word.weight = Math.max(1, current + delta);
    renderStudioWordsTable();
    renderStudioPreview();
}
window.adjustStudioWordWeight = adjustStudioWordWeight;

function renderStudioWordsTable() {
    const tbody = document.getElementById('studioWordsTableBody');
    const countLabel = document.getElementById('studioWordsCountLabel');
    if (!tbody) return;

    tbody.innerHTML = '';
    const allWords = wordCloudStudioState.words || [];
    const activeCount = allWords.filter(w => w.enabled).length;

    if (countLabel) {
        const pct = allWords.length ? Math.round((activeCount / allWords.length) * 100) : 0;
        countLabel.textContent = `${activeCount} ativas de ${allWords.length} palavras (${pct}%)`;
    }

    const selectAllCheckbox = document.getElementById('studioSelectAllWords');
    if (selectAllCheckbox) {
        if (allWords.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (activeCount === allWords.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (activeCount === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    const query = (wordCloudStudioState.filterQuery || '').toLowerCase().trim();
    let displayWords = allWords.map((item, originalIndex) => ({ ...item, originalIndex }));

    if (query) {
        displayWords = displayWords.filter(w => (w.text || '').toLowerCase().includes(query));
    }

    if (wordCloudStudioState.sortKey === 'text') {
        displayWords.sort((a, b) => {
            const cmp = (a.text || '').localeCompare(b.text || '');
            return wordCloudStudioState.sortAsc ? cmp : -cmp;
        });
    } else {
        displayWords.sort((a, b) => {
            const cmp = (a.weight || 0) - (b.weight || 0);
            return wordCloudStudioState.sortAsc ? cmp : -cmp;
        });
    }

    if (displayWords.length === 0) {
        const msg = query ? `Nenhum termo encontrado para "${escapeHtml(query)}"` : 'Nenhum termo na lista. Adicione acima.';
        tbody.innerHTML = `<tr><td colspan="6" class="px-3 py-6 text-center text-xs font-mono text-slate-400 dark:text-slate-500">${msg}</td></tr>`;
        return;
    }

    const maxWeight = Math.max(...allWords.map(w => w.weight || 1), 1);

    displayWords.forEach((item, displayIdx) => {
        const realIdx = item.originalIndex;
        const tr = document.createElement('tr');
        tr.setAttribute('data-word-text', item.text);
        tr.setAttribute('data-word-enabled', item.enabled ? 'true' : 'false');
        tr.className = item.enabled ? 'hover:bg-slate-50/80 dark:hover:bg-[#26262B]' : 'opacity-40 hover:bg-slate-50/80 dark:hover:bg-[#26262B]';

        let rankBadge = `<span class="font-mono text-[10px] text-slate-400">#${displayIdx + 1}</span>`;
        if (displayIdx === 0 && !query && wordCloudStudioState.sortKey === 'weight' && !wordCloudStudioState.sortAsc) {
            rankBadge = `<span class="inline-flex items-center justify-center w-4 h-4 rounded text-[9px] font-bold bg-amber-500 text-white font-mono shadow-xs" title="Termo Líder">1</span>`;
        } else if (displayIdx === 1 && !query && wordCloudStudioState.sortKey === 'weight' && !wordCloudStudioState.sortAsc) {
            rankBadge = `<span class="inline-flex items-center justify-center w-4 h-4 rounded text-[9px] font-bold bg-slate-400 text-white font-mono" title="2º Lugar">2</span>`;
        } else if (displayIdx === 2 && !query && wordCloudStudioState.sortKey === 'weight' && !wordCloudStudioState.sortAsc) {
            rankBadge = `<span class="inline-flex items-center justify-center w-4 h-4 rounded text-[9px] font-bold bg-amber-700 text-white font-mono" title="3º Lugar">3</span>`;
        }

        const barPct = Math.min(100, Math.round((item.weight / maxWeight) * 100));

        let statusHtml = '';
        if (!item.enabled) {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-100 text-slate-500 dark:bg-[#323238] dark:text-[#A1A1AA]">Inativo</span>`;
        } else if (studioLastPlacedWordTexts.has(item.text)) {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 font-semibold">Visível</span>`;
        } else {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 font-medium" title="Não coube no canvas com a forma/fonte atual">Omitido</span>`;
        }

        tr.innerHTML = `
            <td class="py-1 px-2.5 text-center align-middle">
                <input type="checkbox" ${item.enabled ? 'checked' : ''} onchange="toggleStudioWord(${realIdx}, this.checked)" class="text-[#1D4ED8] rounded-sm border-[#E4DFD6] dark:border-[#323238] cursor-pointer align-middle">
            </td>
            <td class="py-1 px-1.5 text-center align-middle">
                ${rankBadge}
            </td>
            <td class="py-1 px-2">
                <input type="text" value="${escapeHtml(item.text)}" onchange="updateStudioWordText(${realIdx}, this.value)" oninput="onStudioWordTextInput(${realIdx}, this.value)" class="studio-inline-input w-full px-1.5 py-0.5 text-xs bg-transparent rounded text-slate-800 dark:text-[#F4F4F6]">
            </td>
            <td class="py-1 px-2 text-right">
                <div class="flex items-center justify-end gap-1.5">
                    <div class="hidden sm:block w-8 h-1.5 bg-slate-100 dark:bg-[#323238] rounded-full overflow-hidden">
                        <div class="h-full bg-[#1D4ED8] dark:bg-[#60A5FA]" style="width: ${barPct}%"></div>
                    </div>
                    <button type="button" onclick="adjustStudioWordWeight(${realIdx}, -5)" class="w-4 h-4 flex items-center justify-center text-[10px] text-slate-400 hover:text-slate-700 dark:hover:text-[#F4F4F6] rounded hover:bg-slate-100 dark:hover:bg-[#323238]" title="Diminuir peso (-5)">-</button>
                    <input type="number" min="1" max="10000" value="${item.weight || 1}" onchange="updateStudioWordWeight(${realIdx}, this.value)" oninput="onStudioWordWeightInput(${realIdx}, this.value)" class="studio-inline-input w-11 px-1 py-0.5 text-xs font-mono text-right bg-transparent rounded text-slate-800 dark:text-[#F4F4F6]">
                    <button type="button" onclick="adjustStudioWordWeight(${realIdx}, 5)" class="w-4 h-4 flex items-center justify-center text-[10px] text-slate-400 hover:text-slate-700 dark:hover:text-[#F4F4F6] rounded hover:bg-slate-100 dark:hover:bg-[#323238]" title="Aumentar peso (+5)">+</button>
                </div>
            </td>
            <td class="studio-word-status-cell py-1 px-2 text-center align-middle">
                ${statusHtml}
            </td>
            <td class="py-1 px-1.5 text-center align-middle">
                <button type="button" onclick="deleteStudioWord(${realIdx})" class="text-slate-400 hover:text-rose-500 p-1 transition-colors" title="Excluir termo">
                    <i class="fa-solid fa-trash-can text-[11px]"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterStudioWordsTable(query) {
    wordCloudStudioState.filterQuery = query || '';
    const btnClear = document.getElementById('btnClearStudioWordSearch');
    if (btnClear) {
        if (query) btnClear.classList.remove('hidden');
        else btnClear.classList.add('hidden');
    }
    renderStudioWordsTable();
}
window.filterStudioWordsTable = filterStudioWordsTable;

function clearStudioWordSearch() {
    const input = document.getElementById('studioWordSearchInput');
    if (input) input.value = '';
    filterStudioWordsTable('');
}
window.clearStudioWordSearch = clearStudioWordSearch;

function toggleSortStudioWords(key) {
    if (wordCloudStudioState.sortKey === key) {
        wordCloudStudioState.sortAsc = !wordCloudStudioState.sortAsc;
    } else {
        wordCloudStudioState.sortKey = key;
        wordCloudStudioState.sortAsc = false;
    }
    renderStudioWordsTable();
}
window.toggleSortStudioWords = toggleSortStudioWords;

function toggleStudioWord(index, checked) {
    if (wordCloudStudioState.words && wordCloudStudioState.words[index]) {
        wordCloudStudioState.words[index].enabled = checked;
        renderStudioWordsTable();
        renderStudioPreview();
    }
}
window.toggleStudioWord = toggleStudioWord;

function toggleAllStudioWords(checked) {
    if (!wordCloudStudioState.words) return;
    wordCloudStudioState.words.forEach(w => {
        w.enabled = checked;
    });
    renderStudioWordsTable();
    renderStudioPreview();
}
window.toggleAllStudioWords = toggleAllStudioWords;

function selectTopWords(count) {
    if (!wordCloudStudioState.words) return;
    const sorted = [...wordCloudStudioState.words].sort((a, b) => (b.weight || 1) - (a.weight || 1));
    const topTexts = new Set(sorted.slice(0, count).map(w => w.text));

    wordCloudStudioState.words.forEach(w => {
        w.enabled = topTexts.has(w.text);
    });
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`Top ${count} termos ativados`, 'info');
}
window.selectTopWords = selectTopWords;

function invertStudioWordsSelection() {
    if (!wordCloudStudioState.words) return;
    wordCloudStudioState.words.forEach(w => {
        w.enabled = !w.enabled;
    });
    renderStudioWordsTable();
    renderStudioPreview();
    showToast('Seleção de termos invertida', 'info');
}
window.invertStudioWordsSelection = invertStudioWordsSelection;

function deleteDisabledStudioWords() {
    if (!wordCloudStudioState.words) return;
    const before = wordCloudStudioState.words.length;
    wordCloudStudioState.words = wordCloudStudioState.words.filter(w => w.enabled);
    const removed = before - wordCloudStudioState.words.length;
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`${removed} termos inativos removidos`, 'info');
}
window.deleteDisabledStudioWords = deleteDisabledStudioWords;

function transformStudioWordsCase(mode) {
    if (!wordCloudStudioState.words || wordCloudStudioState.words.length === 0) return;
    wordCloudStudioState.words.forEach(w => {
        if (!w.text) return;
        if (mode === 'upper') {
            w.text = w.text.toUpperCase();
        } else if (mode === 'lower') {
            w.text = w.text.toLowerCase();
        } else if (mode === 'capitalize') {
            w.text = w.text.charAt(0).toUpperCase() + w.text.slice(1).toLowerCase();
        }
    });
    renderStudioWordsTable();
    renderStudioPreview();
    const modeLabel = mode === 'upper' ? 'MAIÚSCULAS' : (mode === 'lower' ? 'minúsculas' : 'Capitalizadas');
    showToast(`Termos convertidos para ${modeLabel}`, 'info');
}
window.transformStudioWordsCase = transformStudioWordsCase;

function updateStudioWordText(index, val) {
    if (wordCloudStudioState.words && wordCloudStudioState.words[index]) {
        wordCloudStudioState.words[index].text = val.trim();
        renderStudioPreview();
    }
}
window.updateStudioWordText = updateStudioWordText;

function updateStudioWordWeight(index, val) {
    if (wordCloudStudioState.words && wordCloudStudioState.words[index]) {
        wordCloudStudioState.words[index].weight = Math.max(1, parseInt(val, 10) || 1);
        renderStudioPreview();
    }
}
window.updateStudioWordWeight = updateStudioWordWeight;

function deleteStudioWord(index) {
    if (wordCloudStudioState.words) {
        wordCloudStudioState.words.splice(index, 1);
        renderStudioWordsTable();
        renderStudioPreview();
    }
}
window.deleteStudioWord = deleteStudioWord;

function addStudioWord() {
    const input = document.getElementById('newStudioWordInput');
    const weightInput = document.getElementById('newStudioWordWeight');
    const text = input?.value?.trim();
    const weight = Math.max(1, parseInt(weightInput?.value, 10) || 25);

    if (!text) {
        showToast('Digite a palavra para adicionar', 'error');
        return;
    }

    if (!wordCloudStudioState.words) wordCloudStudioState.words = [];
    wordCloudStudioState.words.unshift({
        text: text,
        weight: weight,
        enabled: true
    });

    if (input) input.value = '';
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`Termo "${text}" adicionado com peso ${weight}`, 'info');
}
window.addStudioWord = addStudioWord;

function toggleStudioBulkImport() {
    const drawer = document.getElementById('studioBulkImportDrawer');
    if (drawer) {
        drawer.classList.toggle('hidden');
    }
}
window.toggleStudioBulkImport = toggleStudioBulkImport;

function processStudioBulkImport(replace = false) {
    const textarea = document.getElementById('studioBulkImportTextarea');
    const raw = (textarea?.value || '').trim();
    if (!raw) {
        showToast('Cole o texto ou lista de termos para importar', 'error');
        return;
    }

    const parsed = [];
    const rawLines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

    if (rawLines.length === 1 && rawLines[0].includes(',') && !rawLines[0].match(/,\s*\d+/)) {
        const words = rawLines[0].split(',').map(w => w.trim()).filter(Boolean);
        words.forEach(w => parsed.push({ text: w, weight: 20, enabled: true }));
    } else {
        rawLines.forEach(rawLine => {
            let line = rawLine.replace(/^[•\-\s*]+/, '').trim();
            if (!line) return;
            if (/^(posi[cç][aã]o|rank|#|termo|palavra|word|termo\t|palavra\t)/i.test(line)) return;

            // TSV
            if (line.includes('\t')) {
                const parts = line.split('\t').map(p => p.trim()).filter(Boolean);
                if (parts.length >= 2) {
                    if (/^\d+$/.test(parts[0]) && parts.length >= 3 && !/^\d+$/.test(parts[1])) {
                        const word = parts[1].replace(/^[•\-\s*]+/, '');
                        const weight = parseInt(parts[2].replace(/[^\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight), enabled: true });
                        return;
                    }
                    if (!/^\d+$/.test(parts[0])) {
                        const word = parts[0].replace(/^[•\-\s*]+/, '');
                        const weight = parseInt(parts[1].replace(/[^\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight), enabled: true });
                        return;
                    }
                }
            }

            // CSV
            if (line.includes(',')) {
                const csvParts = line.split(',').map(p => p.trim()).filter(Boolean);
                if (csvParts.length === 2 && /^\d+$/.test(csvParts[1])) {
                    parsed.push({ text: csvParts[0], weight: Math.max(1, parseInt(csvParts[1], 10)), enabled: true });
                    return;
                }
                if (csvParts.length >= 3 && /^\d+$/.test(csvParts[0]) && /^\d+$/.test(csvParts[2])) {
                    parsed.push({ text: csvParts[1], weight: Math.max(1, parseInt(csvParts[2], 10)), enabled: true });
                    return;
                }
            }

            // Ponto-e-vírgula
            if (line.includes(';')) {
                const scParts = line.split(';').map(p => p.trim()).filter(Boolean);
                if (scParts.length >= 2 && /^\d+$/.test(scParts[1])) {
                    parsed.push({ text: scParts[0], weight: Math.max(1, parseInt(scParts[1], 10)), enabled: true });
                    return;
                }
            }

            // Termo com peso (dois-pontos, igual ou espaço)
            const match = line.match(/^(.+?)(?:\s*[:=]\s*|\s+)(\d+)(?:\s*%)?$/);
            if (match) {
                const text = match[1].replace(/^["']|["']$/g, '').trim();
                const weight = Math.max(1, parseInt(match[2], 10));
                parsed.push({ text, weight, enabled: true });
                return;
            }

            // Parênteses
            const parenMatch = line.match(/^(.+?)\s*\(\s*(\d+)\s*\)$/);
            if (parenMatch) {
                parsed.push({ text: parenMatch[1].trim(), weight: Math.max(1, parseInt(parenMatch[2], 10)), enabled: true });
                return;
            }

            // Termo isolado
            const cleaned = line.replace(/^[•\-\s*\d+\.]+/, '').trim();
            if (cleaned) {
                parsed.push({ text: cleaned, weight: 15, enabled: true });
            }
        });
    }

    if (parsed.length === 0) {
        showToast('Nenhum termo válido identificado', 'error');
        return;
    }

    if (replace) {
        wordCloudStudioState.words = parsed;
    } else {
        wordCloudStudioState.words = [...parsed, ...(wordCloudStudioState.words || [])];
    }

    if (textarea) textarea.value = '';
    toggleStudioBulkImport();
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`${parsed.length} termos importados com sucesso!`, 'success');
}
window.processStudioBulkImport = processStudioBulkImport;

function toggleStudioStopwordsSoft() {
    let disabledCount = 0;
    (wordCloudStudioState.words || []).forEach(w => {
        const clean = (w.text || '').toLowerCase().trim();
        if (clean.length <= 2 || COMMON_PORTUGUESE_STOPWORDS.has(clean)) {
            if (w.enabled) {
                w.enabled = false;
                disabledCount++;
            }
        }
    });
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`${disabledCount} stopwords desmarcadas (reversível)`, 'info');
}
window.toggleStudioStopwordsSoft = toggleStudioStopwordsSoft;

function cleanStudioStopwords() {
    const beforeCount = (wordCloudStudioState.words || []).length;
    wordCloudStudioState.words = (wordCloudStudioState.words || []).filter(w => {
        const clean = (w.text || '').toLowerCase().trim();
        return clean.length > 2 && !COMMON_PORTUGUESE_STOPWORDS.has(clean);
    });
    const removed = beforeCount - wordCloudStudioState.words.length;
    renderStudioWordsTable();
    renderStudioPreview();
    showToast(`${removed} stopwords removidas definitivamente`, 'success');
}
window.cleanStudioStopwords = cleanStudioStopwords;

function resetStudioWords() {
    if (currentWordCloudData && currentWordCloudData.length > 0) {
        wordCloudStudioState.words = currentWordCloudData.map(w => ({
            text: w.text || w.name,
            weight: w.weight || w.value || 1,
            enabled: true
        }));
    } else {
        wordCloudStudioState.words = JSON.parse(JSON.stringify(DEFAULT_STUDIO_WORDS));
    }
    renderStudioWordsTable();
    renderStudioPreview();
    showToast('Lista de termos restaurada para os dados originais', 'info');
}
window.resetStudioWords = resetStudioWords;

function setStudioShape(shape) {
    wordCloudStudioState.shape = shape;
    updateStudioShapeUI();
    renderStudioPreview();
}
window.setStudioShape = setStudioShape;

function updateStudioShapeUI() {
    document.querySelectorAll('.studio-shape-card').forEach(card => {
        const shape = card.getAttribute('data-shape');
        if (shape === wordCloudStudioState.shape) {
            card.className = 'studio-shape-card p-2.5 rounded-md border text-left transition-all border-[#1D4ED8] bg-[#1D4ED8]/5 dark:bg-[#60A5FA]/10';
        } else {
            card.className = 'studio-shape-card p-2.5 rounded-md border text-left transition-all border-[#E4DFD6] dark:border-[#323238] hover:border-slate-400';
        }
    });
    const badge = document.getElementById('studioPreviewShapeBadge');
    if (badge) {
        const labels = {
            '16x9': '16:9 Slide Deck',
            '1x1': '1:1 Card Quadrado',
            '9x16': '9:16 Story / Mobile',
            'circle': 'Círculo / Esfera',
            'speech': 'Balão de Diálogo',
            'heart': 'Coração',
            'cloud': 'Nuvem Clássica',
            'star': 'Estrela / Destaque',
            'trophy': 'Troféu de Sucesso',
            'shield': 'Escudo Governança',
            'hexagon': 'Hexágono Modular'
        };
        const shapeIcons = {
            '16x9': 'fa-display',
            '1x1': 'fa-square',
            '9x16': 'fa-mobile-screen',
            'circle': 'fa-circle',
            'speech': 'fa-comment-dots',
            'heart': 'fa-heart',
            'cloud': 'fa-cloud',
            'star': 'fa-star',
            'trophy': 'fa-trophy',
            'shield': 'fa-shield-halved',
            'hexagon': 'fa-cube'
        };
        const icon = shapeIcons[wordCloudStudioState.shape] || 'fa-shapes';
        badge.innerHTML = `<i class="fa-solid ${icon} mr-1 text-[#1D4ED8] dark:text-[#60A5FA]"></i> Formato: ${labels[wordCloudStudioState.shape] || wordCloudStudioState.shape}`;
    }
}

function toggleStudioInvertShape(checked) {
    wordCloudStudioState.invertShape = checked;
    renderStudioPreview();
}
window.toggleStudioInvertShape = toggleStudioInvertShape;

function toggleStudioShapeOutline(checked) {
    wordCloudStudioState.drawShapeOutline = checked;
    renderStudioPreview();
}
window.toggleStudioShapeOutline = toggleStudioShapeOutline;

function updateStudioTypography() {
    const sel = document.getElementById('studioFontFamily');
    if (sel) wordCloudStudioState.fontFamily = sel.value;
    renderStudioPreview();
}
window.updateStudioTypography = updateStudioTypography;

function updateStudioTypographyUI() {
    const sel = document.getElementById('studioFontFamily');
    if (sel && wordCloudStudioState.fontFamily) {
        sel.value = wordCloudStudioState.fontFamily;
    }
    setStudioFontWeight(wordCloudStudioState.fontWeight || '800');

    const minRange = document.getElementById('studioMinFontRange');
    const maxRange = document.getElementById('studioMaxFontRange');
    if (minRange) minRange.value = wordCloudStudioState.minFontSize || 14;
    if (maxRange) maxRange.value = wordCloudStudioState.maxFontSize || 46;

    const minVal = document.getElementById('studioMinFontVal');
    const maxVal = document.getElementById('studioMaxFontVal');
    const scaleLabel = document.getElementById('studioFontScaleLabel');
    if (minVal) minVal.textContent = `${wordCloudStudioState.minFontSize || 14}px`;
    if (maxVal) maxVal.textContent = `${wordCloudStudioState.maxFontSize || 46}px`;
    if (scaleLabel) scaleLabel.textContent = `${wordCloudStudioState.minFontSize || 14}px - ${wordCloudStudioState.maxFontSize || 46}px`;

    setStudioScaleCurve(wordCloudStudioState.scaleCurve || 'linear');
}

function setStudioFontWeight(weight) {
    wordCloudStudioState.fontWeight = weight;
    document.querySelectorAll('.studio-weight-btn').forEach(btn => {
        if (btn.getAttribute('data-weight') === String(weight)) {
            btn.className = 'studio-weight-btn py-1 px-1.5 rounded border text-xs font-bold text-[#1D4ED8] dark:text-[#60A5FA] border-[#1D4ED8] bg-[#1D4ED8]/10';
        } else {
            btn.className = 'studio-weight-btn py-1 px-1.5 rounded border text-xs font-semibold text-slate-700 dark:text-[#F4F4F6] border-[#E4DFD6] dark:border-[#323238]';
        }
    });
    renderStudioPreview();
}
window.setStudioFontWeight = setStudioFontWeight;

function updateStudioFontScale() {
    const minRange = document.getElementById('studioMinFontRange');
    const maxRange = document.getElementById('studioMaxFontRange');
    if (minRange) wordCloudStudioState.minFontSize = parseInt(minRange.value, 10);
    if (maxRange) wordCloudStudioState.maxFontSize = parseInt(maxRange.value, 10);

    const minVal = document.getElementById('studioMinFontVal');
    const maxVal = document.getElementById('studioMaxFontVal');
    const scaleLabel = document.getElementById('studioFontScaleLabel');
    if (minVal) minVal.textContent = `${wordCloudStudioState.minFontSize}px`;
    if (maxVal) maxVal.textContent = `${wordCloudStudioState.maxFontSize}px`;
    if (scaleLabel) scaleLabel.textContent = `${wordCloudStudioState.minFontSize}px - ${wordCloudStudioState.maxFontSize}px`;

    renderStudioPreview();
}
window.updateStudioFontScale = updateStudioFontScale;

function setStudioScaleCurve(curve) {
    wordCloudStudioState.scaleCurve = curve;
    const btnLin = document.getElementById('btnScaleCurveLinear');
    const btnLog = document.getElementById('btnScaleCurveLog');
    if (btnLin && btnLog) {
        if (curve === 'log') {
            btnLog.className = 'px-2 py-0.5 bg-[#1D4ED8] text-white font-medium';
            btnLin.className = 'px-2 py-0.5 bg-[#F1EDE6] dark:bg-[#26262B] text-slate-700 dark:text-[#F4F4F6] hover:bg-slate-200';
        } else {
            btnLin.className = 'px-2 py-0.5 bg-[#1D4ED8] text-white font-medium';
            btnLog.className = 'px-2 py-0.5 bg-[#F1EDE6] dark:bg-[#26262B] text-slate-700 dark:text-[#F4F4F6] hover:bg-slate-200';
        }
    }
    renderStudioPreview();
}
window.setStudioScaleCurve = setStudioScaleCurve;

function setStudioAngle(angle) {
    wordCloudStudioState.angleMode = angle;
    updateStudioAngleUI();
    renderStudioPreview();
}
window.setStudioAngle = setStudioAngle;

function updateStudioAngleUI() {
    document.querySelectorAll('.studio-angle-btn').forEach(btn => {
        if (btn.getAttribute('data-angle') === wordCloudStudioState.angleMode) {
            btn.className = 'studio-angle-btn px-2.5 py-1.5 rounded border text-left border-[#1D4ED8] bg-[#1D4ED8]/10 text-[#1D4ED8] dark:text-[#60A5FA]';
        } else {
            btn.className = 'studio-angle-btn px-2.5 py-1.5 rounded border text-left border-[#E4DFD6] dark:border-[#323238] text-slate-700 dark:text-[#F4F4F6]';
        }
    });
}

function onCustomColorPickerChange(index, hexValue) {
    if (!Array.isArray(wordCloudStudioState.customColors) || wordCloudStudioState.customColors.length < 5) {
        wordCloudStudioState.customColors = ['#1D4ED8', '#2563EB', '#3B82F6', '#60A5FA', '#93C5FD'];
    }
    wordCloudStudioState.customColors[index] = hexValue;
    const hexInput = document.getElementById('studioCustomHexInput');
    if (hexInput) {
        hexInput.value = wordCloudStudioState.customColors.join(', ');
    }
    wordCloudStudioState.paletteName = 'custom';
    updateStudioPaletteUI();
    renderStudioPreview();
}
window.onCustomColorPickerChange = onCustomColorPickerChange;

function parseHexColors(str) {
    if (!str) return [];
    const matches = str.match(/#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}/g);
    if (!matches) return [];
    return matches.map(hex => {
        if (hex.length === 4) {
            return ('#' + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3]).toUpperCase();
        }
        return hex.toUpperCase();
    });
}

function onCustomHexInputChange(val) {
    const colors = parseHexColors(val);
    if (colors.length > 0) {
        while (colors.length < 5) {
            colors.push(colors[colors.length - 1]);
        }
        const finalColors = colors.slice(0, 5);
        wordCloudStudioState.customColors = finalColors;
        finalColors.forEach((c, idx) => {
            const picker = document.getElementById(`studioCustomColor${idx + 1}`);
            if (picker) picker.value = c;
        });
        wordCloudStudioState.paletteName = 'custom';
        updateStudioPaletteUI();
        renderStudioPreview();
    }
}
window.onCustomHexInputChange = onCustomHexInputChange;

function applyCustomPalette() {
    const hexInput = document.getElementById('studioCustomHexInput');
    if (hexInput) {
        const colors = parseHexColors(hexInput.value);
        if (colors.length > 0) {
            while (colors.length < 5) {
                colors.push(colors[colors.length - 1]);
            }
            wordCloudStudioState.customColors = colors.slice(0, 5);
        }
    }
    wordCloudStudioState.paletteName = 'custom';
    updateStudioPaletteUI();
    renderStudioPreview();
    showToast('Paleta personalizada ativada!', 'info');
}
window.applyCustomPalette = applyCustomPalette;

function setStudioPalette(paletteName) {
    wordCloudStudioState.paletteName = paletteName;
    updateStudioPaletteUI();
    renderStudioPreview();
}
window.setStudioPalette = setStudioPalette;

function updateStudioPaletteUI() {
    const isCustom = wordCloudStudioState.paletteName === 'custom';
    const customCard = document.getElementById('studioCustomPaletteCard');
    const customBadge = document.getElementById('studioCustomActiveBadge');
    if (customCard) {
        if (isCustom) {
            customCard.className = 'p-3 rounded-md border-2 border-[#1D4ED8] dark:border-[#60A5FA] bg-[#1D4ED8]/5 dark:bg-[#60A5FA]/10 space-y-2.5 transition-all';
            if (customBadge) customBadge.classList.remove('hidden');
        } else {
            customCard.className = 'p-3 rounded-md border border-[#E4DFD6] dark:border-[#323238] bg-[#F1EDE6]/30 dark:bg-[#26262B]/30 space-y-2.5 transition-all';
            if (customBadge) customBadge.classList.add('hidden');
        }
    }

    if (Array.isArray(wordCloudStudioState.customColors)) {
        wordCloudStudioState.customColors.slice(0, 5).forEach((color, idx) => {
            const picker = document.getElementById(`studioCustomColor${idx + 1}`);
            if (picker && picker.value.toLowerCase() !== color.toLowerCase()) {
                picker.value = color;
            }
        });
        const hexInput = document.getElementById('studioCustomHexInput');
        if (hexInput && document.activeElement !== hexInput) {
            hexInput.value = wordCloudStudioState.customColors.join(', ');
        }
    }

    document.querySelectorAll('.studio-palette-card').forEach(card => {
        if (!isCustom && card.getAttribute('data-palette') === wordCloudStudioState.paletteName) {
            card.className = 'studio-palette-card w-full px-3 py-2 rounded-md border text-left transition-all border-[#1D4ED8] bg-[#1D4ED8]/5 flex items-center justify-between';
        } else {
            card.className = 'studio-palette-card w-full px-3 py-2 rounded-md border text-left transition-all border-[#E4DFD6] dark:border-[#323238] flex items-center justify-between';
        }
    });
}
window.updateStudioPaletteUI = updateStudioPaletteUI;

function setStudioColorMode(mode) {
    wordCloudStudioState.colorMode = mode;
    updateStudioColorModeUI();
    renderStudioPreview();
}
window.setStudioColorMode = setStudioColorMode;

function updateStudioColorModeUI() {
    document.querySelectorAll('.studio-colormode-btn').forEach(btn => {
        if (btn.getAttribute('data-colormode') === wordCloudStudioState.colorMode) {
            btn.className = 'studio-colormode-btn py-1.5 px-2 rounded border text-xs font-medium border-[#1D4ED8] bg-[#1D4ED8]/10 text-[#1D4ED8] dark:text-[#60A5FA]';
        } else {
            btn.className = 'studio-colormode-btn py-1.5 px-2 rounded border text-xs font-medium border-[#E4DFD6] dark:border-[#323238] text-slate-700 dark:text-[#F4F4F6]';
        }
    });
}
window.updateStudioColorModeUI = updateStudioColorModeUI;

function setStudioBg(mode) {
    wordCloudStudioState.bgMode = mode;
    updateStudioBgUI();
    renderStudioPreview();
}
window.setStudioBg = setStudioBg;

function updateStudioBgUI() {
    document.querySelectorAll('.studio-bg-btn').forEach(btn => {
        if (btn.getAttribute('data-bg') === wordCloudStudioState.bgMode) {
            btn.className = 'studio-bg-btn py-1.5 px-1.5 rounded border text-xs font-medium border-[#1D4ED8] bg-[#1D4ED8]/10 text-[#1D4ED8] dark:text-[#60A5FA]';
        } else {
            btn.className = 'studio-bg-btn py-1.5 px-1.5 rounded border text-xs font-medium border-[#E4DFD6] dark:border-[#323238] text-slate-700 dark:text-[#F4F4F6]';
        }
    });
}

function cycleStudioPreviewBg() {
    const modes = ['adaptive', 'light', 'dark', 'solid_white', 'solid_dark'];
    const current = wordCloudStudioState.previewBgCycle || 'adaptive';
    const nextIdx = (modes.indexOf(current) + 1) % modes.length;
    wordCloudStudioState.previewBgCycle = modes[nextIdx];

    const wrapper = document.getElementById('studioCanvasWrapper');
    if (wrapper) {
        wrapper.classList.remove('preview-bg-light', 'preview-bg-dark', 'preview-bg-solid-white', 'preview-bg-solid-dark');
        if (wordCloudStudioState.previewBgCycle === 'light') {
            wrapper.classList.add('preview-bg-light');
        } else if (wordCloudStudioState.previewBgCycle === 'dark') {
            wrapper.classList.add('preview-bg-dark');
        } else if (wordCloudStudioState.previewBgCycle === 'solid_white') {
            wrapper.classList.add('preview-bg-solid-white');
        } else if (wordCloudStudioState.previewBgCycle === 'solid_dark') {
            wrapper.classList.add('preview-bg-solid-dark');
        }
    }
    showToast(`Fundo do preview: ${wordCloudStudioState.previewBgCycle}`, 'info');
}
window.cycleStudioPreviewBg = cycleStudioPreviewBg;

function recalculateStudioPreview() {
    wordCloudStudioState.seed = (wordCloudStudioState.seed || 1) + 1;
    renderStudioPreview();
}
window.recalculateStudioPreview = recalculateStudioPreview;

function updateStudioWordStatusBadges() {
    const rows = document.querySelectorAll('#studioWordsTableBody tr');
    rows.forEach(tr => {
        const text = tr.getAttribute('data-word-text');
        const enabled = tr.getAttribute('data-word-enabled') === 'true';
        const statusCell = tr.querySelector('.studio-word-status-cell');
        if (!statusCell || !text) return;

        let statusHtml = '';
        if (!enabled) {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-100 text-slate-500 dark:bg-[#323238] dark:text-[#A1A1AA]">Inativo</span>`;
        } else if (studioLastPlacedWordTexts && studioLastPlacedWordTexts.has(text)) {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 font-semibold">Visível</span>`;
        } else {
            statusHtml = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 font-medium" title="Não coube no canvas com a forma/fonte atual">Omitido</span>`;
        }
        statusCell.innerHTML = statusHtml;
    });
}
window.updateStudioWordStatusBadges = updateStudioWordStatusBadges;

function renderStudioPreview() {
    const canvas = document.getElementById('studioPreviewCanvas');
    if (!canvas) return;

    const padRange = document.getElementById('studioPaddingRange');
    if (padRange) {
        wordCloudStudioState.padding = parseInt(padRange.value, 10) || 4;
        const padVal = document.getElementById('studioPaddingVal');
        if (padVal) padVal.textContent = `${wordCloudStudioState.padding}px`;
    }

    const maxWordsRange = document.getElementById('studioMaxWordsRange');
    if (maxWordsRange) {
        wordCloudStudioState.maxWords = parseInt(maxWordsRange.value, 10) || 50;
        const maxWordsVal = document.getElementById('studioMaxWordsVal');
        if (maxWordsVal) maxWordsVal.textContent = wordCloudStudioState.maxWords;
    }

    let w = 720;
    let h = 405; // 16:9
    if (wordCloudStudioState.shape === '1x1') {
        w = 480;
        h = 480;
    } else if (wordCloudStudioState.shape === '9x16') {
        w = 340;
        h = 520;
    } else if (wordCloudStudioState.shape === 'circle') {
        w = 520;
        h = 480;
    } else if (wordCloudStudioState.shape === 'speech') {
        w = 600;
        h = 420;
    } else if (wordCloudStudioState.shape === 'heart') {
        w = 540;
        h = 460;
    } else if (wordCloudStudioState.shape === 'cloud') {
        w = 640;
        h = 420;
    } else if (wordCloudStudioState.shape === 'star') {
        w = 560;
        h = 500;
    } else if (wordCloudStudioState.shape === 'trophy') {
        w = 540;
        h = 480;
    } else if (wordCloudStudioState.shape === 'shield') {
        w = 520;
        h = 500;
    } else if (wordCloudStudioState.shape === 'hexagon') {
        w = 560;
        h = 480;
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const result = drawWordCloudToCanvas(canvas, wordCloudStudioState.words, wordCloudStudioState, dpr, true);
    studioLastRenderedBoxes = result.hitboxes || [];
    studioLastPlacedWordTexts = result.placedSet || new Set();
    updateStudioWordStatusBadges();

    const activeList = (wordCloudStudioState.words || []).filter(w => w.enabled);
    const targetWords = Math.min(activeList.length, wordCloudStudioState.maxWords || 50);

    const badge = document.getElementById('studioPlacedWordsBadge');
    if (badge) {
        const pct = targetWords ? Math.round((result.placedCount / targetWords) * 100) : 100;
        badge.innerHTML = `<span class="${pct === 100 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-amber-600 dark:text-amber-400'}">${result.placedCount} de ${targetWords} termos (${pct}% visíveis)</span>`;
    }

    const topWordBadge = document.getElementById('studioTopWordBadge');
    if (topWordBadge) {
        topWordBadge.textContent = result.topWord ? `Top 1: ${result.topWord}` : 'Top 1: -';
    }
}
window.renderStudioPreview = renderStudioPreview;

function applyStudioToDashboard() {
    activeDashboardWordCloudConfig = JSON.parse(JSON.stringify(wordCloudStudioState));
    currentWordCloudData = (wordCloudStudioState.words || []).filter(w => w.enabled);
    renderWordCloud(currentWordCloudData, activeWordCloudFilter);
    closeWordCloudStudio();
    showToast('Configurações do Estúdio aplicadas com sucesso ao Dashboard!', 'success');
}
window.applyStudioToDashboard = applyStudioToDashboard;

function downloadCanvasBlob(canvas, filename) {
    if (canvas.toBlob) {
        canvas.toBlob((blob) => {
            if (!blob) return;
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        }, 'image/png');
    } else {
        const url = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
}
window.downloadCanvasBlob = downloadCanvasBlob;

async function copyStudioImage(mode = 'transparent') {
    const previewCanvas = document.getElementById('studioPreviewCanvas');
    if (!previewCanvas) return;

    let targetCanvas = previewCanvas;
    let filenameFallback = 'nuvem_palavras.png';

    if (mode === 'whatsapp') {
        filenameFallback = 'card_executivo_whatsapp.png';
        const off = document.createElement('canvas');
        const cardW = 1200;
        const cardH = 1200;
        off.width = cardW;
        off.height = cardH;
        const offCtx = off.getContext('2d');

        // Fundo Alabastro Editorial nobre
        offCtx.fillStyle = '#FAF8F5';
        offCtx.fillRect(0, 0, cardW, cardH);

        // Moldura sutil
        offCtx.strokeStyle = '#E4DFD6';
        offCtx.lineWidth = 12;
        offCtx.strokeRect(6, 6, cardW - 12, cardH - 12);

        // Barra institucional no topo
        offCtx.fillStyle = '#1D4ED8';
        offCtx.fillRect(40, 40, cardW - 80, 6);

        // Cabeçalho Executivo
        offCtx.fillStyle = '#111827';
        offCtx.font = '700 32px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif';
        offCtx.textAlign = 'left';
        offCtx.fillText('RASP ANALYTICS • SOCIAL LISTENING', 40, 95);

        offCtx.fillStyle = '#64748B';
        offCtx.font = '400 20px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif';
        const nowStr = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
        offCtx.fillText(`Nuvem de Termos em Alta • Coletado em ${nowStr}`, 40, 130);

        // Renderizar nuvem dedicada em alta resolução
        const cloudCanvas = document.createElement('canvas');
        const cloudW = 1120;
        const cloudH = 880;
        cloudCanvas.width = cloudW;
        cloudCanvas.height = cloudH;

        const cloudConfig = {
            ...wordCloudStudioState,
            bgMode: wordCloudStudioState.bgMode === 'transparent' ? 'transparent' : wordCloudStudioState.bgMode
        };
        drawWordCloudToCanvas(cloudCanvas, wordCloudStudioState.words, cloudConfig, 1.6, false);

        offCtx.drawImage(cloudCanvas, 40, 160, cloudW, cloudH);

        // Rodapé Executivo
        offCtx.fillStyle = '#94A3B8';
        offCtx.font = '500 16px "JetBrains Mono", monospace';
        offCtx.textAlign = 'left';
        offCtx.fillText(`EBM Quintto Comunicação`, 40, cardH - 45);

        const activeWords = (wordCloudStudioState.words || []).filter(w => w.enabled);
        offCtx.textAlign = 'right';
        offCtx.fillText(`${activeWords.length} termos analisados`, cardW - 40, cardH - 45);

        targetCanvas = off;
    } else {
        filenameFallback = `nuvem_transparente_${wordCloudStudioState.shape}.png`;
    }

    if (navigator.clipboard && window.ClipboardItem) {
        targetCanvas.toBlob(async (blob) => {
            if (!blob) {
                showToast('Erro ao capturar imagem', 'error');
                return;
            }
            try {
                await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
                showToast(mode === 'whatsapp' ? 'Card Executivo copiado! Cole no WhatsApp (Ctrl+V)' : 'PNG copiado para a área de transferência!', 'success');
            } catch (err) {
                downloadCanvasBlob(targetCanvas, filenameFallback);
                showToast('Imagem baixada em PNG!', 'success');
            }
        }, 'image/png');
    } else {
        downloadCanvasBlob(targetCanvas, filenameFallback);
        showToast('Imagem baixada em PNG!', 'success');
    }
}
window.copyStudioImage = copyStudioImage;

function copyStudioWordsData() {
    const activeWords = (wordCloudStudioState.words || []).filter(w => w.enabled);
    if (activeWords.length === 0) {
        showToast('Nenhum termo ativo para copiar', 'error');
        return;
    }

    const totalWeight = activeWords.reduce((acc, w) => acc + (w.weight || 0), 0);
    const sorted = [...activeWords].sort((a, b) => (b.weight || 0) - (a.weight || 0));

    let tsv = 'Posição\tTermo\tFrequência\tParticipação\n';
    sorted.forEach((w, i) => {
        const pct = totalWeight ? ((w.weight / totalWeight) * 100).toFixed(1) + '%' : '0%';
        tsv += `${i + 1}\t${w.text}\t${w.weight}\t${pct}\n`;
    });

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(tsv).then(() => {
            showToast(`${sorted.length} termos copiados no formato tabela (Excel/PowerPoint)!`, 'success');
        }).catch(() => {
            showToast('Erro ao copiar dados para clipboard', 'error');
        });
    } else {
        showToast('Clipboard não suportado neste navegador', 'error');
    }
}
window.copyStudioWordsData = copyStudioWordsData;

function downloadStudioImageUltraHD() {
    exportStudioCanvasAtScale(3, 'ultra_hd_3x');
}
window.downloadStudioImageUltraHD = downloadStudioImageUltraHD;

function downloadStudioImage4K() {
    exportStudioCanvasAtScale(4, '4k_ultra_hd');
}
window.downloadStudioImage4K = downloadStudioImage4K;

function exportStudioCanvasAtScale(multiplier, suffix) {
    let baseW = 800;
    let baseH = 450;
    if (wordCloudStudioState.shape === '1x1') {
        baseW = 600;
        baseH = 600;
    } else if (wordCloudStudioState.shape === '9x16') {
        baseW = 450;
        baseH = 800;
    } else if (wordCloudStudioState.shape === 'circle') {
        baseW = 600;
        baseH = 600;
    } else if (wordCloudStudioState.shape === 'speech') {
        baseW = 700;
        baseH = 500;
    } else if (wordCloudStudioState.shape === 'heart') {
        baseW = 650;
        baseH = 550;
    } else if (wordCloudStudioState.shape === 'cloud') {
        baseW = 750;
        baseH = 500;
    } else if (wordCloudStudioState.shape === 'star') {
        baseW = 600;
        baseH = 600;
    } else if (wordCloudStudioState.shape === 'trophy') {
        baseW = 600;
        baseH = 600;
    } else if (wordCloudStudioState.shape === 'shield') {
        baseW = 600;
        baseH = 600;
    } else if (wordCloudStudioState.shape === 'hexagon') {
        baseW = 600;
        baseH = 550;
    }

    const outCanvas = document.createElement('canvas');
    outCanvas.width = baseW * multiplier;
    outCanvas.height = baseH * multiplier;

    drawWordCloudToCanvas(outCanvas, wordCloudStudioState.words, wordCloudStudioState, multiplier, false);

    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = `nuvem_palavras_${wordCloudStudioState.shape}_${suffix}_${timestamp}.png`;
    downloadCanvasBlob(outCanvas, filename);
    showToast(`Download da imagem em alta resolução (${suffix}) iniciado!`, 'success');
}
window.exportStudioCanvasAtScale = exportStudioCanvasAtScale;


// Debounced auto-resize for Word Cloud
let wordCloudResizeDebounce = null;
window.addEventListener('resize', () => {
    clearTimeout(wordCloudResizeDebounce);
    wordCloudResizeDebounce = setTimeout(() => {
        const dashTab = document.getElementById('tab-dashboard');
        if (dashTab && dashTab.classList.contains('active') && currentWordCloudData && currentWordCloudData.length > 0) {
            renderWordCloud(currentWordCloudData, activeWordCloudFilter);
        }
    }, 250);
});

function getPostUrl(item) {
    if (item.link && item.link.startsWith('http')) {
        return item.link;
    }
    const net = (item.network || '').toLowerCase();
    if (net.includes('x') || net.includes('twitter')) return 'https://x.com';
    if (net.includes('tiktok')) return 'https://www.tiktok.com';
    if (net.includes('instagram')) return 'https://www.instagram.com';
    if (net.includes('youtube')) return 'https://www.youtube.com';
    if (net.includes('facebook')) return 'https://www.facebook.com';
    return '#';
}

function getProfileUrl(item) {
    const author = (item.author || '').replace('@', '').trim();
    const net = (item.network || '').toLowerCase();
    if (author && author !== 'perfil_instagram' && author !== 'youtube_canal') {
        if (net.includes('x') || net.includes('twitter')) return `https://x.com/${author}`;
        if (net.includes('tiktok')) return `https://www.tiktok.com/@${author}`;
        if (net.includes('instagram')) return `https://www.instagram.com/${author}`;
        if (net.includes('youtube')) return `https://www.youtube.com/@${author}`;
    }
    return getPostUrl(item);
}

function filterDashboardFeedTable() {
    const feedNetSelect = document.getElementById('feedNetworkFilter');
    if (feedNetSelect && typeof currentDashboardFilter !== 'undefined' && feedNetSelect.value !== currentDashboardFilter.network) {
        setDashboardNetworkFilter(feedNetSelect.value);
        return;
    }

    const rawSearch = (document.getElementById('feedSearchInput')?.value || '').trim();
    if (activeWordCloudFilter && rawSearch.toLowerCase() !== activeWordCloudFilter.toLowerCase()) {
        activeWordCloudFilter = null;
        renderWordCloud(currentWordCloudData, null);
    }

    applyAllDashboardFilters();
}
window.filterDashboardFeedTable = filterDashboardFeedTable;

const FEED_MAX_ROWS = 1500;

function formatShortDate(value) {
    let shortDate = value || 'Sem data';
    if (shortDate.includes('/')) {
        const parts = shortDate.split(' ');
        const dateParts = parts[0].split('/');
        if (parts.length >= 2 && dateParts.length >= 2) {
            shortDate = parts[1] === '00:00' ? `${dateParts[0]}/${dateParts[1]}` : `${dateParts[0]}/${dateParts[1]} ${parts[1]}`;
        } else if (dateParts.length === 3) {
            shortDate = `${dateParts[0]}/${dateParts[1]}/${dateParts[2].slice(-2)}`;
        }
    } else if (shortDate.includes('-')) {
        const parts = shortDate.split(' ');
        const dParts = parts[0].split('-');
        if (dParts.length === 3) {
            const timePart = parts.length > 1 && !['00:00:00', '00:00'].includes(parts[1]) ? ` ${parts[1].substring(0, 5)}` : '';
            shortDate = `${dParts[2]}/${dParts[1]}${timePart}`;
        }
    }
    return shortDate;
}

function renderFeed(feedItems) {
    const tbody = document.getElementById('feedTableBody');
    if (!tbody) return;

    if (!feedItems || feedItems.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-12 text-center text-sm text-slate-500 font-medium">Nenhuma publicação encontrada para o filtro selecionado.</td></tr>';
        return;
    }

    const rows = feedItems.slice(0, FEED_MAX_ROWS).map(item => {
        const n = (item.network || '').toLowerCase();
        const netKey = normalizeNetKey(item.network);
        const netIcon = getNetworkIcon(netKey === 'X' ? 'x' : n);
        const postUrl = escapeHtml(safeHttpUrl(getPostUrl(item)));
        const profileUrl = escapeHtml(safeHttpUrl(getProfileUrl(item)));

        let netBadgeClass = 'bg-slate-100 dark:bg-[#1E1E22] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-[#323238]';
        let netAbbr = netKey;
        if (netKey === 'X') { netBadgeClass = 'bg-slate-900 text-white border-slate-800'; netAbbr = 'X'; }
        else if (netKey === 'TIKTOK') { netBadgeClass = 'bg-black text-cyan-400 border-slate-800'; netAbbr = 'TikTok'; }
        else if (netKey === 'INSTAGRAM') { netBadgeClass = 'bg-[#E1306C] text-white border-transparent'; netAbbr = 'IG'; }
        else if (netKey === 'YOUTUBE') { netBadgeClass = 'bg-red-600 text-white border-red-700'; netAbbr = 'YT'; }
        else if (netKey === 'FACEBOOK') { netBadgeClass = 'bg-blue-600 text-white border-blue-700'; netAbbr = 'FB'; }

        const term = escapeHtml(item.specific_term || item.keyword || 'Geral');
        const author = escapeHtml(item.author || '');
        const likes = escapeHtml(item.likes_str || item.likes || 0);
        const comments = escapeHtml(item.comments_str || item.comments || 0);
        const views = escapeHtml(item.views_str || item.views || 0);
        const shares = Number(item.shares) || 0;

        const metricsStatus = (item.metrics_status || 'coletado').toLowerCase();
        const metricsBadge = metricsStatus === 'exato'
            ? `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 shadow-2xs" title="Métricas oficiais exatas"><i class="fa-solid fa-check-double text-[8px]"></i> Exato</span>`
            : `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-100 text-slate-600 dark:bg-[#1E1E22] dark:text-slate-400" title="Métricas públicas coletadas"><i class="fa-solid fa-calculator text-[8px]"></i> Coletado</span>`;

        let mediaActionHtml = '';
        if (item.transcription_text || item.contact_sheet_url || (item.media_urls && item.media_urls.length > 0)) {
            mediaActionHtml = `
            <div class="mt-1.5 flex items-center gap-1.5 flex-wrap">
                ${(item.media_urls && item.media_urls.length > 0) ? `
                <button type="button" onclick="openMediaModal(${item.id})" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#1D4ED8]/10 text-[#1D4ED8] dark:bg-[#1D4ED8]/20 dark:text-[#60A5FA] border border-[#1D4ED8]/30 dark:border-[#60A5FA]/40 hover:bg-[#1D4ED8]/15 transition-colors" title="Ver mídias coletadas (${item.media_urls.length} arquivos)">
                    <i class="fa-solid fa-images text-[9px]"></i> Mídia (${item.media_urls.length})
                </button>` : ''}
                ${item.transcription_text ? `
                <button type="button" onclick="openMediaModal(${item.id})" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-50 text-teal-700 dark:bg-teal-950/80 dark:text-teal-300 border border-teal-200 dark:border-teal-800 hover:bg-teal-100 transition-colors" title="Ver transcrição fonética local (Whisper)">
                    <i class="fa-solid fa-microphone-lines text-[9px]"></i> Transcrição (${escapeHtml(item.transcription_status || 'ok')})
                </button>` : ''}
                ${item.contact_sheet_url ? `
                <button type="button" onclick="openMediaModal(${item.id})" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#1D4ED8]/10 text-[#1D4ED8] dark:bg-[#1D4ED8]/20 dark:text-[#60A5FA] border border-[#1D4ED8]/30 dark:border-[#60A5FA]/40 hover:bg-[#1D4ED8]/15 transition-colors" title="Ver Folha de Contato 4x4 (FFmpeg)">
                    <i class="fa-solid fa-table-cells text-[9px]"></i> Grade 4x4
                </button>` : ''}
            </div>`;
        } else {
            mediaActionHtml = `
            <div class="mt-1">
                <button type="button" onclick="enrichPostDirectly(${item.id})" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-slate-400 hover:text-[#1D4ED8] dark:hover:text-[#60A5FA] hover:bg-[#1D4ED8]/10 dark:hover:bg-[#1D4ED8]/20 transition-colors" title="Processar mídias e transcrições para este post">
                    <i class="fa-solid fa-film text-[9px]"></i> Enriquecer mídia
                </button>
            </div>`;
        }

        const captionHtml = item.accessibility_caption ? `
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1 italic line-clamp-2" title="Texto alternativo de acessibilidade">
                <i class="fa-solid fa-universal-access mr-1 text-[#1D4ED8] dark:text-[#60A5FA]"></i> ${escapeHtml(item.accessibility_caption)}
            </p>` : '';

        return `
        <tr class="hover:bg-slate-100/80 dark:hover:bg-slate-700/60 transition-colors border-b border-slate-100 dark:border-[#323238]/80">
            <td class="px-2.5 py-3 align-top whitespace-nowrap text-xs font-semibold text-slate-500 dark:text-slate-400">
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-[#1E1E22]/90 text-slate-700 dark:text-slate-300 font-mono text-[11px]" title="${escapeHtml(item.date || '')}">${escapeHtml(formatShortDate(item.date))}</span>
            </td>
            <td class="px-2 py-3 align-top whitespace-nowrap text-center">
                <span class="inline-flex items-center justify-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-extrabold border ${netBadgeClass} shadow-2xs">
                    <i class="fa-brands ${netIcon}"></i>${netKey === 'X' ? '' : ` ${netAbbr}`}
                </span>
            </td>
            <td class="px-2 py-3 align-top text-left">
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-[#1D4ED8]/10 dark:bg-[#1D4ED8]/20 text-[#1D4ED8] dark:text-[#60A5FA] border border-[#1D4ED8]/30 dark:border-[#60A5FA]/40 truncate max-w-[110px]" title="${term}">${term}</span>
            </td>
            <td class="px-2.5 py-3 align-top text-xs font-bold truncate max-w-[120px]" title="${author}">
                <a href="${profileUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-slate-800 dark:text-slate-200 hover:text-[#1D4ED8] dark:hover:text-[#60A5FA] hover:underline transition-colors truncate">
                    <span class="truncate">${author}</span>
                </a>
            </td>
            <td class="px-3 py-3 align-top text-xs text-slate-900 dark:text-slate-100">
                <a href="${postUrl}" target="_blank" rel="noopener noreferrer" title="Abrir a publicação original" class="group font-medium text-slate-900 dark:text-slate-100 hover:text-[#1D4ED8] dark:hover:text-[#60A5FA] transition-colors block leading-relaxed">
                    <span>${escapeHtml((item.text || '').trim())}</span>
                    <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-400 group-hover:text-[#1D4ED8] dark:group-hover:text-[#60A5FA] ml-1 opacity-0 group-hover:opacity-100 transition-opacity"></i>
                </a>
                ${captionHtml}
                ${mediaActionHtml}
            </td>
            <td class="px-2.5 py-3 align-top whitespace-nowrap text-center text-xs font-semibold text-slate-900 dark:text-slate-100">
                <div class="flex flex-col items-center gap-1">
                    <div class="flex items-center gap-1">
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 dark:bg-amber-950/80 text-amber-900 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800 rounded-md text-[11px] font-extrabold shadow-2xs" title="Total de Interações (Curtidas + Comentários)">
                            <i class="fa-solid fa-fire text-amber-500 text-[10px]"></i> ${escapeHtml(item.engagement_str || item.engagement || 0)}
                        </span>
                        ${metricsBadge}
                    </div>
                    <div class="flex items-center justify-center gap-1.5 text-[10px] font-mono">
                        <span class="inline-flex items-center gap-0.5 text-rose-600 dark:text-rose-400 font-bold" title="${likes} curtidas"><i class="fa-solid fa-heart text-[8px]"></i> ${likes}</span>
                        <span class="text-slate-300 dark:text-slate-700">•</span>
                        <span class="inline-flex items-center gap-0.5 text-blue-600 dark:text-blue-400 font-bold" title="${comments} comentários"><i class="fa-solid fa-comment text-[8px]"></i> ${comments}</span>
                        ${Number(item.views) > 0 ? `
                        <span class="text-slate-300 dark:text-slate-700">•</span>
                        <span class="inline-flex items-center gap-0.5 text-purple-600 dark:text-purple-400 font-bold" title="${views} visualizações"><i class="fa-solid fa-eye text-[8px]"></i> ${views}</span>` : ''}
                    </div>
                    ${shares > 0 ? `<span class="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold" title="Compartilhamentos"><i class="fa-solid fa-share text-[8px]"></i> ${escapeHtml(item.shares_str || shares)}</span>` : ''}
                    ${renderCommentChip(item)}
                </div>
            </td>
        </tr>`;
    });

    if (feedItems.length > FEED_MAX_ROWS) {
        rows.push(`<tr><td colspan="6" class="px-6 py-4 text-center text-xs text-slate-500 font-medium">Exibindo as primeiras ${FEED_MAX_ROWS.toLocaleString('pt-BR')} publicações. Use os filtros ou baixe o Excel para ver todas.</td></tr>`);
    }
    tbody.innerHTML = rows.join('');
}

function selectedRunIdForExport() {
    const select = document.getElementById('runHistorySelect');
    return (select && select.value) || lastDashboardData?.run?.run_id || '';
}

function downloadPDF() {
    const runId = selectedRunIdForExport();
    const url = runId ? `${BASE_URL}/api/report/pdf?run_id=${encodeURIComponent(runId)}` : `${BASE_URL}/api/report/pdf`;
    showToast('Gerando relatório PDF...', 'info');
    window.open(url, '_blank');
}
window.downloadPDF = downloadPDF;

function downloadExcel() {
    const runId = selectedRunIdForExport();
    const url = runId ? `${BASE_URL}/api/export/excel?run_id=${encodeURIComponent(runId)}` : `${BASE_URL}/api/export/excel`;
    showToast('Gerando planilha Excel...', 'info');
    window.open(url, '_blank');
}
window.downloadExcel = downloadExcel;

async function deleteSelectedRun() {
    const runId = selectedRunIdForExport();
    if (!runId) {
        showToast('Nenhuma extração selecionada', 'info');
        return;
    }
    const select = document.getElementById('runHistorySelect');
    const label = select?.selectedOptions?.[0]?.textContent || runId;
    if (!confirm(`Excluir esta extração do histórico?\n\n${label}\n\nOs posts dela serão removidos do banco. Planilhas já baixadas não são afetadas.`)) return;
    try {
        const response = await fetch(`${BASE_URL}/api/history/runs/${encodeURIComponent(runId)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha ao excluir extração'));
        showToast('Extração excluída do histórico', 'success');
        await loadDashboardData('', false);
    } catch (error) {
        showToast(error.message || 'Falha ao excluir extração', 'error');
    }
}
window.deleteSelectedRun = deleteSelectedRun;

// SECTION 7C - MULTIMÍDIA E TRANSCRIÇÕES (ZERO TOKEN)
function copyTranscription(postId) {
    const post = (lastDashboardData?.feed || []).find(p => p.id === postId);
    if (!post || !post.transcription_text) {
        showToast('Nenhuma transcrição disponível para copiar.', 'warning');
        return;
    }
    const txt = post.transcription_text;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt)
            .then(() => showToast('Transcrição copiada para a área de transferência!', 'success'))
            .catch(() => {
                const ta = document.createElement('textarea');
                ta.value = txt;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('Transcrição copiada para a área de transferência!', 'success');
            });
    } else {
        const ta = document.createElement('textarea');
        ta.value = txt;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Transcrição copiada para a área de transferência!', 'success');
    }
}
window.copyTranscription = copyTranscription;

function openMediaModal(postId) {
    const post = (lastDashboardData?.feed || []).find(p => p.id === postId);
    if (!post) {
        showToast('Publicação não encontrada no painel atual', 'error');
        return;
    }
    const modal = document.getElementById('mediaModal');
    const content = document.getElementById('mediaModalContent');
    const sub = document.getElementById('mediaModalSub');
    if (!modal || !content) return;

    if (sub) {
        sub.innerHTML = `${escapeHtml(post.author)} • <span class="font-semibold capitalize">${escapeHtml(post.network)}</span> • Post #${postId} • <a href="${safeHttpUrl(post.link)}" target="_blank" class="text-[#1D4ED8] dark:text-[#60A5FA] hover:underline inline-flex items-center gap-1"><i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i> Ver original</a>`;
    }

    let blocks = [];

    // Galeria de Mídias / Carrossel de Imagens
    if (post.media_urls && post.media_urls.length > 0) {
        const mediaCards = post.media_urls.map((url, idx) => `
            <a href="${url}" target="_blank" class="group relative rounded-lg overflow-hidden border border-slate-200 dark:border-[#323238] bg-[#161618] aspect-square flex items-center justify-center hover:opacity-95 transition-opacity" title="Mídia ${idx + 1} - Clique para abrir original">
                ${url.toLowerCase().endsWith('.mp4') || url.toLowerCase().endsWith('.webm')
                    ? `<video src="${url}" class="w-full h-full object-cover pointer-events-none" preload="metadata"></video><div class="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/20"><i class="fa-solid fa-play text-white text-lg"></i></div>`
                    : `<img src="${url}" alt="Mídia ${idx + 1}" class="w-full h-full object-cover" loading="lazy" />`
                }
                <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded text-[10px] bg-black/70 text-white font-mono">#${idx + 1}</span>
            </a>
        `).join('');

        blocks.push(`
        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-semibold text-slate-700 dark:text-[#F4F4F6] flex items-center gap-1.5">
                    <i class="fa-solid fa-images text-[#1D4ED8] dark:text-[#60A5FA]"></i> Galeria de mídias coletadas (${post.media_urls.length} item${post.media_urls.length > 1 ? 's' : ''})
                </h4>
                <span class="text-[11px] text-slate-500 font-mono">${escapeHtml(post.media_type || 'mídia')}</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                ${mediaCards}
            </div>
        </div>`);
    }

    // Folha de Contato 4x4
    if (post.contact_sheet_url) {
        blocks.push(`
        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-semibold text-slate-700 dark:text-[#F4F4F6] flex items-center gap-1.5">
                    <i class="fa-solid fa-table-cells text-[#1D4ED8] dark:text-[#60A5FA]"></i> Folha de contato 4x4 (FFmpeg tile com carimbo de tempo)
                </h4>
                <a href="${post.contact_sheet_url}" target="_blank" download class="text-xs text-[#1D4ED8] dark:text-[#60A5FA] hover:underline flex items-center gap-1">
                    <i class="fa-solid fa-arrow-down"></i> Baixar imagem
                </a>
            </div>
            <div class="rounded-md overflow-hidden border border-slate-200 dark:border-[#323238] bg-black flex items-center justify-center p-1">
                <a href="${post.contact_sheet_url}" target="_blank" title="Clique para ampliar">
                    <img src="${post.contact_sheet_url}" alt="Folha de Contato" class="max-h-[420px] w-auto object-contain rounded-lg hover:opacity-95 transition-opacity cursor-zoom-in" />
                </a>
            </div>
        </div>`);
    }

    // Transcrição Fonética Local
    if (post.transcription_text) {
        const textClean = escapeHtml(post.transcription_text);
        const statusBadge = post.transcription_status === 'done'
            ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">100% Concluída</span>'
            : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(post.transcription_status)}</span>`;

        blocks.push(`
        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-semibold text-slate-700 dark:text-[#F4F4F6] flex items-center gap-1.5">
                    <i class="fa-solid fa-microphone-lines text-teal-500"></i> Transcrição fonética local (faster-whisper CPU int8)
                </h4>
                ${statusBadge}
            </div>
            <div class="relative bg-slate-50 dark:bg-[#1E1E22]/80 p-4 rounded-md border border-slate-200 dark:border-[#323238] text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed select-text font-mono text-xs">
                ${textClean}
                <button type="button" onclick="copyTranscription(${postId})" class="absolute top-2.5 right-2.5 px-2 py-1 text-[11px] rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-[#323238] shadow-2xs hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors flex items-center gap-1 font-sans">
                    <i class="fa-regular fa-copy text-xs"></i> Copiar
                </button>
            </div>
        </div>`);
    }

    // Alt Text / Legenda de acessibilidade
    if (post.accessibility_caption) {
        blocks.push(`
        <div class="space-y-1.5">
            <h4 class="text-xs font-semibold text-slate-700 dark:text-[#F4F4F6] flex items-center gap-1.5">
                <i class="fa-solid fa-universal-access text-[#1D4ED8] dark:text-[#60A5FA]"></i> Legenda de acessibilidade (Alt text coletado)
            </h4>
            <div class="bg-slate-50 dark:bg-[#1E1E22]/60 p-3 rounded-md border border-slate-200 dark:border-[#323238] text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                ${escapeHtml(post.accessibility_caption)}
            </div>
        </div>`);
    }

    if (blocks.length === 0) {
        blocks.push(`
        <div class="text-center py-10 text-slate-500 space-y-3">
            <i class="fa-solid fa-film text-3xl text-slate-400"></i>
            <p>Nenhuma mídia ou transcrição foi processada ainda para esta publicação.</p>
            <button type="button" onclick="closeMediaModal(); enrichPostDirectly(${postId})" class="px-4 py-2 rounded-md text-xs font-bold bg-[#1D4ED8] hover:bg-blue-700 text-white transition-colors inline-flex items-center gap-1.5">
                <i class="fa-solid fa-film"></i> Processar Mídia e Transcrição Agora
            </button>
        </div>`);
    }

    content.innerHTML = blocks.join('');
    modal.classList.remove('hidden');
}
window.openMediaModal = openMediaModal;

function closeMediaModal() {
    document.getElementById('mediaModal')?.classList.add('hidden');
}
window.closeMediaModal = closeMediaModal;

async function enrichPostDirectly(postId) {
    showToast(`Iniciando enriquecimento multimídia do post #${postId}...`, 'info');
    try {
        const response = await fetch(`${BASE_URL}/api/posts/${postId}/enrich`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enrich_media: true, generate_contact_sheet: true, transcribe_audio: true, detect_scenes: true })
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha no enriquecimento'));
        const data = await response.json();
        showToast(`Post #${postId} enriquecido com sucesso!`, 'success');
        const runId = selectedRunIdForExport();
        await loadDashboardData(runId, false);
    } catch (err) {
        showToast(err.message || 'Falha ao enriquecer post', 'error');
    }
}
window.enrichPostDirectly = enrichPostDirectly;

async function enrichCurrentRun() {
    const runId = selectedRunIdForExport();
    if (!runId) {
        showToast('Nenhuma extração selecionada', 'error');
        return;
    }
    if (!confirm('Deseja iniciar o enriquecimento de todas as publicações desta extração?\\n(Download de mídias, folhas de contato 4x4 e transcrições de áudio).')) return;
    showToast('Iniciando enriquecimento da extração em segundo plano...', 'info');
    try {
        const response = await fetch(`${BASE_URL}/api/runs/${encodeURIComponent(runId)}/enrich`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: clientId, enrich_media: true, generate_contact_sheet: true, transcribe_audio: true, detect_scenes: true })
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha ao iniciar enriquecimento da extração'));
        const data = await response.json();
        showToast('Enriquecimento multimídia iniciado em segundo plano!', 'success');
        if (data.data) {
            startTrackingJob(data.data);
        }
    } catch (err) {
        showToast(err.message || 'Falha ao enriquecer extração', 'error');
    }
}
window.enrichCurrentRun = enrichCurrentRun;

// SECTION 7B - COMENTÁRIOS DAS PUBLICAÇÕES
// A coleta roda no servidor (fila de extrações). O painel acompanha por consulta periódica ao job, então
// sobrevive a quedas do WebSocket, recarregamentos da página e várias abas abertas.
const COMMENT_NETWORKS = ['youtube', 'tiktok', 'instagram', 'x', 'facebook'];
const COMMENT_NET_LABELS = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram', x: 'X', facebook: 'Facebook' };
const COMMENT_NET_COLORS = { youtube: 'var(--net-youtube)', tiktok: 'var(--net-tiktok)', instagram: 'var(--net-instagram)', x: 'var(--net-x)', facebook: 'var(--net-facebook)' };
let commentsSummary = null;
let activeCommentsJob = null;
let commentsPollTimer = null;
let commentsLastSummaryAt = 0;
let commentsModalState = { postId: null, offset: 0, total: 0, loading: false, seq: 0 };
let commentsSearchTimer = null;

function commentsRunId() {
    return lastDashboardData?.run?.run_id || '';
}

function commentNetKey(network) {
    const key = normalizeNetKey(network).toLowerCase();
    return COMMENT_NETWORKS.includes(key) ? key : '';
}

function fmtInt(n) {
    return (Number(n) || 0).toLocaleString('pt-BR');
}

async function loadCommentsSummary(runId) {
    if (!runId) {
        commentsSummary = null;
        renderCommentsCard();
        return;
    }
    try {
        const r = await fetchWithRetry(`${BASE_URL}/api/comments/summary?run_id=${encodeURIComponent(runId)}`, {}, 3, 400);
        if (!r.ok || runId !== commentsRunId()) return;
        commentsSummary = await r.json();
        commentsLastSummaryAt = Date.now();
        const statuses = commentsSummary.statuses || {};
        let changed = false;
        (currentRawFeedData || []).forEach(item => {
            const s = statuses[item.id];
            if (s && (item.comments_status !== s[0] || item.comments_collected !== s[1])) {
                [item.comments_status, item.comments_collected, item.comments_error] = s;
                changed = true;
            }
        });
        updateCommentsNetworkSelect();
        updateAdaptiveCommentsMaxPosts();
        renderCommentsCard();
        if (changed) renderFeed(getFilteredFeed());
        const job = commentsSummary.active_job;
        if (job && !FINISHED_JOB_STATUSES.includes(job.status) && (!activeCommentsJob || activeCommentsJob.job_id !== job.job_id)) {
            trackCommentsJob(job, false);
        }
    } catch (e) {
        console.warn('Resumo de comentários indisponível:', e);
    }
}

function getSelectedCommentsNetwork() {
    return document.getElementById('commentsSelectedNetwork')?.value || '';
}

function getCommentsEligibleCount(targetNet = undefined) {
    if (!commentsSummary) return 0;
    const netKey = targetNet !== undefined ? targetNet : getSelectedCommentsNetwork();
    const skipZero = document.getElementById('commentsSkipZero')?.checked !== false;

    if (netKey) {
        const net = (commentsSummary.networks || []).find(n => n.network === netKey);
        if (!net || !net.supported) return 0;
        return (net.pending || 0) + (skipZero ? 0 : (net.pending_zero || 0));
    }

    const t = commentsSummary.totals || {};
    return (t.pending || 0) + (skipZero ? 0 : (t.pending_zero || 0));
}

function pendingCommentsCount() {
    const eligible = getCommentsEligibleCount();
    const maxPostsVal = document.getElementById('commentsMaxPosts')?.value || '';
    const maxPosts = parseInt(maxPostsVal, 10);
    return maxPosts ? Math.min(eligible, maxPosts) : eligible;
}

function updateCommentsNetworkSelect() {
    const select = document.getElementById('commentsSelectedNetwork');
    if (!select) return;
    const prevVal = select.value;
    const skipZero = document.getElementById('commentsSkipZero')?.checked !== false;
    const networks = (commentsSummary?.networks || []).filter(n => n.supported);
    const totalPending = getCommentsEligibleCount('');

    let optionsHtml = `<option value="">Todas as redes (${fmtInt(totalPending)} pendente${totalPending === 1 ? '' : 's'})</option>`;
    networks.forEach(n => {
        const netPending = (n.pending || 0) + (skipZero ? 0 : (n.pending_zero || 0));
        const label = COMMENT_NET_LABELS[n.network] || n.network.toUpperCase();
        optionsHtml += `<option value="${escapeHtml(n.network)}">${escapeHtml(label)} (${fmtInt(netPending)} pendente${netPending === 1 ? '' : 's'})</option>`;
    });

    select.innerHTML = optionsHtml;
    if (prevVal && networks.some(n => n.network === prevVal)) {
        select.value = prevVal;
    } else {
        select.value = '';
    }
}

function updateAdaptiveCommentsMaxPosts() {
    const select = document.getElementById('commentsMaxPosts');
    if (!select) return;

    const eligible = getCommentsEligibleCount();
    const prevVal = select.value;
    const prevCustom = select.dataset.customValue || '';

    const selectedNet = getSelectedCommentsNetwork();
    const targetStats = selectedNet ? (commentsSummary?.networks || []).find(x => x.network === selectedNet) : commentsSummary?.totals;
    const completed = (targetStats?.done || 0) + (targetStats?.empty || 0) + (targetStats?.disabled || 0);
    const hasCompleted = completed > 0;
    const totalSupported = targetStats?.supported || 0;
    const maxReference = hasCompleted ? Math.max(eligible, totalSupported) : eligible;

    if (!eligible || eligible <= 0) {
        if (totalSupported > 0) {
            select.disabled = false;
            let optionsHtml = `<option value="">Todas as publicações (${fmtInt(totalSupported)})</option>`;
            const allTiers = [10, 20, 50, 100, 250, 500, 1000, 2000, 5000, 10000];
            let candidateTiers = allTiers.filter(t => t < totalSupported);
            if (candidateTiers.length > 6) candidateTiers = candidateTiers.slice(candidateTiers.length - 6);
            candidateTiers.forEach(tier => {
                optionsHtml += `<option value="${tier}">${fmtInt(tier)} maiores</option>`;
            });
            if (prevCustom && parseInt(prevCustom, 10) > 0 && parseInt(prevCustom, 10) < totalSupported && !candidateTiers.includes(parseInt(prevCustom, 10))) {
                optionsHtml += `<option value="${prevCustom}">${fmtInt(prevCustom)} maiores (personalizado)</option>`;
            }
            optionsHtml += '<option value="custom">Personalizado…</option>';
            select.innerHTML = optionsHtml;
            const prevInt = parseInt(prevVal, 10);
            if (prevVal === '' || (prevInt && prevInt <= totalSupported)) {
                select.value = prevVal;
            } else {
                select.value = '';
            }
            return;
        }
        select.innerHTML = '<option value="">Nenhuma pendente (0)</option>';
        select.disabled = true;
        return;
    }

    select.disabled = false;
    const allLabel = hasCompleted ? 'Todas as pendentes' : 'Todas';
    let optionsHtml = `<option value="">${allLabel} (${fmtInt(eligible)} publicaç${eligible === 1 ? 'ão' : 'ões'})</option>`;

    // Patamares padrão dinâmicos adequados à quantidade real encontrada
    const allTiers = [10, 20, 50, 100, 250, 500, 1000, 2000, 5000, 10000];
    let candidateTiers = allTiers.filter(t => t < maxReference);

    // Se houver mais de 6 opções (ex: 3000 posts), mantém os patamares superiores mais expressivos
    if (candidateTiers.length > 6) {
        candidateTiers = candidateTiers.slice(candidateTiers.length - 6);
    }

    candidateTiers.forEach(tier => {
        let label;
        if (!hasCompleted) {
            label = `${fmtInt(tier)} maiores`;
        } else if (tier <= eligible) {
            label = `${fmtInt(tier)} maiores pendentes`;
        } else {
            label = `${fmtInt(tier)} maiores (recoleta da base)`;
        }
        optionsHtml += `<option value="${tier}">${label}</option>`;
    });

    if (prevCustom && parseInt(prevCustom, 10) > 0 && parseInt(prevCustom, 10) < maxReference && !candidateTiers.includes(parseInt(prevCustom, 10))) {
        const customInt = parseInt(prevCustom, 10);
        let customLabel;
        if (!hasCompleted) {
            customLabel = `${fmtInt(prevCustom)} maiores (personalizado)`;
        } else if (customInt <= eligible) {
            customLabel = `${fmtInt(prevCustom)} maiores pendentes (personalizado)`;
        } else {
            customLabel = `${fmtInt(prevCustom)} maiores (personalizado)`;
        }
        optionsHtml += `<option value="${prevCustom}">${customLabel}</option>`;
    }

    optionsHtml += '<option value="custom">Personalizado…</option>';
    select.innerHTML = optionsHtml;

    const prevInt = parseInt(prevVal, 10);
    if (prevVal === '' || (prevInt && prevInt <= maxReference)) {
        select.value = prevVal;
    } else {
        select.value = '';
    }
}

function onCommentsNetworkChange() {
    updateAdaptiveCommentsMaxPosts();
    renderCommentsCard();
}
window.onCommentsNetworkChange = onCommentsNetworkChange;

function onCommentsFilterChange() {
    updateCommentsNetworkSelect();
    updateAdaptiveCommentsMaxPosts();
    renderCommentsCard();
}
window.onCommentsFilterChange = onCommentsFilterChange;

function onCommentsMaxPostsChange() {
    const select = document.getElementById('commentsMaxPosts');
    if (!select) return;

    if (select.value === 'custom') {
        const eligible = getCommentsEligibleCount();
        const selectedNet = getSelectedCommentsNetwork();
        const targetStats = selectedNet ? (commentsSummary?.networks || []).find(x => x.network === selectedNet) : commentsSummary?.totals;
        const totalSupported = targetStats?.supported || 0;
        const hasCompleted = ((targetStats?.done || 0) + (targetStats?.empty || 0) + (targetStats?.disabled || 0)) > 0;
        const maxLimit = hasCompleted ? Math.max(eligible, totalSupported) : eligible;
        const input = prompt(`Informe a quantidade máxima de publicações (máximo: ${fmtInt(maxLimit)}):`, '50');
        const num = parseInt((input || '').replace(/\D/g, ''), 10);
        if (num && num > 0) {
            const finalVal = Math.min(num, maxLimit);
            select.dataset.customValue = String(finalVal);
            updateAdaptiveCommentsMaxPosts();
            select.value = String(finalVal);
        } else {
            select.value = '';
        }
    }
    renderCommentsCard();
}
window.onCommentsMaxPostsChange = onCommentsMaxPostsChange;

function selectCommentsNetwork(net) {
    const select = document.getElementById('commentsSelectedNetwork');
    if (select) {
        select.value = net || '';
        onCommentsNetworkChange();
    }
}
window.selectCommentsNetwork = selectCommentsNetwork;

function renderCommentsCard() {
    const sub = document.getElementById('commentsSubtitle');
    const stats = document.getElementById('commentsNetworkStats');
    const btn = document.getElementById('btnCommentsStart');
    const viewBtn = document.getElementById('btnCommentsView');
    const recollect = document.getElementById('btnCommentsRecollect');
    if (!sub || !stats || !btn) return;
    const t = commentsSummary?.totals || {};
    const running = !!activeCommentsJob;
    const selectedNet = getSelectedCommentsNetwork();
    const netLabel = selectedNet ? (COMMENT_NET_LABELS[selectedNet] || selectedNet.toUpperCase()) : '';
    const pending = pendingCommentsCount();

    if (!commentsSummary) {
        sub.textContent = commentsRunId() ? 'Carregando…' : 'Execute uma extração para coletar os comentários das publicações.';
    } else if (!t.supported) {
        sub.textContent = 'Nenhuma publicação desta extração tem link compatível com a coleta de comentários.';
    } else {
        let statsObj = t;
        let prefix = '';
        if (selectedNet) {
            const n = (commentsSummary?.networks || []).find(x => x.network === selectedNet);
            if (n) {
                statsObj = n;
                prefix = `[${netLabel}] `;
            }
        }
        const failed = (statsObj.error || 0) + (statsObj.login || 0);
        const parts = [`${prefix}${fmtInt(statsObj.comments || 0)} comentários coletados de ${fmtInt((statsObj.done || 0) + (statsObj.partial || 0))} publicações`];
        parts.push(pending ? `${fmtInt(pending)} pendente${pending === 1 ? '' : 's'}` : 'nenhuma pendente');
        if (statsObj.pending_zero && document.getElementById('commentsSkipZero')?.checked !== false) {
            parts.push(`${fmtInt(statsObj.pending_zero)} sem comentários serão puladas`);
        }
        if (failed) parts.push(`${fmtInt(failed)} com falha (serão tentadas de novo)`);
        sub.textContent = parts.join(' • ');
    }

    stats.innerHTML = (commentsSummary?.networks || []).filter(n => n.supported).map(n => {
        const failed = (n.error || 0) + (n.login || 0);
        const isSelected = selectedNet === n.network;
        const activeStyle = isSelected ? 'box-shadow: 0 0 0 2px var(--rp-accent); font-weight: 700; transform: translateY(-1px);' : '';
        const title = [`${n.supported} publicações`, `${n.done || 0} concluídas`, `${n.partial || 0} parciais`, `${n.empty || 0} sem comentários`,
            `${n.disabled || 0} desativados`, `${n.error || 0} com falha`, `${n.login || 0} aguardando login`, 'Clique para filtrar por esta rede'].join(' • ');
        return `<span class="rp-net-stat cursor-pointer transition-all" style="${activeStyle}" onclick="selectCommentsNetwork('${n.network}')" title="${escapeHtml(title)}"><span class="rp-dot" style="background:${COMMENT_NET_COLORS[n.network]}"></span>
            ${COMMENT_NET_LABELS[n.network] || escapeHtml(n.network)} <b>${fmtInt(n.comments)}</b>
            ${failed ? `<span class="rp-cchip ${n.login ? 'warn' : 'bad'} muted" style="cursor:help">${n.login ? '<i class="fa-solid fa-lock"></i> login' : `${failed} falha${failed > 1 ? 's' : ''}`}</span>` : ''}</span>`;
    }).join('');

    btn.disabled = running || !pending;
    const actionText = running ? 'Coletando…' : (pending ? (selectedNet ? `Coletar ${netLabel} (${fmtInt(pending)})` : `Coletar comentários (${fmtInt(pending)})`) : 'Tudo coletado');
    const spanEl = btn.querySelector('span');
    if (spanEl) {
        spanEl.textContent = actionText;
    } else {
        btn.textContent = actionText;
    }
    const iconEl = btn.querySelector('i');
    if (iconEl) {
        iconEl.className = running ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-comment-dots';
    }
    if (viewBtn) viewBtn.disabled = !(t.comments > 0);
    if (recollect) {
        recollect.classList.toggle('hidden', running || !t.supported);
        const maxPostsVal = document.getElementById('commentsMaxPosts')?.value || '';
        const maxPostsNum = parseInt(maxPostsVal, 10);
        if (maxPostsNum && maxPostsNum > 0) {
            recollect.textContent = `Recoletar as ${fmtInt(maxPostsNum)} maiores`;
            recollect.title = `Recoletar os comentários das ${fmtInt(maxPostsNum)} maiores publicações da base (mesmo as já concluídas)`;
        } else {
            recollect.textContent = 'Recoletar todas';
            recollect.title = 'Recoletar os comentários de todas as publicações da base (mesmo as já concluídas)';
        }
    }
}
window.renderCommentsCard = renderCommentsCard;

function renderCommentChip(item) {
    const net = commentNetKey(item.network);
    if (!net || !/^https?:\/\//i.test(item.link || '')) return '';
    const status = item.comments_status || '';
    const n = Number(item.comments_collected) || 0;
    const err = escapeHtml(item.comments_error || '');
    const id = Number(item.id);
    if (n > 0) {
        const cls = status === 'partial' ? 'warn' : 'ok';
        const title = status === 'partial' ? `Coleta parcial${err ? ': ' + err : ''} — clique para ler` : 'Ler comentários coletados';
        return `<button type="button" class="rp-cchip ${cls}" title="${title}" onclick="openCommentsModal(${id})"><i class="fa-regular fa-comment"></i> ${fmtInt(n)}</button>`;
    }
    if (status === 'empty') return '<span class="rp-cchip muted" title="Coletado: nenhum comentário">sem comentários</span>';
    if (status === 'disabled') return '<span class="rp-cchip muted" title="O autor desativou os comentários">desativados</span>';
    if (status === 'login') return `<button type="button" class="rp-cchip warn" title="${err || 'Conecte a conta em Contas'} — clique para tentar de novo" onclick="collectPostComments(${id})"><i class="fa-solid fa-lock"></i> login</button>`;
    if (status === 'error' || status === 'partial') return `<button type="button" class="rp-cchip bad" title="${err || 'Falha'} — clique para tentar de novo" onclick="collectPostComments(${id})"><i class="fa-solid fa-rotate-right"></i> falhou</button>`;
    return `<button type="button" class="rp-cchip" title="Coletar os comentários desta publicação" onclick="collectPostComments(${id})"><i class="fa-regular fa-comment"></i> coletar</button>`;
}

async function startCommentsCollection(options = {}) {
    const runId = commentsRunId();
    if (!runId) {
        showToast('Nenhuma extração carregada no dashboard', 'info');
        return;
    }
    if (activeCommentsJob) {
        showToast('Já existe uma coleta de comentários em andamento', 'info');
        return;
    }
    const mode = options.mode || 'pending';
    const selectedNet = getSelectedCommentsNetwork();
    const netLabel = selectedNet ? (COMMENT_NET_LABELS[selectedNet] || selectedNet.toUpperCase()) : 'todas as redes';

    const maxPosts = parseInt(document.getElementById('commentsMaxPosts')?.value || '', 10);
    const targetDesc = (maxPosts && maxPosts > 0) ? `das ${fmtInt(maxPosts)} maiores publicações` : 'de todas as publicações';
    if (mode === 'all' && !options.postIds &&
        !confirm(`Recoletar os comentários ${targetDesc} (${netLabel}) desta extração?\n\nOs comentários já salvos são mantidos e não serão duplicados.`)) {
        return;
    }
    const payload = {
        client_id: clientId,
        run_id: runId,
        mode,
        post_ids: options.postIds || null,
        networks: options.postIds ? null : (selectedNet ? [selectedNet] : null),
        max_per_post: parseInt(document.getElementById('commentsMaxPerPost')?.value || '100', 10) || 100,
        max_posts: options.postIds ? null : (maxPosts || null),
        skip_zero: document.getElementById('commentsSkipZero')?.checked !== false
    };
    const btn = document.getElementById('btnCommentsStart');
    if (btn) btn.disabled = true;
    try {
        connectWebSocket().catch(() => {});
        const r = await fetch(`${BASE_URL}/api/comments/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!r.ok) throw new Error(await readErrorDetail(r, 'Não foi possível iniciar a coleta de comentários'));
        const data = await r.json();
        if (data.status === 'already_running') showToast('Esta extração já está coletando comentários — acompanhando a coleta atual', 'info');
        else showToast(options.postIds ? 'Coletando os comentários da publicação…' : `Coleta de comentários iniciada (${netLabel})`, 'success');
        trackCommentsJob(data.data, data.status !== 'already_running');
    } catch (error) {
        showToast(error.message || 'Falha ao iniciar a coleta de comentários', 'error');
        renderCommentsCard();
    }
}
window.startCommentsCollection = startCommentsCollection;

function collectPostComments(postId) {
    startCommentsCollection({ mode: 'all', postIds: [postId] });
}
window.collectPostComments = collectPostComments;

function trackCommentsJob(job, fresh) {
    activeCommentsJob = job;
    try { sessionStorage.setItem('raspActiveCommentsJob', job.job_id); } catch (e) {}
    document.getElementById('commentsProgress')?.classList.remove('hidden');
    const cancelBtn = document.getElementById('btnCommentsCancel');
    if (cancelBtn) { cancelBtn.classList.remove('hidden'); cancelBtn.disabled = false; }
    if (fresh) renderCommentsLog([]);
    updateCommentsProgress(job);
    renderCommentsCard();
    clearInterval(commentsPollTimer);
    pollCommentsJob();
    commentsPollTimer = setInterval(pollCommentsJob, 2500);
}

async function pollCommentsJob() {
    const job = activeCommentsJob;
    if (!job) return;
    try {
        const r = await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(job.job_id)}?logs=true`);
        if (r.status === 404) {
            finishCommentsJob({ ...job, status: 'error', error: 'O servidor foi reiniciado. O que já foi coletado está salvo — clique em Coletar para continuar.' });
            return;
        }
        if (!r.ok) return;
        const data = await r.json();
        renderCommentsLog(data.logs || []);
        handleCommentsJobUpdate(data);
    } catch (e) {
        // servidor momentaneamente indisponível: tenta de novo na próxima rodada
    }
}

function handleCommentsJobUpdate(job) {
    if (!job || !activeCommentsJob || job.job_id !== activeCommentsJob.job_id) return;
    activeCommentsJob = { ...activeCommentsJob, ...job };
    updateCommentsProgress(job);
    if (FINISHED_JOB_STATUSES.includes(job.status)) {
        finishCommentsJob(job);
        return;
    }
    // Atualiza contadores e selos da tabela durante a coleta, sem sobrecarregar o servidor
    if (Date.now() - commentsLastSummaryAt > 6000 && job.run_id === commentsRunId()) {
        commentsLastSummaryAt = Date.now();
        loadCommentsSummary(job.run_id);
    }
}

function updateCommentsProgress(job) {
    const bar = document.getElementById('commentsProgressBar');
    const text = document.getElementById('commentsProgressText');
    const total = job.progress?.total || 0;
    const done = job.progress?.done || 0;
    let pct = total ? Math.round(done / total * 100) : 0;
    if (FINISHED_JOB_STATUSES.includes(job.status)) pct = 100;
    else if (pct < 3) pct = 3;
    if (bar) bar.style.width = `${pct}%`;
    if (!text) return;
    const comments = `${fmtInt(job.total_comments)} comentários`;
    const labels = { queued: 'Na fila', running: 'Coletando', done: 'Concluído', cancelled: 'Cancelado', error: 'Interrompido' };
    text.textContent = `${labels[job.status] || 'Coletando'} • ${fmtInt(done)}/${fmtInt(total)} publicações • ${comments}`;
}

function renderCommentsLog(lines) {
    const box = document.getElementById('commentsLog');
    if (!box) return;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    box.innerHTML = lines.slice(-80).map(line => {
        const m = String(line).match(/^\[(\w+)\]\s?([\s\S]*)$/);
        if (m && LOG_TAG_STYLES[m[1]]) return `<div><span class="${LOG_TAG_STYLES[m[1]]}">[${m[1]}]</span> ${escapeHtml(m[2])}</div>`;
        return `<div>${escapeHtml(line)}</div>`;
    }).join('') || '<div class="text-gray-500">[SYSTEM] Preparando a coleta…</div>';
    if (nearBottom || lines.length < 4) box.scrollTop = box.scrollHeight;
}

function finishCommentsJob(job) {
    clearInterval(commentsPollTimer);
    commentsPollTimer = null;
    activeCommentsJob = null;
    try { sessionStorage.removeItem('raspActiveCommentsJob'); } catch (e) {}
    updateCommentsProgress(job);
    document.getElementById('btnCommentsCancel')?.classList.add('hidden');
    if (job.status === 'done') {
        showToast(`Coleta concluída: ${fmtInt(job.total_comments)} comentários`, 'success');
    } else if (job.status === 'cancelled') {
        showToast('Coleta cancelada — os comentários coletados foram salvos', 'info');
    } else {
        showToast(job.error || 'A coleta de comentários foi interrompida — o que já foi coletado está salvo', 'error');
    }
    // Busca o log completo uma última vez (a mensagem final pode ter chegado depois da última consulta)
    fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(job.job_id)}?logs=true`)
        .then(r => (r.ok ? r.json() : null)).then(d => d && renderCommentsLog(d.logs || [])).catch(() => {});
    if (job.run_id && job.run_id === commentsRunId()) loadCommentsSummary(job.run_id);
    else renderCommentsCard();
}

async function cancelCommentsCollection() {
    if (!activeCommentsJob) return;
    if (!confirm('Cancelar a coleta de comentários? O que já foi coletado continua salvo e as publicações restantes ficam pendentes.')) return;
    const btn = document.getElementById('btnCommentsCancel');
    if (btn) btn.disabled = true;
    try {
        await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(activeCommentsJob.job_id)}/cancel`, { method: 'POST' });
        showToast('Cancelando: finalizando a publicação atual…', 'info');
    } catch (e) {
        showToast('Não foi possível cancelar agora', 'error');
        if (btn) btn.disabled = false;
    }
}
window.cancelCommentsCollection = cancelCommentsCollection;

async function restoreActiveCommentsJob() {
    let jobId = null;
    try { jobId = sessionStorage.getItem('raspActiveCommentsJob'); } catch (e) {}
    if (!jobId) return;
    try {
        const r = await fetch(`${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}?logs=true`);
        if (!r.ok) {
            sessionStorage.removeItem('raspActiveCommentsJob');
            return;
        }
        const job = await r.json();
        if (FINISHED_JOB_STATUSES.includes(job.status)) {
            sessionStorage.removeItem('raspActiveCommentsJob');
            return;
        }
        trackCommentsJob(job, false);
        renderCommentsLog(job.logs || []);
    } catch (e) {
        console.warn('Não foi possível retomar a coleta de comentários:', e);
    }
}

// ---- Leitura dos comentários
function openCommentsModal(postId = null) {
    const modal = document.getElementById('commentsModal');
    if (!modal || !commentsRunId()) return;
    commentsModalState.postId = postId;
    const post = postId ? (currentRawFeedData || []).find(p => p.id === postId) : null;
    document.getElementById('commentsModalTitle').textContent = post ? `Comentários de ${post.author || 'publicação'}` : 'Comentários da extração';
    const sub = document.getElementById('commentsModalSub');
    sub.textContent = post ? (post.text || '') : (lastDashboardData?.run?.query || '').replace(/\s*\|\s*/g, ', ');
    sub.title = sub.textContent;
    const search = document.getElementById('commentsSearch');
    if (search) search.value = '';
    const netFilter = document.getElementById('commentsNetworkFilter');
    if (netFilter) {
        netFilter.value = '';
        netFilter.classList.toggle('hidden', !!postId);
    }
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadCommentsPage(true);
    setTimeout(() => search?.focus(), 50);
}
window.openCommentsModal = openCommentsModal;

function closeCommentsModal() {
    document.getElementById('commentsModal')?.classList.add('hidden');
    document.body.style.overflow = '';
}
window.closeCommentsModal = closeCommentsModal;

function onCommentsSearch() {
    clearTimeout(commentsSearchTimer);
    commentsSearchTimer = setTimeout(() => loadCommentsPage(true), 300);
}
window.onCommentsSearch = onCommentsSearch;

async function loadCommentsPage(reset) {
    const list = document.getElementById('commentsModalList');
    const moreBtn = document.getElementById('btnCommentsMore');
    const count = document.getElementById('commentsModalCount');
    if (!list) return;
    const state = commentsModalState;
    const seq = ++state.seq;  // descarta respostas de buscas antigas
    if (reset) {
        state.offset = 0;
        list.innerHTML = '<p class="rp-muted-text py-10 text-center"><i class="fa-solid fa-circle-notch fa-spin mr-1.5"></i>Carregando comentários…</p>';
    }
    if (moreBtn) moreBtn.disabled = true;
    const params = new URLSearchParams({ run_id: commentsRunId(), limit: '200', offset: String(state.offset) });
    if (state.postId) params.set('post_id', state.postId);
    const q = (document.getElementById('commentsSearch')?.value || '').trim();
    if (q) params.set('q', q);
    const net = document.getElementById('commentsNetworkFilter')?.value || '';
    if (net && !state.postId) params.set('network', net);
    try {
        const r = await fetchWithRetry(`${BASE_URL}/api/comments?${params}`, {}, 3, 400);
        if (seq !== state.seq) return;
        if (!r.ok) throw new Error(await readErrorDetail(r, 'Falha ao carregar comentários'));
        const data = await r.json();
        state.total = data.total || 0;
        const html = (data.items || []).map(c => {
            const netKey = c.network || '';
            const post = c.post || {};
            const meta = [c.date ? escapeHtml(formatCommentDate(c.date)) : '', c.likes ? `<i class="fa-solid fa-heart text-[9px]"></i> ${fmtInt(c.likes)}` : '',
                c.replies ? `${fmtInt(c.replies)} resposta${c.replies > 1 ? 's' : ''}` : '', c.parent_id ? 'resposta' : ''].filter(Boolean).join(' • ');
            const ctx = state.postId ? '' : `<p class="ctx"><span class="rp-dot" style="background:${COMMENT_NET_COLORS[netKey] || 'var(--rp-muted)'}"></span>
                em <a href="${escapeHtml(safeHttpUrl(post.link))}" target="_blank" rel="noopener noreferrer">${escapeHtml(post.author || 'publicação')}</a>:
                ${escapeHtml((post.text || '').slice(0, 110))}${(post.text || '').length > 110 ? '…' : ''}</p>`;
            return `<div class="rp-comment"><div class="flex flex-wrap items-baseline gap-x-2"><span class="who">${escapeHtml(c.author || 'Anônimo')}</span><span class="meta">${meta}</span></div>
                <p class="body">${escapeHtml(c.text || '')}</p>${ctx}</div>`;
        }).join('');
        if (reset) list.innerHTML = html || '<p class="rp-muted-text py-10 text-center">Nenhum comentário encontrado.</p>';
        else list.insertAdjacentHTML('beforeend', html);
        state.offset += (data.items || []).length;
        if (count) count.textContent = `${fmtInt(Math.min(state.offset, state.total))} de ${fmtInt(state.total)} comentários`;
        if (moreBtn) {
            moreBtn.classList.toggle('hidden', state.offset >= state.total);
            moreBtn.disabled = false;
        }
    } catch (error) {
        if (seq !== state.seq) return;
        if (reset) list.innerHTML = `<p class="rp-muted-text py-10 text-center">${escapeHtml(error.message || 'Falha ao carregar comentários')}</p>`;
        else showToast(error.message || 'Falha ao carregar mais comentários', 'error');
        if (moreBtn) moreBtn.disabled = false;
    }
}
window.loadCommentsPage = loadCommentsPage;

function formatCommentDate(value) {
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : value;
}

// SECTION 8 - SCHEDULES
const CRON_LABELS = {
    '0 8 * * *': 'Diário às 8h',
    '0 12 * * *': 'Diário às 12h',
    '0 18 * * *': 'Diário às 18h',
    '0 8,18 * * *': 'Diário às 8h e 18h',
    '0 */6 * * *': 'A cada 6 horas',
    '0 8 * * 1-5': 'Dias úteis às 8h',
    '0 8 * * 1': 'Toda Segunda às 8h',
    '0 8 * * 5': 'Toda Sexta às 8h'
};

async function loadSchedules(isInitialLoad = false) {
    try {
        const response = await fetchWithRetry(`${BASE_URL}/api/schedules`, {}, isInitialLoad ? 4 : 2, 350);
        if (!response.ok) return;
        const data = await response.json();
        const container = document.getElementById('schedulesList');
        if (!container) return;

        const schedules = data.schedules || [];
        if (schedules.length === 0) {
            container.innerHTML = '<div class="px-6 py-8 text-center text-sm text-slate-500">Nenhum agendamento configurado.</div>';
            return;
        }

        container.innerHTML = schedules.map(sch => {
            const active = sch.status === 'active';
            const id = escapeHtml(sch.id);
            const keywords = escapeHtml((sch.keywords || []).join(', '));
            const nets = (sch.networks || []).map(n => `<i class="fa-brands ${getNetworkIcon(n)}" title="${escapeHtml(getNetworkName(n))}"></i>`).join(' ');
            return `
            <div class="px-5 py-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold border ${active ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'}">${active ? 'Ativo' : 'Pausado'}</span>
                        <span class="text-xs font-medium text-slate-500 dark:text-slate-400">${sch.search_type === 'profile' ? 'Perfil / Marca' : 'Palavra-chave'}</span>
                    </div>
                    <p class="mt-1 font-bold text-sm text-slate-900 truncate" title="${keywords}">${keywords}</p>
                    <p class="mt-1 text-xs text-slate-500 flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span><i class="fa-regular fa-clock mr-1"></i>${escapeHtml(CRON_LABELS[sch.cron] || `Cron: ${sch.cron}`)}</span>
                        <span class="text-slate-700 space-x-1">${nets}</span>
                        <span>${Number(sch.limit) || 50} posts/rede</span>
                        ${active && sch.next_run ? `<span>Próxima: ${escapeHtml(sch.next_run)}</span>` : ''}
                        ${sch.last_run_at ? `<span>Última: ${escapeHtml(sch.last_run_at)}</span>` : ''}
                    </p>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                    <button type="button" data-id="${id}" onclick="runScheduleNow(this.dataset.id)" class="px-2.5 py-1.5 text-xs font-bold rounded-lg border border-[#1D4ED8]/30 dark:border-[#60A5FA]/40 text-[#1D4ED8] dark:text-[#60A5FA] bg-[#1D4ED8]/10 dark:bg-[#1D4ED8]/20 hover:bg-[#1D4ED8]/20 transition-colors" title="Executar agora"><i class="fa-solid fa-play text-[10px]"></i> Executar</button>
                    <button type="button" data-id="${id}" data-status="${active ? 'paused' : 'active'}" onclick="toggleSchedule(this.dataset.id, this.dataset.status)" class="px-2.5 py-1.5 text-xs font-bold rounded-lg border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 transition-colors">
                        <i class="fa-solid ${active ? 'fa-pause' : 'fa-rotate-right'} text-[10px]"></i> ${active ? 'Pausar' : 'Retomar'}
                    </button>
                    <button type="button" data-id="${id}" onclick="deleteSchedule(this.dataset.id)" class="p-1.5 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition-colors" title="Excluir agendamento"><i class="fa-solid fa-trash-can text-sm"></i></button>
                </div>
            </div>`;
        }).join('');
    } catch (error) {
        console.warn('Erro ao carregar agendamentos:', error);
    }
}

async function handleScheduleSubmit(e) {
    e.preventDefault();

    const searchType = document.querySelector('input[name="sch_search_type"]:checked')?.value || 'keyword';
    let keywords = [];
    if (searchType === 'profile') {
        const brand = document.getElementById('schBrandSelect')?.value;
        if (!brand) {
            showToast('Selecione uma marca para o agendamento', 'error');
            return;
        }
        keywords = [brand];
    } else {
        const text = (document.getElementById('schKeywordEditor')?.innerText || '').replace(/ /g, ' ').trim();
        keywords = text.split(',').map(k => k.trim()).filter(Boolean);
        if (keywords.length === 0) {
            showToast('Adicione sua expressão de busca (Lógica Booleana)', 'error');
            return;
        }
    }

    const networks = Array.from(document.querySelectorAll('input[name="schNetwork"]:checked')).map(cb => cb.value);
    if (networks.length === 0) {
        showToast('Selecione pelo menos uma rede para o agendamento', 'error');
        return;
    }

    const payload = {
        keywords,
        networks,
        search_type: searchType,
        cron: document.getElementById('schCron').value,
        limit: Math.min(1000, Math.max(1, parseInt(document.getElementById('schLimit')?.value, 10) || 50))
    };

    const btn = document.getElementById('btnCreateSchedule');
    if (btn) btn.disabled = true;
    try {
        const response = await fetch(`${BASE_URL}/api/schedules`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Erro ao criar agendamento'));

        showToast('Agendamento criado com sucesso', 'success');
        document.getElementById('scheduleForm').reset();
        document.getElementById('schKeywordEditor').innerHTML = '';
        updateSearchMode('keyword', 'sch');
        await loadSchedules();
    } catch (error) {
        console.error(error);
        showToast(error.message || 'Falha ao criar agendamento', 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function runScheduleNow(id) {
    try {
        const response = await fetch(`${BASE_URL}/api/schedules/${encodeURIComponent(id)}/run`, { method: 'POST' });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha ao executar'));
        showToast('Execução iniciada em segundo plano. O resultado aparecerá no Dashboard.', 'success');
        setTimeout(() => loadSchedules(), 1500);
    } catch (error) {
        showToast(error.message || 'Falha ao executar agendamento', 'error');
    }
}
window.runScheduleNow = runScheduleNow;

async function toggleSchedule(id, status) {
    try {
        const response = await fetch(`${BASE_URL}/api/schedules/${encodeURIComponent(id)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha ao atualizar'));
        showToast(status === 'active' ? 'Agendamento retomado' : 'Agendamento pausado', 'success');
        await loadSchedules();
    } catch (error) {
        showToast(error.message || 'Falha ao atualizar agendamento', 'error');
    }
}
window.toggleSchedule = toggleSchedule;

async function deleteSchedule(id) {
    if (!confirm('Excluir este agendamento? As extrações já realizadas continuam no histórico.')) return;
    try {
        const response = await fetch(`${BASE_URL}/api/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Falha ao excluir'));
        showToast('Agendamento excluído', 'success');
        await loadSchedules();
    } catch (error) {
        showToast(error.message || 'Falha ao excluir agendamento', 'error');
    }
}
window.deleteSchedule = deleteSchedule;

// SECTION 9 - SEARCH MODE (palavra-chave x perfil/marca)
function updateSearchMode(mode, context) {
    const prefix = context === 'sch' ? 'sch' : 'scrape';
    const isKeyword = mode === 'keyword';
    document.getElementById(`${prefix}KeywordContainer`)?.classList.toggle('hidden', !isKeyword);
    document.getElementById(`${prefix}BrandsContainer`)?.classList.toggle('hidden', isKeyword);
    const label = document.getElementById(`${prefix}InputLabel`);
    if (label) label.textContent = isKeyword ? 'Termos de Busca (Lógica Booleana)' : 'Perfil / Marca (Benchmarking)';
}
window.updateSearchMode = updateSearchMode;

// SECTION 10 - BRANDS
const BRAND_NETWORKS = [
    { key: 'x', label: 'X', icon: 'fa-x-twitter text-slate-800 dark:text-slate-100', input: 'brandX' },
    { key: 'instagram', label: 'Instagram', icon: 'fa-instagram text-pink-500', input: 'brandInstagram' },
    { key: 'tiktok', label: 'TikTok', icon: 'fa-tiktok text-cyan-400', input: 'brandTiktok' },
    { key: 'youtube', label: 'YouTube', icon: 'fa-youtube text-red-500', input: 'brandYoutube' },
    { key: 'facebook', label: 'Facebook', icon: 'fa-facebook text-blue-500', input: 'brandFacebook' }
];

async function loadBrandsList(isInitialLoad = false) {
    try {
        const response = await fetchWithRetry(`${BASE_URL}/api/brands`, {}, isInitialLoad ? 4 : 2, 350);
        if (!response.ok) return;
        const data = await response.json();
        allBrands = data.brands || {};
        renderBrandsTable();
        renderBrandSelects();
    } catch (error) {
        console.warn('Erro ao carregar marcas:', error);
    }
}

function renderBrandsTable() {
    const tbody = document.getElementById('brandsTableBody');
    if (!tbody) return;

    const brandNames = Object.keys(allBrands);
    if (brandNames.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-sm text-slate-400 dark:text-slate-500 font-medium">Nenhuma marca cadastrada.</td></tr>';
        return;
    }

    tbody.innerHTML = brandNames.map(name => {
        const brand = allBrands[name] || {};
        const profiles = BRAND_NETWORKS
            .filter(net => String(brand[net.key] || '').trim())
            .map(net => {
                const handle = String(brand[net.key]).trim().replace(/^@/, '');
                return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-[#1E1E22] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-[#323238] shadow-2xs mr-1.5 mb-1 shrink-0"><i class="fa-brands ${net.icon} text-xs"></i> <span class="text-xs text-slate-500 dark:text-slate-400 font-medium">${net.label}:</span> @${escapeHtml(handle)}</span>`;
            }).join('') || '<span class="text-xs text-slate-400 dark:text-slate-500 italic">Nenhum perfil vinculado</span>';
        const safeName = escapeHtml(name);
        return `
        <tr class="hover:bg-slate-50/50 dark:hover:bg-[#26262B]/40 transition-colors">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-slate-900 dark:text-slate-100">${safeName}</td>
            <td class="px-6 py-4 text-sm text-slate-500"><div class="flex flex-wrap gap-1 items-center">${profiles}</div></td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button type="button" data-brand="${safeName}" onclick="editBrand(this.dataset.brand)" class="p-1.5 rounded-lg text-[#1D4ED8] dark:text-[#60A5FA] hover:text-blue-700 hover:bg-[#1D4ED8]/10 dark:hover:bg-[#1D4ED8]/20 transition-colors" title="Editar marca">
                    <i class="fa-solid fa-pen text-sm"></i>
                </button>
                <button type="button" data-brand="${safeName}" onclick="deleteBrand(this.dataset.brand)" class="p-1.5 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors" title="Excluir marca">
                    <i class="fa-solid fa-trash-can text-sm"></i>
                </button>
            </td>
        </tr>`;
    }).join('');
}

function renderBrandSelects() {
    ['scrapeBrandSelect', 'schBrandSelect'].forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        select.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = Object.keys(allBrands).length ? 'Selecione uma marca...' : 'Nenhuma marca cadastrada (aba Marcas)';
        select.appendChild(placeholder);
        Object.keys(allBrands).forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        });
        if (current && allBrands[current]) select.value = current;
    });
}

function editBrand(name) {
    const brand = allBrands[name];
    if (!brand) return;
    document.getElementById('brandName').value = name;
    BRAND_NETWORKS.forEach(net => {
        const input = document.getElementById(net.input);
        if (input) input.value = String(brand[net.key] || '').replace(/^@/, '');
    });
    document.getElementById('brandForm')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('brandName')?.focus();
}
window.editBrand = editBrand;

function resetBrandForm() {
    document.getElementById('brandForm')?.reset();
}
window.resetBrandForm = resetBrandForm;

async function handleBrandSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('brandName').value.trim();
    if (!name) {
        showToast('Nome da marca é obrigatório', 'error');
        return;
    }
    const payload = { name };
    BRAND_NETWORKS.forEach(net => {
        payload[net.key] = (document.getElementById(net.input)?.value || '').trim().replace(/^@/, '');
    });
    if (!BRAND_NETWORKS.some(net => payload[net.key])) {
        showToast('Informe ao menos um perfil para a marca', 'error');
        return;
    }

    const btn = document.getElementById('btnSaveBrand');
    if (btn) btn.disabled = true;
    try {
        const response = await fetch(`${BASE_URL}/api/brands`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Erro ao salvar marca'));
        showToast('Marca salva com sucesso', 'success');
        resetBrandForm();
        await loadBrandsList();
    } catch (error) {
        console.error(error);
        showToast(error.message || 'Falha ao salvar marca', 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function deleteBrand(name) {
    if (!confirm(`Tem certeza que deseja excluir a marca "${name}"?`)) return;
    try {
        const response = await fetch(`${BASE_URL}/api/brands/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await readErrorDetail(response, 'Erro ao excluir marca'));
        showToast('Marca excluída com sucesso', 'success');
        await loadBrandsList();
    } catch (error) {
        console.error(error);
        showToast(error.message || 'Falha ao excluir marca', 'error');
    }
}
window.deleteBrand = deleteBrand;

// --- QUERY HISTORY ---
function loadHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;
    
    let history = [];
    try {
        history = JSON.parse(localStorage.getItem('raspQueryHistory') || '[]');
    } catch (e) {
        history = [];
    }
    if (history.length === 0) {
        historyList.innerHTML = '<li class="px-3 py-4 text-xs text-center text-gray-400">Nenhum histórico ainda.</li>';
        return;
    }
    
    historyList.innerHTML = '';
    history.forEach(item => {
        const queryText = typeof item === 'string' ? item : item.query;
        const limitVal = typeof item === 'object' && item.limit ? item.limit : null;
        const startDate = typeof item === 'object' && item.start_date ? item.start_date : null;
        const endDate = typeof item === 'object' && item.end_date ? item.end_date : null;
        const networks = typeof item === 'object' && item.networks ? item.networks : null;

        const li = document.createElement('li');
        li.className = 'px-3.5 py-3 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#26262B]/90 cursor-pointer flex flex-col gap-1 border-b border-slate-100 dark:border-[#323238]/80 last:border-0 transition-colors';
        
        function formatDateBR(dateStr) {
            if (!dateStr) return '';
            const s = String(dateStr).trim();
            if (s.includes('-')) {
                const parts = s.split('-');
                if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
            return s;
        }

        let metaParts = [];
        if (limitVal) metaParts.push(`${limitVal} posts`);
        const startDisp = formatDateBR(startDate);
        const endDisp = formatDateBR(endDate);
        if (startDisp || endDisp) metaParts.push(`${startDisp || 'Início'} até ${endDisp || 'Hoje'}`);
        const detailsBadge = metaParts.length > 0 ? `<div class="text-[10px] text-slate-400 dark:text-slate-400 font-sans">${escapeHtml(metaParts.join(' • '))}</div>` : '';

        li.innerHTML = `
            <div class="flex items-center justify-between group">
                <span class="truncate flex-1 font-mono font-bold text-slate-800 dark:text-slate-100 group-hover:text-[#1D4ED8] dark:group-hover:text-[#60A5FA] transition-colors" title="${escapeHtml(queryText)}">${escapeHtml(queryText)}</span>
                <i class="fa-solid fa-arrow-turn-down text-slate-300 dark:text-slate-600 group-hover:text-[#1D4ED8] dark:group-hover:text-[#60A5FA] ml-2 transition-colors"></i>
            </div>
            ${detailsBadge}
        `;
        li.onclick = () => {
            const editor = document.getElementById('keywordEditor');
            editor.innerText = queryText;
            highlightBooleanSyntax(editor);

            if (limitVal) {
                const limitInput = document.getElementById('limit');
                const limitLabel = document.getElementById('limitValue');
                if (limitInput) limitInput.value = limitVal;
                if (limitLabel) limitLabel.textContent = (parseInt(limitVal) >= 1000 ? '1.000+ (Sem Limite)' : limitVal);
            }

            // Sincroniza e preenche visualmente o seletor de datas (Flatpickr) com a data real salva no histórico
            if (window.fpStart) {
                if (startDate && String(startDate).trim()) {
                    window.fpStart.setDate(String(startDate).trim(), true);
                } else {
                    window.fpStart.clear();
                }
            } else {
                const startEl = document.getElementById('startDate');
                if (startEl) startEl.value = startDate || '';
            }

            if (window.fpEnd) {
                if (endDate && String(endDate).trim()) {
                    window.fpEnd.setDate(String(endDate).trim(), true);
                } else {
                    window.fpEnd.clear();
                }
            } else {
                const endEl = document.getElementById('endDate');
                if (endEl) endEl.value = endDate || '';
            }

            // Abre o painel de período de datas caso haja datas configuradas para visualização imediata
            const dateDetails = document.getElementById('startDate')?.closest('details');
            if (dateDetails && (startDate || endDate)) {
                dateDetails.open = true;
            }

            updateClearDateButtonsVisibility();

            if (networks && Array.isArray(networks) && networks.length > 0) {
                document.querySelectorAll('input[name="network"]').forEach(cb => {
                    cb.checked = networks.includes(cb.value);
                });
            }
            toggleHistoryDropdown();
        };
        historyList.appendChild(li);
    });
}

function saveToHistory(query, limit, startDate, endDate, networks) {
    if (!query || query.trim() === '') return;
    let history = [];
    try {
        history = JSON.parse(localStorage.getItem('raspQueryHistory') || '[]');
    } catch (e) {
        history = [];
    }
    
    const entry = {
        query: query.trim(),
        limit: limit || 20,
        start_date: startDate || '',
        end_date: endDate || '',
        networks: networks || []
    };

    // Remove if query text already exists
    history = history.filter(item => (typeof item === 'string' ? item : item.query) !== entry.query);
    // Add to beginning
    history.unshift(entry);
    // Mantém as 10 buscas mais recentes
    history = history.slice(0, 10);
    try {
        localStorage.setItem('raspQueryHistory', JSON.stringify(history));
    } catch (e) {}
    loadHistory();
}

function clearHistory() {
    try {
        localStorage.removeItem('raspQueryHistory');
    } catch (e) {}
    loadHistory();
}

function toggleHistoryDropdown() {
    const dropdown = document.getElementById('historyDropdown');
    dropdown.classList.toggle('hidden');
    if (!dropdown.classList.contains('hidden')) {
        loadHistory();
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('historyDropdown');
    const button = dropdown?.previousElementSibling;
    if (dropdown && !dropdown.classList.contains('hidden') && !dropdown.contains(e.target) && e.target !== button && !button.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});
