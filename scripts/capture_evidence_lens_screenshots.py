"""Automated Playwright captures for Phase P8 Error Analysis Engine & Signature Feature A (Evidence Lens).

Captures:
1. evidence_lens_main_view.png - Evidence Lens with highlighted candidate spans, audio playback controller, and SVA candidate card.
2. evidence_lens_audio_seek.png - Interactive span click seeking audio playback and switching candidate deviation card to TNS.
3. evidence_lens_participant_gated.png - Participant blinded view before researcher release with research protocol notice.
4. evidence_lens_review_queue.png - Researcher Human Review Adjudication Queue (/admin/review-queue) with flagged spans.
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

USER_RESEARCHER = {
    "id": "u1111111-1111-1111-1111-111111111111",
    "email": "lead.researcher@syntaxlens.edu",
    "full_name": "Dr. Eleanor Vance",
    "role": "researcher_admin",
    "is_active": True,
    "must_change_password": False,
}

REPORT_RELEASED = {
    "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
    "assessment_type": "pre_test",
    "status": "analyzed",
    "transcript": "He go to college every day by bus, but yesterday he walk because the bus was late.",
    "word_count": 17,
    "is_visible_to_participant": True,
    "banner_notice": "Automated preliminary analysis for research purposes. All candidate errors are unverified until human review.",
    "rubric_version": "v1.0-jam-phd",
    "prompt_version": "v1.0-assessor",
    "model_version": "gemini-1.5-pro",
    "annotations": [
        {
            "annotation_id": "ann-sva-001",
            "start_char": 3,
            "end_char": 5,
            "start_time_ms": 650,
            "end_time_ms": 1100,
            "candidate_error": "go",
            "suggested_correction": "goes",
            "category_code": "SVA",
            "explanation": "Subject 'He' requires third-person singular verb 'goes' in simple present habit.",
            "confidence": 0.96,
            "ai_status": "suggested",
            "flag": "none",
            "rubric_version": "v1.0-jam-phd",
            "prompt_version": "v1.0-assessor",
            "model_version": "gemini-1.5-pro",
        },
        {
            "annotation_id": "ann-tns-002",
            "start_char": 55,
            "end_char": 59,
            "start_time_ms": 4500,
            "end_time_ms": 5000,
            "candidate_error": "walk",
            "suggested_correction": "walked",
            "category_code": "TNS",
            "explanation": "Past temporal marker 'yesterday' requires simple past 'walked'.",
            "confidence": 0.94,
            "ai_status": "suggested",
            "flag": "none",
            "rubric_version": "v1.0-jam-phd",
            "prompt_version": "v1.0-assessor",
            "model_version": "gemini-1.5-pro",
        },
    ],
}

REPORT_GATED = {
    "assessment_id": "b1234567-89ab-4cde-f012-3456789abcde",
    "assessment_type": "pre_test",
    "status": "analyzed",
    "transcript": "He go to college every day by bus, but yesterday he walk because the bus was late.",
    "word_count": 17,
    "is_visible_to_participant": False,
    "banner_notice": "Automated candidate analysis is being evaluated and will be released following review.",
    "rubric_version": "v1.0-jam-phd",
    "prompt_version": "v1.0-assessor",
    "model_version": "gemini-1.5-pro",
    "annotations": [],
}

REVIEW_QUEUE = [
    {
        "assessment_id": "a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a",
        "participant_code": "SL-2026-0004",
        "assessment_type": "pre_test",
        "needs_review_count": 2,
        "total_annotations": 4,
        "created_at": "2026-10-27T18:20:00Z",
    },
    {
        "assessment_id": "b1234567-89ab-4cde-f012-3456789abcde",
        "participant_code": "SL-2026-0012",
        "assessment_type": "post_test",
        "needs_review_count": 1,
        "total_annotations": 3,
        "created_at": "2026-10-27T19:05:00Z",
    },
    {
        "assessment_id": "c9998888-7777-6666-5555-444433332222",
        "participant_code": "SL-2026-0021",
        "assessment_type": "pre_test",
        "needs_review_count": 3,
        "total_annotations": 5,
        "created_at": "2026-10-27T19:40:00Z",
    },
]


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("Checking / starting Next.js development server...")
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

        # Intercept and mock API routes
        async def handle_route(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(USER_RESEARCHER),
                )
            elif "/assessments/a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a/report" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(REPORT_RELEASED),
                )
            elif "/assessments/b1234567-89ab-4cde-f012-3456789abcde/report" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(REPORT_GATED),
                )
            elif "/assessments/review-queue" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(REVIEW_QUEUE),
                )
            elif "/audio-url" in url:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"audio_url": "https://example.com/audio/sample.webm"}),
                )
            else:
                await route.continue_()

        await page.route("**/api/v1/**", handle_route)

        # 1. Main Evidence Lens View (SVA Card focused)
        print("Capturing 1: evidence_lens_main_view.png...")
        await page.goto(f"{BASE_URL}/assessment/a9876543-210f-4e3b-9a1c-8f7e6d5c4b3a/report", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        path1 = ARTIFACT_DIR / "evidence_lens_main_view.png"
        await page.screenshot(path=str(path1))
        print(f"Captured: {path1}")

        # 2. Audio Seek & Span Selection (Click 'walk' TNS span)
        print("Capturing 2: evidence_lens_audio_seek.png...")
        walk_span = page.locator("button:has-text('walk')")
        if await walk_span.count() > 0:
            await walk_span.first.click()
            await page.wait_for_timeout(500)
        path2 = ARTIFACT_DIR / "evidence_lens_audio_seek.png"
        await page.screenshot(path=str(path2))
        print(f"Captured: {path2}")

        # 3. Participant Gated / Blinded View
        print("Capturing 3: evidence_lens_participant_gated.png...")
        await page.goto(f"{BASE_URL}/assessment/b1234567-89ab-4cde-f012-3456789abcde/report", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        path3 = ARTIFACT_DIR / "evidence_lens_participant_gated.png"
        await page.screenshot(path=str(path3))
        print(f"Captured: {path3}")

        # 4. Human Review Adjudication Queue
        print("Capturing 4: evidence_lens_review_queue.png...")
        await page.goto(f"{BASE_URL}/admin/review-queue", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        path4 = ARTIFACT_DIR / "evidence_lens_review_queue.png"
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
