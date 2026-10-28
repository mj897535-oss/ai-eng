"""Automated Playwright captures for Phase P10 AI Tutor & Hint Ladder (Signature Feature C).

Captures:
1. tutor_desktop_conversation.png - Desktop view (1280x850) showing Hint Ladder L1 hint card, self-correction, and transfer check.
2. tutor_360_conversation.png - Mobile 360px viewport responsive conversation view.
3. tutor_desktop_gated.png - Blinded window / locked tutoring gating screen when pre-test is unverified.
4. tutor_desktop_session_complete.png - End-of-session summary card with duration, turns, and self-correction metrics.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = Path(r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0")
BASE_URL = "http://localhost:3000"

USER_PARTICIPANT = {
    "id": "u3333333-3333-3333-3333-333333333333",
    "email": "learner@syntaxlens.edu",
    "full_name": "Aarav Sharma",
    "role": "participant",
    "is_active": True,
    "must_change_password": False,
}

STATUS_ELIGIBLE = {
    "can_start_tutoring": True,
    "is_pretest_verified": True,
    "priority_categories": ["SVA", "TNS"],
    "saved_interests": "Technology and College Life",
    "gating_message": None,
    "study_group": "intervention",
}

STATUS_LOCKED = {
    "can_start_tutoring": False,
    "is_pretest_verified": False,
    "priority_categories": [],
    "saved_interests": "Daily Life",
    "gating_message": "Tutoring is locked until your baseline pre-test assessment has been reviewed and verified.",
    "study_group": "intervention",
}


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("Checking / starting Next.js development server...")
    web_proc = subprocess.Popen(
        "npm --prefix apps/web run dev -- -p 3000",
        shell=True,
    )

    import urllib.request
    server_ready = False
    for _ in range(20):
        try:
            req = urllib.request.Request(BASE_URL)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 307, 308):
                    server_ready = True
                    break
        except Exception:
            time.sleep(1)

    if not server_ready:
        print("Waiting extra 3 seconds for server...")
        time.sleep(3)

    print("Next.js server is ready! Launching Microsoft Edge in headless mode...")
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)

        # ----------------------------------------------------
        # 1. Desktop Conversation View
        # ----------------------------------------------------
        context_desktop = await browser.new_context(viewport={"width": 1280, "height": 900})
        page_desktop = await context_desktop.new_page()

        async def handle_eligible_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_PARTICIPANT))
            elif "/tutor/status" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(STATUS_ELIGIBLE))
            elif "/tutor/sessions" in url and "turns" not in url and "end" not in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "session_id": "sess-live-1",
                        "status": "active",
                        "topic": "Technology and College Life",
                        "target_categories": ["SVA", "TNS"],
                        "tutor_opening_message": "Hello! Today we'll chat naturally about college life and technology. To get started, tell me: what does a typical day look like for your friend or colleague?",
                        "prompt_version": "v1.0-tutor-ladder",
                    }),
                )
            elif "/turns" in url:
                data = json.loads(route.request.post_data or "{}")
                utt = data.get("utterance", "")
                if "goes" in utt.lower():
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({
                            "reply_text": 'Spot on! "He goes to college every day" is completely accurate. Notice how the verb smoothly agrees with "He". Now for a transfer check: what does someone else in your office or family do every morning?',
                            "target_category": "SVA",
                            "hint_level": 1,
                            "is_self_correction": True,
                            "attempt_type": "hint_assisted",
                            "expects_attempt": True,
                            "transfer_prompt": "What does someone else in your office or family do every morning?",
                        }),
                    )
                else:
                    await route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({
                            "reply_text": 'Notice the subject and the verb in: "He go to college every day". When the subject is third-person singular (he/she/it), what ending does the verb usually take in the present tense?',
                            "target_category": "SVA",
                            "hint_level": 1,
                            "learner_phrase_quoted": "He go to college every day",
                            "is_self_correction": False,
                            "attempt_type": "hint_assisted",
                            "expects_attempt": True,
                            "transfer_prompt": None,
                        }),
                    )
            elif "/end" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "session_id": "sess-live-1",
                        "status": "completed",
                        "active_duration_seconds": 185,
                        "turns_count": 3,
                        "total_attempts": 2,
                        "independent_self_corrections": 0,
                        "hint_assisted_corrections": 1,
                        "prompt_version": "v1.0-tutor-ladder",
                    }),
                )
            else:
                await route.continue_()

        await page_desktop.route("**/api/v1/**", handle_eligible_routes)

        print("Navigating to Tutor page (Desktop)...")
        await page_desktop.goto(f"{BASE_URL}/tutor", wait_until="networkidle")
        await page_desktop.wait_for_timeout(800)

        # Start session
        start_btn = page_desktop.locator("button:has-text('Begin Practice Session')")
        if await start_btn.count() > 0:
            await start_btn.click()
            await page_desktop.wait_for_timeout(800)

        # Learner turn 1: Erroneous utterance (Appendix A)
        input_box = page_desktop.locator("input[placeholder*='Type or speak']")
        await input_box.fill("He go to college every day by bus.")
        await page_desktop.keyboard.press("Enter")
        await page_desktop.wait_for_timeout(1000)

        # Learner turn 2: Hint-assisted self-correction
        await input_box.fill("He goes to college every day by bus.")
        await page_desktop.keyboard.press("Enter")
        await page_desktop.wait_for_timeout(1200)

        # 1. Capture Desktop Conversation Screenshot
        path1 = ARTIFACT_DIR / "tutor_desktop_conversation.png"
        await page_desktop.screenshot(path=str(path1))
        print(f"Captured: {path1}")

        # 2. Click Finish Practice to show Session Complete Card
        finish_btn = page_desktop.locator("button:has-text('Finish Practice')")
        if await finish_btn.count() > 0:
            await finish_btn.click()
            await page_desktop.wait_for_timeout(800)
            path2 = ARTIFACT_DIR / "tutor_desktop_session_complete.png"
            await page_desktop.screenshot(path=str(path2))
            print(f"Captured: {path2}")

        await page_desktop.close()
        await context_desktop.close()

        # ----------------------------------------------------
        # 3. Mobile 360px Viewport Screenshot
        # ----------------------------------------------------
        print("Capturing Mobile 360px conversation view...")
        context_mobile = await browser.new_context(viewport={"width": 360, "height": 740})
        page_mobile = await context_mobile.new_page()
        await page_mobile.route("**/api/v1/**", handle_eligible_routes)

        await page_mobile.goto(f"{BASE_URL}/tutor", wait_until="networkidle")
        await page_mobile.wait_for_timeout(800)

        start_btn_m = page_mobile.locator("button:has-text('Begin Practice Session')")
        if await start_btn_m.count() > 0:
            await start_btn_m.click()
            await page_mobile.wait_for_timeout(800)

        input_box_m = page_mobile.locator("input[placeholder*='Type or speak']")
        await input_box_m.fill("He go to college every day.")
        await page_mobile.keyboard.press("Enter")
        await page_mobile.wait_for_timeout(1000)

        path3 = ARTIFACT_DIR / "tutor_360_conversation.png"
        await page_mobile.screenshot(path=str(path3))
        print(f"Captured: {path3}")

        await page_mobile.close()
        await context_mobile.close()

        # ----------------------------------------------------
        # 4. Desktop Gated / Blinded Assessment Window Screenshot
        # ----------------------------------------------------
        print("Capturing Desktop Gated / Locked view...")
        context_locked = await browser.new_context(viewport={"width": 1280, "height": 850})
        page_locked = await context_locked.new_page()

        async def handle_locked_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_PARTICIPANT))
            elif "/tutor/status" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(STATUS_LOCKED))
            else:
                await route.continue_()

        await page_locked.route("**/api/v1/**", handle_locked_routes)
        await page_locked.goto(f"{BASE_URL}/tutor", wait_until="networkidle")
        await page_locked.wait_for_timeout(1000)

        path4 = ARTIFACT_DIR / "tutor_desktop_gated.png"
        await page_locked.screenshot(path=str(path4))
        print(f"Captured: {path4}")

        await page_locked.close()
        await context_locked.close()

        await browser.close()

    try:
        web_proc.terminate()
        web_proc.kill()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
