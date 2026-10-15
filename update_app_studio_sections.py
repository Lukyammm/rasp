# -*- coding: utf-8 -*-
import os

app_js_path = r"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\frontend\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, l in enumerate(lines):
    if l.strip().startswith("function openWordCloudStudio()"):
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if lines[i].strip() == "window.exportStudioCanvasAtScale = exportStudioCanvasAtScale;":
        end_idx = i + 1
        break

print(f"Replacing lines {start_idx+1} to {end_idx}")

new_code = '''function openWordCloudStudio() {
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
    renderStudioWordsTable();

    const modal = document.getElementById('wordCloudStudioModal');
    if (modal) modal.classList.remove('hidden');

    setupStudioInteractivity();

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
            <td class="py-1 px-2 text-center align-middle">
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
    const rawLines = raw.split(/\\r?\\n/).map(l => l.trim()).filter(Boolean);

    if (rawLines.length === 1 && rawLines[0].includes(',') && !rawLines[0].match(/,\\s*\\d+/)) {
        const words = rawLines[0].split(',').map(w => w.trim()).filter(Boolean);
        words.forEach(w => parsed.push({ text: w, weight: 20, enabled: true }));
    } else {
        rawLines.forEach(rawLine => {
            let line = rawLine.replace(/^[•\\-\\s*]+/, '').trim();
            if (!line) return;
            if (/^(posi[cç][aã]o|rank|#|termo|palavra|word|termo\\t|palavra\\t)/i.test(line)) return;

            // TSV
            if (line.includes('\\t')) {
                const parts = line.split('\\t').map(p => p.trim()).filter(Boolean);
                if (parts.length >= 2) {
                    if (/^\\d+$/.test(parts[0]) && parts.length >= 3 && !/^\\d+$/.test(parts[1])) {
                        const word = parts[1].replace(/^[•\\-\\s*]+/, '');
                        const weight = parseInt(parts[2].replace(/[^\\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight), enabled: true });
                        return;
                    }
                    if (!/^\\d+$/.test(parts[0])) {
                        const word = parts[0].replace(/^[•\\-\\s*]+/, '');
                        const weight = parseInt(parts[1].replace(/[^\\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight), enabled: true });
                        return;
                    }
                }
            }

            // CSV
            if (line.includes(',')) {
                const csvParts = line.split(',').map(p => p.trim()).filter(Boolean);
                if (csvParts.length === 2 && /^\\d+$/.test(csvParts[1])) {
                    parsed.push({ text: csvParts[0], weight: Math.max(1, parseInt(csvParts[1], 10)), enabled: true });
                    return;
                }
                if (csvParts.length >= 3 && /^\\d+$/.test(csvParts[0]) && /^\\d+$/.test(csvParts[2])) {
                    parsed.push({ text: csvParts[1], weight: Math.max(1, parseInt(csvParts[2], 10)), enabled: true });
                    return;
                }
            }

            // Ponto-e-vírgula
            if (line.includes(';')) {
                const scParts = line.split(';').map(p => p.trim()).filter(Boolean);
                if (scParts.length >= 2 && /^\\d+$/.test(scParts[1])) {
                    parsed.push({ text: scParts[0], weight: Math.max(1, parseInt(scParts[1], 10)), enabled: true });
                    return;
                }
            }

            // Termo com peso (dois-pontos, igual ou espaço)
            const match = line.match(/^(.+?)(?:\\s*[:=]\\s*|\\s+)(\\d+)(?:\\s*%)?$/);
            if (match) {
                const text = match[1].replace(/^["']|["']$/g, '').trim();
                const weight = Math.max(1, parseInt(match[2], 10));
                parsed.push({ text, weight, enabled: true });
                return;
            }

            // Parênteses
            const parenMatch = line.match(/^(.+?)\\s*\\(\\s*(\\d+)\\s*\\)$/);
            if (parenMatch) {
                parsed.push({ text: parenMatch[1].trim(), weight: Math.max(1, parseInt(parenMatch[2], 10)), enabled: true });
                return;
            }

            // Termo isolado
            const cleaned = line.replace(/^[•\\-\\s*\\d+\\.]+/, '').trim();
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
            btn.className = 'studio-angle-btn p-2 rounded border text-left border-[#1D4ED8] bg-[#1D4ED8]/10 text-[#1D4ED8] dark:text-[#60A5FA]';
        } else {
            btn.className = 'studio-angle-btn p-2 rounded border text-left border-[#E4DFD6] dark:border-[#323238] text-slate-700 dark:text-[#F4F4F6]';
        }
    });
}

function setStudioPalette(paletteName) {
    wordCloudStudioState.paletteName = paletteName;
    updateStudioPaletteUI();
    renderStudioPreview();
}
window.setStudioPalette = setStudioPalette;

function updateStudioPaletteUI() {
    document.querySelectorAll('.studio-palette-card').forEach(card => {
        if (card.getAttribute('data-palette') === wordCloudStudioState.paletteName) {
            card.className = 'studio-palette-card w-full p-2.5 rounded-md border text-left transition-all border-[#1D4ED8] bg-[#1D4ED8]/5 flex items-center justify-between';
        } else {
            card.className = 'studio-palette-card w-full p-2.5 rounded-md border text-left transition-all border-[#E4DFD6] dark:border-[#323238] flex items-center justify-between';
        }
    });
}

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
        offCtx.font = '700 32px "Plus Jakarta Sans", system-ui, sans-serif';
        offCtx.textAlign = 'left';
        offCtx.fillText('RASP ANALYTICS • SOCIAL LISTENING', 40, 95);

        offCtx.fillStyle = '#64748B';
        offCtx.font = '400 20px "Plus Jakarta Sans", system-ui, sans-serif';
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
        offCtx.fillText(`Processamento 100% Local • Zero Token IA • EBM Quintto`, 40, cardH - 45);

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

    let tsv = 'Posição\\tTermo\\tFrequência\\tParticipação\\n';
    sorted.forEach((w, i) => {
        const pct = totalWeight ? ((w.weight / totalWeight) * 100).toFixed(1) + '%' : '0%';
        tsv += `${i + 1}\\t${w.text}\\t${w.weight}\\t${pct}\\n`;
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
'''

lines[start_idx:end_idx] = [new_code + "\n"]

with open(app_js_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Update completed successfully!")
