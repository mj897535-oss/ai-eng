"""Automated Playwright captures and video recording for Phase P9 Reviewer Cockpit (Signature Feature D).

Captures:
1. reviewer_cockpit_queue.png - Multi-criteria filtered review queue with workload counts.
2. reviewer_cockpit_main.png - Reviewer Cockpit main screen with waveform, context-linked transcript, side-by-side AI/Reviewer panel.
3. reviewer_cockpit_edit.png - Reviewer inline editing candidate attributes (span, category, correction).
4. reviewer_cockpit_shortcuts.png - Keyboard shortcuts cheat-sheet modal (? key).
5. reviewer_cockpit_agreement.png - Inter-rater agreement statistics & Cohen's Kappa modal.
6. reviewer_cockpit_keyboard_review.webm - Native screen-recording of keyboard-only review workflow (A/R/E/U/N).
"""

import asyncio
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = Path(r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0")
BASE_URL = "http://localhost:3000"

USER_REVIEWER = {
    "id": "u2222222-2222-2222-2222-222222222222",
    "email": "dr.vance@syntaxlens.edu",
    "full_name": "Dr. Eleanor Vance",
    "role": "reviewer",
    "is_active": True,
    "must_change_password": False,
}

COCKPIT_MOCK = {
    "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
    "participant_code": "SL-2026-0004",
    "study_group": "ai_intervention",
    "assessment_type": "pre_test",
    "review_status": "unreviewed",
    "is_verified": False,
    "transcript": "He go to college every day by bus, but yesterday he walk because the bus was late.",
    "word_count": 17,
    "audio_key": "audio/pre-test-0004.webm",
    "audio_url": "https://example.com/audio/sample.webm",
    "rubric_version": "v1.0-jam-phd",
    "model_version": "gemini-1.5-pro",
    "effective_annotations": [
        {
            "annotation_id": "ann-sva-1",
            "start_char": 3,
            "end_char": 5,
            "start_time_ms": 650,
            "end_time_ms": 1100,
            "span_text": "go",
            "category_code": "SVA",
            "suggested_correction": "goes",
            "explanation": "Subject 'He' requires third-person singular verb 'goes' in simple present habit.",
            "confidence": 0.96,
            "origin": "ai",
            "review_status": "unreviewed",
            "decision_id": None,
            "reason": None,
            "is_active_for_metrics": True,
            "flag": "candidate_error",
        },
        {
            "annotation_id": "ann-tns-2",
            "start_char": 55,
            "end_char": 59,
            "start_time_ms": 4500,
            "end_time_ms": 5000,
            "span_text": "walk",
            "category_code": "TNS",
            "suggested_correction": "walked",
            "explanation": "Past temporal marker 'yesterday' requires simple past 'walked'.",
            "confidence": 0.94,
            "origin": "ai",
            "review_status": "unreviewed",
            "decision_id": None,
            "reason": None,
            "is_active_for_metrics": True,
            "flag": "candidate_error",
        },
    ],
}


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    video_temp_dir = ARTIFACT_DIR / "video_temp"
    video_temp_dir.mkdir(parents=True, exist_ok=True)

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

    print("Next.js server is ready! Launching Microsoft Edge in headless mode with video recording...")
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)

        context = await browser.new_context(
            viewport={"width": 1280, "height": 920},
            record_video_dir=str(video_temp_dir),
            record_video_size={"width": 1280, "height": 920},
        )
        page = await context.new_page()

        # Intercept and mock API routes
        async def handle_route(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(USER_REVIEWER),
                )
            elif "/reviews/cockpit/a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a/decisions" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"status": "recorded", "decision_id": "d-12345"}),
                )
            elif "/reviews/cockpit/a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(COCKPIT_MOCK),
                )
            else:
                await route.continue_()

        await page.route("**/api/v1/**", handle_route)

        # 1. Review Queue Page
        print("Capturing 1: reviewer_cockpit_queue.png...")
        await page.goto(f"{BASE_URL}/admin/review-queue", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        path1 = ARTIFACT_DIR / "reviewer_cockpit_queue.png"
        await page.screenshot(path=str(path1))
        print(f"Captured: {path1}")

        # 2. Inter-Rater Agreement & Kappa Stats Modal
        print("Capturing 2: reviewer_cockpit_agreement.png...")
        agreement_btn = page.locator("button:has-text('Agreement & Kappa Stats')")
        if await agreement_btn.count() > 0:
            await agreement_btn.click()
            await page.wait_for_timeout(500)
            path2 = ARTIFACT_DIR / "reviewer_cockpit_agreement.png"
            await page.screenshot(path=str(path2))
            print(f"Captured: {path2}")
            # Close dialog
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)

        # 3. Main Reviewer Cockpit Screen
        print("Capturing 3: reviewer_cockpit_main.png...")
        await page.goto(f"{BASE_URL}/reviewer/cockpit/a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        path3 = ARTIFACT_DIR / "reviewer_cockpit_main.png"
        await page.screenshot(path=str(path3))
        print(f"Captured: {path3}")

        # 4. Keyboard Shortcuts Cheat-Sheet Modal (? key)
        print("Capturing 4: reviewer_cockpit_shortcuts.png...")
        await page.keyboard.press("?")
        await page.wait_for_timeout(600)
        path4 = ARTIFACT_DIR / "reviewer_cockpit_shortcuts.png"
        await page.screenshot(path=str(path4))
        print(f"Captured: {path4}")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # 5. Inline Edit State (E key)
        print("Capturing 5: reviewer_cockpit_edit.png...")
        await page.keyboard.press("e")
        await page.wait_for_timeout(500)
        path5 = ARTIFACT_DIR / "reviewer_cockpit_edit.png"
        await page.screenshot(path=str(path5))
        print(f"Captured: {path5}")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # 6. Screen Recording of Keyboard-Only Workflow:
        # Step A: Press 'a' to Accept SVA candidate #1 (autosaves and advances to #2)
        print("Recording keyboard review action: Pressing 'a' (Accept)...")
        await page.keyboard.press("a")
        await page.wait_for_timeout(1500)

        # Step B: On candidate #2 (TNS: "walk"), press 'u' to mark Uncertain
        print("Recording keyboard review action: Pressing 'u' (Uncertain)...")
        await page.keyboard.press("u")
        await page.wait_for_timeout(1500)

        # Step C: Press 'n' to open Add Missed Error dialog
        print("Recording keyboard review action: Pressing 'n' (Add Missed)...")
        await page.keyboard.press("n")
        await page.wait_for_timeout(1200)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

        # Close page to ensure video is finalized
        video = page.video
        await page.close()
        await context.close()
        await browser.close()

        if video:
            video_path = await video.path()
            target_video = ARTIFACT_DIR / "reviewer_cockpit_keyboard_review.webm"
            shutil.copy(video_path, str(target_video))
            print(f"Screen recording saved: {target_video}")

    try:
        shutil.rmtree(video_temp_dir)
        web_proc.terminate()
        web_proc.kill()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
