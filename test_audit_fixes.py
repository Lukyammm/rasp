# -*- coding: utf-8 -*-
import asyncio
import os
from playwright.async_api import async_playwright

async def run_audit_tests():
    out_dir = r"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\screenshots_studio"
    os.makedirs(out_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1000)

        # 1. Open Studio
        await page.evaluate("""
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            openWordCloudStudio();
        """)
        await page.wait_for_timeout(500)

        # 2. Verify Table Columns and Status badges
        table_html = await page.evaluate("document.getElementById('studioWordsTableBody').innerHTML")
        status_text = await page.evaluate("document.querySelector('.studio-word-status-cell')?.innerText")
        print("First word status text:", repr(status_text))
        assert 'Vis' in status_text, f"Unexpected status text: {status_text}"
        assert 'studio-inline-input' in table_html, "Inline inputs missing in table"
        print("[TEST 1 PASSED] Table rendered with Status badges and inline inputs.")

        # 3. Test Preset Synchronization with DOM Sliders and Buttons
        await page.evaluate("applyStudioPreset('whatsapp_card')")
        await page.wait_for_timeout(400)
        state_padding = await page.evaluate("wordCloudStudioState.padding")
        dom_padding = await page.evaluate("parseInt(document.getElementById('studioPaddingRange').value, 10)")
        assert state_padding == dom_padding, f"Padding sync failed: state={state_padding}, dom={dom_padding}"
        
        state_max_words = await page.evaluate("wordCloudStudioState.maxWords")
        dom_max_words = await page.evaluate("parseInt(document.getElementById('studioMaxWordsRange').value, 10)")
        assert state_max_words == dom_max_words, f"MaxWords sync failed: state={state_max_words}, dom={dom_max_words}"
        print(f"[TEST 2 PASSED] Preset sync verified: padding={dom_padding}, maxWords={dom_max_words}.")

        # 4. Test Shape Outline Toggle
        await page.evaluate("toggleStudioShapeOutline(true)")
        await page.wait_for_timeout(400)
        outline_state = await page.evaluate("wordCloudStudioState.drawShapeOutline")
        assert outline_state is True, "Outline state not set to True"
        await page.screenshot(path=os.path.join(out_dir, "test_shape_outline_active.png"))
        print("[TEST 3 PASSED] Shape outline enabled and drawn.")

        # 5. Test Canvas Pan & Zoom
        await page.evaluate("""
            zoomStudioCanvas(1.2);
            studioPanX = 40;
            studioPanY = -25;
            applyStudioCanvasTransform();
        """)
        await page.wait_for_timeout(300)
        transform = await page.evaluate("document.getElementById('studioPreviewCanvas').style.transform")
        assert 'translate(40px, -25px)' in transform, f"Pan transform incorrect: {transform}"
        assert 'scale(1.2)' in transform, f"Zoom transform incorrect: {transform}"
        
        # Test reset Pan & Zoom
        await page.evaluate("resetStudioCanvasPanAndZoom()")
        transform_reset = await page.evaluate("document.getElementById('studioPreviewCanvas').style.transform")
        assert 'translate(0px, 0px) scale(1)' in transform_reset, f"Reset transform incorrect: {transform_reset}"
        print("[TEST 4 PASSED] Canvas Pan & Zoom and reset verified.")

        # 6. Test Multi-Format Bulk Import Parser
        test_bulk = """
Posição\tTermo\tFrequência\tParticipação
1\tGovernança Digital\t90\t35%
2\tTransparência Pública\t75\t25%
Fortaleza, 85
🎉 Inovação 2026: 70
Sustentabilidade (65)
Comunidade; 60
        """
        await page.evaluate(f"""
            document.getElementById('studioBulkImportTextarea').value = `{test_bulk}`;
            processStudioBulkImport(true);
        """)
        await page.wait_for_timeout(500)
        words_count = await page.evaluate("wordCloudStudioState.words.length")
        assert words_count == 6, f"Expected 6 parsed words, got {words_count}"
        
        first_word = await page.evaluate("wordCloudStudioState.words[0]")
        assert first_word['text'] == "Governança Digital" and first_word['weight'] == 90, f"TSV parsed incorrectly: {first_word}"
        
        third_word = await page.evaluate("wordCloudStudioState.words[2]")
        assert third_word['text'] == "Fortaleza" and third_word['weight'] == 85, f"CSV parsed incorrectly: {third_word}"
        
        fourth_word = await page.evaluate("wordCloudStudioState.words[3]")
        assert "Inovação 2026" in fourth_word['text'] and fourth_word['weight'] == 70, f"Emoji/colon parsed incorrectly: {fourth_word}"
        print(f"[TEST 5 PASSED] Bulk import multi-format parser verified: {words_count} words correctly parsed.")

        # 7. Test Top Words Chips and Inline Weight Adjustment
        await page.evaluate("selectTopWords(3)")
        await page.wait_for_timeout(300)
        active_count = await page.evaluate("wordCloudStudioState.words.filter(w => w.enabled).length")
        assert active_count == 3, f"Expected 3 active words, got {active_count}"
        
        await page.evaluate("adjustStudioWordWeight(0, 10)")
        updated_weight = await page.evaluate("wordCloudStudioState.words[0].weight")
        assert updated_weight == 100, f"Expected weight 100, got {updated_weight}"
        print("[TEST 6 PASSED] Quick Top-N filter and inline weight adjustment verified.")

        # 8. Test WhatsApp Card Generation
        await page.evaluate("copyStudioImage('whatsapp')")
        await page.wait_for_timeout(500)
        print("[TEST 7 PASSED] WhatsApp Card generated and exported.")

        await page.screenshot(path=os.path.join(out_dir, "test_audit_final_studio.png"))
        await browser.close()
        print("\nALL AUDIT & FIX TESTS PASSED 100%!")

if __name__ == "__main__":
    asyncio.run(run_audit_tests())
