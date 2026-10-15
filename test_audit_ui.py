import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1000)

        # Force dark mode
        await page.evaluate("""
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        """)
        await page.wait_for_timeout(500)

        # Measure background color of body
        body_bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
        print('Dark Body Background:', body_bg)

        # Measure background color of cards
        card_bg = await page.evaluate("""
            const card = document.querySelector('.bg-white');
            card ? getComputedStyle(card).backgroundColor : 'N/A'
        """)
        print('Dark Card Background:', card_bg)

        # Screenshot dark main
        await page.screenshot(path=r'C:\Users\_EBMQUINTTO_\.gemini\antigravity\brain\c153c55f-dedd-4755-9398-9626550acc69\audit\antigravity_dark_main.png')

        # Open Studio Modal
        await page.evaluate("openWordCloudStudio()")
        await page.wait_for_timeout(800)
        await page.screenshot(path=r'C:\Users\_EBMQUINTTO_\.gemini\antigravity\brain\c153c55f-dedd-4755-9398-9626550acc69\audit\antigravity_dark_studio.png')

        # Close Studio Modal
        await page.evaluate("closeWordCloudStudio()")
        await page.wait_for_timeout(300)

        # Switch to dashboard tab
        await page.evaluate("""
            if (typeof switchTab === 'function') switchTab('tab-dashboard');
        """)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=r'C:\Users\_EBMQUINTTO_\.gemini\antigravity\brain\c153c55f-dedd-4755-9398-9626550acc69\audit\antigravity_dark_dashboard.png')

        # Switch to light mode
        await page.evaluate("""
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        """)
        await page.wait_for_timeout(500)
        light_bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
        print('Light Body Background:', light_bg)

        # Back to extract tab
        await page.evaluate("""
            if (typeof switchTab === 'function') switchTab('tab-extract');
        """)
        await page.wait_for_timeout(500)
        await page.screenshot(path=r'C:\Users\_EBMQUINTTO_\.gemini\antigravity\brain\c153c55f-dedd-4755-9398-9626550acc69\audit\antigravity_light_main.png')

        await browser.close()
        print('Audit screenshots updated successfully!')

asyncio.run(run())
