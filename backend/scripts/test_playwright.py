import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://apps.apple.com/in/app/id1044431526?see-all=reviews", wait_until="domcontentloaded")
        html = await page.content()
        with open("apple_dump.html", "w") as f:
            f.write(html)
        print("Dumped HTML.")
        await browser.close()

asyncio.run(main())
