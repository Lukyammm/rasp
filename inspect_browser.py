import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://127.0.0.1:8000')
        await page.wait_for_timeout(1000)
        await page.evaluate('openWordCloudStudio()')
        await page.wait_for_timeout(400)
        await page.evaluate('applyStudioPreset("awards_star")')
        await page.wait_for_timeout(500)
        res = await page.evaluate('''() => {
            const boxes = studioLastRenderedBoxes.map(b => b.text);
            const total = wordCloudStudioState.words.filter(w => w.enabled).length;
            const state = JSON.stringify(wordCloudStudioState);
            return { placedTexts: boxes, count: boxes.length, total: total, state: state };
        }''')
        print('Placed texts in browser:', res['placedTexts'])
        print('Count:', res['count'])
        await browser.close()

asyncio.run(inspect())
