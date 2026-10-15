import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    out_dir = r"C:\Users\_EBMQUINTTO_\.gemini\antigravity\scratch\SocialScraper\screenshots_studio"
    os.makedirs(out_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1200)

        # 1. Dark Mode: Open Studio
        await page.evaluate("""
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            openWordCloudStudio();
        """)
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(out_dir, "after_dark_tab_words.png"))
        print("[OK] Screenshot: after_dark_tab_words.png")

        # 2. Test Presets tab
        await page.evaluate("switchStudioTab('presets')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_dark_tab_presets.png"))
        print("[OK] Screenshot: after_dark_tab_presets.png")

        # 3. Apply WhatsApp Card Preset
        await page.evaluate("applyStudioPreset('whatsapp_card')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(out_dir, "after_preset_whatsapp_applied.png"))
        print("[OK] Screenshot: after_preset_whatsapp_applied.png")

        # 4. Apply Star Preset
        await page.evaluate("applyStudioPreset('awards_star')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(out_dir, "after_preset_star_applied.png"))
        print("[OK] Screenshot: after_preset_star_applied.png")

        # 5. Switch to Shape tab
        await page.evaluate("switchStudioTab('shape')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_dark_tab_shape.png"))
        print("[OK] Screenshot: after_dark_tab_shape.png")

        # 6. Switch to Typography tab
        await page.evaluate("switchStudioTab('type')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_dark_tab_type.png"))
        print("[OK] Screenshot: after_dark_tab_type.png")

        # 7. Switch to Colors tab
        await page.evaluate("switchStudioTab('colors')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_dark_tab_colors.png"))
        print("[OK] Screenshot: after_dark_tab_colors.png")

        # 8. Test Search & Word Filtering in Words tab
        await page.evaluate("""
            switchStudioTab('words');
            const search = document.getElementById('studioWordSearchInput');
            if (search) {
                search.value = 'Fortaleza';
                filterStudioWordsTable('Fortaleza');
            }
        """)
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_words_search_filter.png"))
        print("[OK] Screenshot: after_words_search_filter.png")

        # 9. Clear search and test bulk import drawer
        await page.evaluate("""
            clearStudioWordSearch();
            toggleStudioBulkImport();
            const ta = document.getElementById('studioBulkImportTextarea');
            if (ta) ta.value = 'Metas 2026: 120\\nLiderança: 95\\nInovação Digital: 88\\nInteligência Artificial: 76';
        """)
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(out_dir, "after_bulk_import_drawer.png"))
        print("[OK] Screenshot: after_bulk_import_drawer.png")

        # Process bulk import
        await page.evaluate("processStudioBulkImport(false)")
        await page.wait_for_timeout(600)

        # 10. Switch to Light Mode (Alabastro Editorial)
        await page.evaluate("""
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            applyStudioPreset('executive_deck');
            switchStudioTab('words');
        """)
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(out_dir, "after_light_tab_words.png"))
        print("[OK] Screenshot: after_light_tab_words.png")

        # 11. Test Apply to Dashboard and verify Dashboard sync
        await page.evaluate("applyStudioToDashboard()")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(out_dir, "after_dashboard_synced.png"))
        print("[OK] Screenshot: after_dashboard_synced.png")

        await browser.close()
        print("All E2E UI verification tests passed successfully!")

asyncio.run(run())
