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
        await page.wait_for_timeout(1000)

        # 1. Dark mode - Open studio
        await page.evaluate("""
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            openWordCloudStudio();
        """)
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(out_dir, "before_dark_tab_words.png"))

        # Switch to Shape tab
        await page.evaluate("switchStudioTab('shape')")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(out_dir, "before_dark_tab_shape.png"))

        # Switch to Type tab
        await page.evaluate("switchStudioTab('type')")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(out_dir, "before_dark_tab_type.png"))

        # Switch to Colors tab
        await page.evaluate("switchStudioTab('colors')")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(out_dir, "before_dark_tab_colors.png"))

        # 2. Light mode
        await page.evaluate("""
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            switchStudioTab('words');
        """)
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(out_dir, "before_light_tab_words.png"))

        await browser.close()
        print("Captured before screenshots successfully!")

asyncio.run(run())
