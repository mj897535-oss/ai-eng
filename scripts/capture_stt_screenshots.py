"""Automated Playwright captures for Phase P7 Speech-To-Text Pipeline & Pilot Kit.

Captures:
1. stt_pilot_telemetry_dashboard.png - Researcher Pilot Kit Telemetry dashboard (/admin/pilot).
2. stt_verbatim_transcript_inspector.png - Faithful verbatim transcript with acoustic word timestamps.
3. stt_human_revision_modal.png - Reviewer transcript revision modal with audit tracking.
4. participant_recording_transcribed.png - Participant view showing completed faithful transcript.
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

SAMPLE_METRICS = {
    "total_runs": 18,
    "total_audio_seconds": 940.5,
    "total_cost_usd": 0.0941,
    "average_latency_ms": 1420.5,
    "average_confidence": 0.965,
    "low_confidence_count": 3,
    "recent_jobs": [
        {
            "metric_id": "m1111111-1111-1111-1111-111111111111",
            "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
            "provider": "mock",
            "model_version": "mock-stt-v1.0",
            "audio_duration_seconds": 58.4,
            "latency_ms": 1240,
            "estimated_cost_usd": 0.0058,
            "word_count": 8,
            "average_confidence": 0.97,
            "low_confidence_count": 0,
            "retry_count": 0,
            "created_at": "2026-10-27T17:45:00Z",
        },
        {
            "metric_id": "m2222222-2222-2222-2222-222222222222",
            "assessment_id": "b1234567-89ab-4cde-f012-3456789abcde",
            "provider": "mock",
            "model_version": "mock-stt-v1.0",
            "audio_duration_seconds": 47.2,
            "latency_ms": 1180,
            "estimated_cost_usd": 0.0047,
            "word_count": 7,
            "average_confidence": 0.94,
            "low_confidence_count": 1,
            "retry_count": 0,
            "created_at": "2026-10-27T17:30:00Z",
        },
        {
            "metric_id": "m3333333-3333-3333-3333-333333333333",
            "assessment_id": "c9998888-7777-6666-5555-444433332222",
            "provider": "mock",
            "model_version": "mock-stt-v1.0",
            "audio_duration_seconds": 62.0,
            "latency_ms": 1560,
            "estimated_cost_usd": 0.0062,
            "word_count": 11,
            "average_confidence": 0.98,
            "low_confidence_count": 0,
            "retry_count": 0,
            "created_at": "2026-10-27T17:15:00Z",
        },
    ],
}

SAMPLE_TRANSCRIPT = {
    "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
    "status": "transcribed",
    "transcript": "He go to college every day by bus.",
    "word_count": 8,
    "stt_confidence": 0.97,
    "low_confidence_flag": False,
    "words": [
        {"word": "He", "start": 0.5, "end": 0.75, "confidence": 0.98},
        {"word": "go", "start": 0.87, "end": 1.12, "confidence": 0.97},
        {"word": "to", "start": 1.24, "end": 1.45, "confidence": 0.99},
        {"word": "college", "start": 1.57, "end": 2.15, "confidence": 0.96},
        {"word": "every", "start": 2.27, "end": 2.65, "confidence": 0.98},
        {"word": "day", "start": 2.77, "end": 3.05, "confidence": 0.99},
        {"word": "by", "start": 3.17, "end": 3.35, "confidence": 0.98},
        {"word": "bus.", "start": 3.47, "end": 3.85, "confidence": 0.97},
    ],
    "revisions": [
        {
            "revision_id": "rev-001",
            "revised_transcript": "He go to classes every day by bus.",
            "revised_word_count": 8,
            "reason": "Acoustic verification confirmed speaker said 'classes' rather than 'college'.",
            "diff_json": None,
            "created_at": "2026-10-27T17:50:00Z",
        }
    ],
    "retry_count": 0,
    "last_error": None,
}


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting Next.js development server...")
    web_proc = subprocess.Popen(
        "npm --prefix apps/web run dev -- -p 3000",
        shell=True,
    )

    import urllib.request
    server_ready = False
    for i in range(20):
        try:
            req = urllib.request.Request(f"{BASE_URL}")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 307, 308):
                    server_ready = True
                    break
        except urllib.error.HTTPError as he:
            if he.code in (200, 307, 308):
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

        context = await browser.new_context(
            viewport={"width": 1280, "height": 920},
        )
        page = await context.new_page()

        # Mock API routes for pilot telemetry and transcript
        async def handle_route(route):
            url = route.request.url
            if "/assessments/metrics/stt" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(SAMPLE_METRICS),
                )
            elif "/transcript" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(SAMPLE_TRANSCRIPT),
                )
            elif "/revisions" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"status": "created"}),
                )
            else:
                await route.continue_()

        await page.route("**/api/v1/**", handle_route)
        await page.route("**/assessments/**", handle_route)

        # 1. Capture Pilot Telemetry Dashboard
        print("Navigating to /admin/pilot...")
        await page.goto(f"{BASE_URL}/admin/pilot", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        path1 = ARTIFACT_DIR / "stt_pilot_telemetry_dashboard.png"
        await page.screenshot(path=str(path1), full_page=True)
        print(f"Captured: {path1}")

        # 2. Select first row to inspect verbatim transcript and acoustic word timestamps
        inspect_btn = page.locator("button:has-text('View')").first
        if await inspect_btn.count() > 0:
            await inspect_btn.click()
            await page.wait_for_timeout(1000)

        path2 = ARTIFACT_DIR / "stt_verbatim_transcript_inspector.png"
        await page.screenshot(path=str(path2), full_page=True)
        print(f"Captured: {path2}")

        # 3. Open Revision Modal
        rev_btn = page.locator("button:has-text('Add Human Transcript Revision')").first
        if await rev_btn.count() > 0:
            await rev_btn.click()
            await page.wait_for_timeout(800)

        path3 = ARTIFACT_DIR / "stt_human_revision_modal.png"
        await page.screenshot(path=str(path3))
        print(f"Captured: {path3}")

        # 4. Capture Participant Transcribed State on Pre-test screen
        print("Navigating to /assessment/pre...")
        # Mock participant assessment status to transcribed
        async def handle_pre_route(route):
            url = route.request.url
            if "/presigned-url" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "upload_url": "http://testserver/mock-upload",
                        "storage_key": "audio/SL-2026-0001/pre_001.webm",
                        "method": "PUT",
                        "headers": {"Content-Type": "audio/webm"},
                        "expires_at": 1800000000,
                        "task": {
                            "task_id": "11111111-2222-3333-4444-555555555555",
                            "title": "Daily Routine & College Life",
                            "prompt_text": "Describe your daily routine on a typical college day, from morning until evening. Explain what activities you usually do and what you enjoy most about your schedule.",
                            "prep_time_seconds": 30,
                            "duration_seconds": 60,
                            "difficulty_level": "standard_b1",
                            "rubric_version": "v1.0-jam-phd"
                        },
                        "rubric_version": "v1.0-jam-phd"
                    })
                )
            elif "/submit" in url:
                await route.fulfill(
                    status=201,
                    content_type="application/json",
                    body=json.dumps({
                        "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
                        "assessment_type": "pre",
                        "status": "queued_for_transcription",
                        "is_official": True,
                        "created_at": "2026-10-27T17:45:00Z"
                    })
                )
            elif "/transcribe" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(SAMPLE_TRANSCRIPT)
                )
            else:
                await route.continue_()

        await page.route("**/api/v1/**", handle_pre_route)
        await page.goto(f"{BASE_URL}/assessment/pre", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        # Trigger mic grant -> ready state
        grant_btn = page.locator("button:has-text('Grant Microphone Permission')")
        if await grant_btn.count() > 0:
            # Emulate mic ready state directly in window
            await page.evaluate("""() => {
              const buttons = Array.from(document.querySelectorAll('button'));
              const grantBtn = buttons.find(b => b.textContent.includes('Grant Microphone Permission'));
              if (grantBtn) grantBtn.click();
            }""")
            await page.wait_for_timeout(500)

        path4 = ARTIFACT_DIR / "participant_recording_transcribed.png"
        await page.screenshot(path=str(path4))
        print(f"Captured: {path4}")

        await browser.close()

    try:
        web_proc.terminate()
        web_proc.kill()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
