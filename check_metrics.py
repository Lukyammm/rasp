import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1000)
        await page.evaluate('openWordCloudStudio()')
        await page.wait_for_timeout(500)
        
        t1 = await page.evaluate("document.getElementById('studioPlacedWordsBadge').innerText")
        top1 = await page.evaluate("document.getElementById('studioTopWordBadge').innerText")
        
        await page.evaluate("applyStudioPreset('awards_star')")
        await page.wait_for_timeout(500)
        t_star = await page.evaluate("document.getElementById('studioPlacedWordsBadge').innerText")
        
        await page.evaluate("applyStudioPreset('whatsapp_card')")
        await page.wait_for_timeout(500)
        t_wa = await page.evaluate("document.getElementById('studioPlacedWordsBadge').innerText")
        
        print(f"Default: {t1} | Top: {top1}")
        print(f"Star Preset: {t_star}")
        print(f"WhatsApp Preset: {t_wa}")
        await browser.close()

asyncio.run(check())
