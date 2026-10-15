# -*- coding: utf-8 -*-

app_js_path = r"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\frontend\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update tr creation in renderStudioWordsTable
old_tr = """        const tr = document.createElement('tr');
        tr.className = item.enabled ? 'hover:bg-slate-50/80 dark:hover:bg-[#26262B]' : 'opacity-40 hover:bg-slate-50/80 dark:hover:bg-[#26262B]';"""

new_tr = """        const tr = document.createElement('tr');
        tr.setAttribute('data-word-text', item.text);
        tr.setAttribute('data-word-enabled', item.enabled ? 'true' : 'false');
        tr.className = item.enabled ? 'hover:bg-slate-50/80 dark:hover:bg-[#26262B]' : 'opacity-40 hover:bg-slate-50/80 dark:hover:bg-[#26262B]';"""

assert old_tr in content, "old_tr not found"
content = content.replace(old_tr, new_tr, 1)

# 2. Update status cell class
old_cell = """            <td class="py-1 px-2 text-center align-middle">
                ${statusHtml}
            </td>"""

new_cell = """            <td class="studio-word-status-cell py-1 px-2 text-center align-middle">
                ${statusHtml}
            </td>"""

assert old_cell in content, "old_cell not found"
content = content.replace(old_cell, new_cell, 1)

# 3. Add updateStudioWordStatusBadges function right above renderStudioPreview
target_prev = "function renderStudioPreview() {"
badges_fn = """function updateStudioWordStatusBadges() {
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

"""
assert target_prev in content, "renderStudioPreview not found"
content = content.replace(target_prev, badges_fn + target_prev, 1)

# 4. Call updateStudioWordStatusBadges in renderStudioPreview
old_boxes = "studioLastRenderedBoxes = result.hitboxes || [];"
new_boxes = """studioLastRenderedBoxes = result.hitboxes || [];
    updateStudioWordStatusBadges();"""
assert old_boxes in content, "old_boxes not found"
content = content.replace(old_boxes, new_boxes, 1)

# 5. In openWordCloudStudio, render preview before or together with table
old_open_seq = """    clearStudioWordSearch();
    resetStudioCanvasPanAndZoom();
    syncStudioControlsFromState();
    renderStudioWordsTable();

    const modal = document.getElementById('wordCloudStudioModal');
    if (modal) modal.classList.remove('hidden');

    setupStudioInteractivity();

    setTimeout(() => {
        renderStudioPreview();
    }, 60);"""

new_open_seq = """    clearStudioWordSearch();
    resetStudioCanvasPanAndZoom();
    syncStudioControlsFromState();

    const modal = document.getElementById('wordCloudStudioModal');
    if (modal) modal.classList.remove('hidden');

    setupStudioInteractivity();
    renderStudioPreview();
    renderStudioWordsTable();

    setTimeout(() => {
        renderStudioPreview();
    }, 60);"""
assert old_open_seq in content, "old_open_seq not found"
content = content.replace(old_open_seq, new_open_seq, 1)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)

print("patch_status_badges completed successfully!")
