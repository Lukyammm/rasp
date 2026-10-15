import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        errors = []
        warnings = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else (warnings.append(m.text) if m.type == 'warning' else None))

        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1000)

        # Exercise tabs
        for tab in ['tab-extract', 'tab-direct-link', 'tab-dashboard', 'tab-schedule', 'tab-brands']:
            await page.evaluate(f"switchTab('{tab}')")
            await page.wait_for_timeout(300)

        # Open and close modals
        await page.evaluate("openWordCloudStudio()")
        await page.wait_for_timeout(500)
        await page.evaluate("closeWordCloudStudio()")
        await page.wait_for_timeout(300)

        await page.evaluate("document.getElementById('accountsModal').classList.remove('hidden')")
        await page.wait_for_timeout(300)
        await page.evaluate("document.getElementById('accountsModal').classList.add('hidden')")
        await page.wait_for_timeout(300)

        await page.evaluate("document.getElementById('booleanHelpModal').classList.remove('hidden')")
        await page.wait_for_timeout(300)
        await page.evaluate("document.getElementById('booleanHelpModal').classList.add('hidden')")
        await page.wait_for_timeout(300)

        await browser.close()
        print('Browser errors count:', len(errors))
        if errors:
            print('Errors:', errors)
        print('Browser warnings count:', len(warnings))
        if warnings:
            print('Warnings:', warnings[:5])

asyncio.run(run())
