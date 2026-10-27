"""Automated screenshot capture for /design page using Playwright.

Captures:
1. Desktop Light Mode (1280x900)
2. Desktop Dark Mode (1280x900)
3. Mobile 360px viewport (360x840)
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = Path(r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0")
URL = "http://localhost:3000/design"


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # Start Next.js server in production mode
    print("Starting Next.js server...")
    proc = subprocess.Popen(
        "npm --prefix apps/web start",
        shell=True,
    )

    # Wait for server ready
    import urllib.request
    server_ready = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(URL, timeout=2) as resp:
                if resp.status == 200:
                    server_ready = True
                    break
        except Exception:
            time.sleep(1)

    if not server_ready:
        print("Server could not start in time.")
        proc.kill()
        return

    print("Server ready! Launching native Chromium/Edge browser...")
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)

        # 1. Desktop Light Mode
        context_light = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context_light.new_page()
        await page.goto(URL, wait_until="networkidle")
        path_light = ARTIFACT_DIR / "design_light.png"
        await page.screenshot(path=str(path_light), full_page=True)
        print(f"Captured light mode screenshot to {path_light}")

        # 2. Desktop Dark Mode (click the theme toggle button)
        await page.click('button:has-text("Dark Mode")')
        await page.wait_for_timeout(500)
        path_dark = ARTIFACT_DIR / "design_dark.png"
        await page.screenshot(path=str(path_dark), full_page=True)
        print(f"Captured dark mode screenshot to {path_dark}")
        await context_light.close()

        # 3. Mobile Viewport (360px width)
        context_mobile = await browser.new_context(viewport={"width": 360, "height": 840})
        page_mobile = await context_mobile.new_page()
        await page_mobile.goto(URL, wait_until="networkidle")
        path_mobile = ARTIFACT_DIR / "design_mobile_360.png"
        await page_mobile.screenshot(path=str(path_mobile), full_page=True)
        print(f"Captured mobile 360px screenshot to {path_mobile}")
        await context_mobile.close()

        await browser.close()

    try:
        subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
    except Exception:
        proc.kill()
    print("Screenshot capture completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
