"""Automated Playwright captures for Phase P11: Session History, Active Timing, and Recurrence (SRS Section 10, FR-13, FR-14).

Captures:
1. practice_session_history.png - Learner view showing practice KPIs, active vs idle duration, category correction rates, and recurring utterance patterns.
2. practice_session_history_360.png - Mobile 360px responsive view of practice history.
3. admin_adherence_dashboard.png - Researcher view showing cohort adherence vs target (3 sess/wk, 15m/sess) and FR-14 zero double-counting audit table.
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

USER_ADMIN = {
    "id": "u1111111-1111-1111-1111-111111111111",
    "email": "admin@syntaxlens.edu",
    "full_name": "Dr. Elena Rostova",
    "role": "researcher_admin",
    "is_active": True,
    "must_change_password": False,
}

PRACTICE_HISTORY = {
    "sessions": [
        {
            "session_id": "sess-8001-demo-a",
            "start_time": "2026-02-10T10:00:00Z",
            "end_time": "2026-02-10T10:16:00Z",
            "active_duration_seconds": 900,
            "idle_duration_seconds": 60,
            "turns_count": 8,
            "status": "completed",
            "topic": "Technology and College Life",
            "target_categories": ["SVA", "TNS"],
            "interruption_count": 0,
            "prompt_version": "v1.0-tutor-standard",
        },
        {
            "session_id": "sess-8001-demo-b",
            "start_time": "2026-02-12T14:30:00Z",
            "end_time": "2026-02-12T14:47:00Z",
            "active_duration_seconds": 900,
            "idle_duration_seconds": 120,
            "turns_count": 10,
            "status": "completed",
            "topic": "Daily routines and workplace communication",
            "target_categories": ["SVA"],
            "interruption_count": 1,
            "prompt_version": "v1.0-tutor-standard",
        },
    ],
    "total_sessions": 2,
    "correction_metrics": {
        "overall_rate_pct": 66.7,
        "total_unique_error_episodes": 3,
        "total_independent_corrections": 2,
        "category_breakdown": {
            "SVA": {
                "unique_error_episodes": 2,
                "independent_corrections": 1,
                "hint_assisted_corrections": 1,
                "unresolved": 0,
                "independent_correction_rate_pct": 50.0,
            },
            "TNS": {
                "unique_error_episodes": 1,
                "independent_corrections": 1,
                "hint_assisted_corrections": 0,
                "unresolved": 0,
                "independent_correction_rate_pct": 100.0,
            },
        },
        "disclaimer": "Descriptive practice metric only. Never used as an official assessment score or proficiency certification.",
    },
}

RECURRENCE_PATTERNS = [
    {
        "pattern_id": "pat-1",
        "target_category": "SVA",
        "utterance_fingerprint": "d9e84b12f6a78201",
        "canonical_phrase": "he go to college every day",
        "construction_type": "SVA_construction",
        "occurrence_count": 2,
        "first_seen_at": "2026-02-10T10:02:15Z",
        "last_seen_at": "2026-02-12T14:35:40Z",
        "resolved_independently": True,
    },
    {
        "pattern_id": "pat-2",
        "target_category": "TNS",
        "utterance_fingerprint": "a4f1082c33bc09e1",
        "canonical_phrase": "yesterday i go there by bus",
        "construction_type": "TNS_construction",
        "occurrence_count": 1,
        "first_seen_at": "2026-02-10T10:08:20Z",
        "last_seen_at": "2026-02-10T10:08:20Z",
        "resolved_independently": True,
    },
]

ADHERENCE_DATA = {
    "total_active_minutes": 45.0,
    "completed_sessions": 3,
    "active_duration_seconds": 2700,
    "estimated_weeks": 1.0,
    "sessions_per_week": 3.0,
    "expected_sessions_per_week": 3,
    "expected_total_minutes": 45.0,
    "adherence_percentage": 100.0,
    "status_label": "High Adherence",
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
    for _ in range(25):
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
        # 1. Learner Practice History View (Desktop 1280x950)
        # ----------------------------------------------------
        context_history = await browser.new_context(viewport={"width": 1280, "height": 950})
        page_history = await context_history.new_page()

        async def handle_history_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_PARTICIPANT))
            elif "/tutor/history" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(PRACTICE_HISTORY))
            elif "/tutor/recurrence" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(RECURRENCE_PATTERNS))
            else:
                await route.continue_()

        await page_history.route("**/api/v1/**", handle_history_routes)
        print("Navigating to http://localhost:3000/tutor/history...")
        await page_history.goto(f"{BASE_URL}/tutor/history", wait_until="networkidle")
        await page_history.wait_for_timeout(1000)

        history_path = ARTIFACT_DIR / "practice_session_history.png"
        await page_history.screenshot(path=str(history_path), full_page=True)
        print(f"Captured: {history_path}")

        # ----------------------------------------------------
        # 2. Learner Practice History View (Mobile 360x800)
        # ----------------------------------------------------
        context_mobile = await browser.new_context(viewport={"width": 360, "height": 800})
        page_mobile = await context_mobile.new_page()
        await page_mobile.route("**/api/v1/**", handle_history_routes)
        await page_mobile.goto(f"{BASE_URL}/tutor/history", wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        mobile_path = ARTIFACT_DIR / "practice_session_history_360.png"
        await page_mobile.screenshot(path=str(mobile_path), full_page=True)
        print(f"Captured: {mobile_path}")

        # ----------------------------------------------------
        # 3. Researcher Adherence Dashboard (Desktop 1280x950)
        # ----------------------------------------------------
        context_admin = await browser.new_context(viewport={"width": 1280, "height": 950})
        page_admin = await context_admin.new_page()

        async def handle_admin_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_ADMIN))
            elif "/tutor/adherence" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(ADHERENCE_DATA))
            else:
                await route.continue_()

        await page_admin.route("**/api/v1/**", handle_admin_routes)
        print("Navigating to http://localhost:3000/admin/adherence...")
        await page_admin.goto(f"{BASE_URL}/admin/adherence", wait_until="networkidle")
        await page_admin.wait_for_timeout(1000)

        admin_path = ARTIFACT_DIR / "admin_adherence_dashboard.png"
        await page_admin.screenshot(path=str(admin_path), full_page=True)
        print(f"Captured: {admin_path}")

        await browser.close()

    # Terminate background web server
    try:
        subprocess.call(f"taskkill /F /T /PID {web_proc.pid}", shell=True)
    except Exception:
        pass
    print("Screenshot captures complete.")


if __name__ == "__main__":
    asyncio.run(main())
