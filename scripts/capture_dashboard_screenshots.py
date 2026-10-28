"""Automated Playwright captures for Phase P13: Participant and Researcher Dashboards.

Captures:
1. student_home_desktop.png (1280x900) - Student Home screen with progress ring, gentle next-best-action, and milestones.
2. student_home_360.png (360x800) - Student Home screen on 360px mobile viewport.
3. student_progress_desktop.png (1280x950) - Student Progress screen with category trends, plain-language explainer, and repeated patterns.
4. student_progress_360.png (360x800) - Student Progress screen on 360px mobile viewport.
5. researcher_dashboard_desktop.png (1280x1100) - Researcher Cohort dashboard with funnel, group comparison distribution table, and capacity & cost panel.
6. researcher_dashboard_360.png (360x850) - Researcher Cohort dashboard on 360px mobile viewport.
7. researcher_drilldown_desktop.png (1280x950) - Researcher per-participant drilldown with longitudinal event timeline.
"""

import asyncio
import json
import os
import subprocess
import time
import urllib.request
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
    "email": "lead.researcher@syntaxlens.edu",
    "full_name": "Dr. Elena Rostova",
    "role": "researcher_admin",
    "is_active": True,
    "must_change_password": False,
}

PARTICIPANT_HOME_DATA = {
    "participant_code": "SL-2026-0042",
    "study_group": "intervention",
    "stage": "practising",
    "progress_percentage": 65,
    "next_best_action": {
        "title": "Practice Session 2 of 3 Ready",
        "action_text": "Start Practice Turn",
        "route": "/tutor",
        "description": "Engage in a 15-minute conversational practice session with the Hint Ladder tutor.",
        "urgency": "medium",
    },
    "pre_test_status": "completed",
    "post_test_status": "not_started",
    "practice_sessions_completed": 1,
    "total_active_minutes": 15.5,
    "recent_activity": [
        {
            "title": "Tutoring Session (Past Tense Narration)",
            "timestamp": "2026-10-27T10:15:00Z",
            "status": "completed",
            "active_minutes": 15.5,
        },
        {
            "title": "Completed Baseline Pre-Test Assessment",
            "timestamp": "2026-10-24T10:45:00Z",
            "status": "completed",
        },
    ],
    "is_blinded": True,
}

PARTICIPANT_PROGRESS_DATA = {
    "participant_code": "SL-2026-0042",
    "is_results_released": True,
    "total_practice_minutes": 42.5,
    "total_completed_sessions": 3,
    "independent_correction_rate_pct": 68.2,
    "repeated_error_patterns": [
        {
            "fingerprint": "she_go_to_market",
            "category_code": "SVA",
            "normalised_form": "she go to market",
            "raw_utterance": "yesterday she go to market",
            "recurrence_count": 3,
            "first_seen": "2026-10-25T14:30:00Z",
            "last_seen": "2026-10-27T10:15:00Z",
        },
        {
            "fingerprint": "i_am_agree_with_you",
            "category_code": "AUX",
            "normalised_form": "i am agree with you",
            "raw_utterance": "i am agree with you",
            "recurrence_count": 2,
            "first_seen": "2026-10-26T09:00:00Z",
            "last_seen": "2026-10-27T10:45:00Z",
        },
    ],
    "category_breakdown": {},
    "comparative_summary": {
        "pre_rate_per_100": 9.38,
        "post_rate_per_100": 4.17,
        "absolute_reduction": 5.21,
        "relative_reduction_pct": 55.54,
        "is_provisional": False,
        "status_label": "Verified by Reviewer",
        "post_assessment_id": "demo-post-id",
        "category_comparisons": [
            {
                "category_code": "TNS",
                "category_name": "Tense & Aspect",
                "pre_count": 6,
                "post_count": 2,
                "pre_rate_per_100": 4.69,
                "post_rate_per_100": 1.67,
                "absolute_reduction": 3.02,
                "relative_reduction_pct": 64.39,
                "post_status_label": "Observed",
            },
            {
                "category_code": "SVA",
                "category_name": "Subject-Verb Agreement",
                "pre_count": 4,
                "post_count": 0,
                "pre_rate_per_100": 3.12,
                "post_rate_per_100": 0.0,
                "absolute_reduction": 3.12,
                "relative_reduction_pct": 100.0,
                "post_status_label": "Not observed in this sample",
            },
            {
                "category_code": "WO",
                "category_name": "Word Order",
                "pre_count": 2,
                "post_count": 1,
                "pre_rate_per_100": 1.56,
                "post_rate_per_100": 0.83,
                "absolute_reduction": 0.73,
                "relative_reduction_pct": 46.79,
                "post_status_label": "Observed",
            },
        ],
    },
    "plain_language_explainer": {
        "title": "What do these numbers mean?",
        "intro": "SyntaxLens evaluates your spoken English syntax during spontaneous speaking tasks.",
        "sections": [
            {
                "term": "Error Rate per 100 Words",
                "explanation": "Instead of counting raw mistakes, we divide your errors by the total number of words you spoke and multiply by 100. This makes speaking samples of different lengths fair to compare.",
            },
            {
                "term": "Observed vs Not Observed",
                "explanation": "If a grammar structure had 0 errors in your post-test, we label it 'not observed in this sample'. In academic research, we never say 'mastered' because one speech sample does not prove permanent perfection.",
            },
            {
                "term": "Provisional vs Verified",
                "explanation": "AI first analyzes your audio, but a human research linguist reviews candidate deviations. While review is in progress, numbers are marked 'Provisional'.",
            },
            {
                "term": "Descriptive Practice Metrics",
                "explanation": "Practice sessions and self-correction rates describe your learning journey during tutoring. They are not official scores.",
            },
        ],
        "standard_caution": "This is a descriptive comparison and does not by itself show that AI caused the change.",
    },
}

RESEARCHER_DASHBOARD_DATA = {
    "filter_group": "all",
    "funnel": {
        "enrolled": 48,
        "consented": 45,
        "pre_test_completed": 42,
        "practising": 38,
        "post_test_completed": 34,
    },
    "group_allocation": {
        "intervention": 24,
        "control": 24,
    },
    "missing_data": {
        "withdrawn_count": 2,
        "missing_pre_count": 3,
        "missing_post_count": 8,
        "withdrawn_participants": ["SL-2026-0012", "SL-2026-0029"],
    },
    "review_queue_size": 14,
    "pipeline_failures": 0,
    "aggregates": {
        "n": 34,
        "total_pre_words": 4320,
        "total_post_words": 4410,
        "total_pre_errors": 389,
        "total_post_errors": 198,
        "pre_distribution": {
            "n": 34,
            "mean": 9.0,
            "median": 8.85,
            "min": 5.2,
            "max": 14.5,
            "std_dev": 2.15,
        },
        "post_distribution": {
            "n": 34,
            "mean": 4.49,
            "median": 4.25,
            "min": 1.1,
            "max": 8.9,
            "std_dev": 1.82,
        },
        "absolute_reduction_distribution": {
            "n": 34,
            "mean": 4.51,
            "median": 4.4,
            "min": 0.8,
            "max": 9.2,
            "std_dev": 1.95,
        },
        "mean_relative_reduction_pct": 49.8,
        "all_verified": False,
        "provisional_count": 6,
        "standard_caution": "This is a descriptive comparison and does not by itself show that AI caused the change.",
    },
    "capacity_and_cost": {
        "design_target_participants": 120,
        "enrolled_participants": 48,
        "capacity_utilization_pct": 40.0,
        "total_storage_mb": 284.5,
        "total_stt_calls": 86,
        "total_llm_calls": 340,
        "estimated_total_cost_usd": 6.85,
        "estimated_cost_per_participant_usd": 0.14,
        "headroom_participants": 72,
    },
}

PARTICIPANTS_ROSTER = [
    {
        "participant_id": "demo-part-1",
        "research_code": "SL-2026-0042",
        "study_group": "intervention",
        "pre_test_status": "completed",
        "pre_test_verified": True,
        "post_test_status": "completed",
        "post_test_verified": True,
        "practice_sessions_count": 3,
        "active_practice_minutes": 42.5,
        "is_withdrawn": False,
        "enrolled_at": "2026-10-24T10:00:00Z",
    },
    {
        "participant_id": "demo-part-2",
        "research_code": "SL-2026-0043",
        "study_group": "control",
        "pre_test_status": "completed",
        "pre_test_verified": True,
        "post_test_status": "completed",
        "post_test_verified": False,
        "practice_sessions_count": 0,
        "active_practice_minutes": 0.0,
        "is_withdrawn": False,
        "enrolled_at": "2026-10-24T11:15:00Z",
    },
    {
        "participant_id": "demo-part-3",
        "research_code": "SL-2026-0044",
        "study_group": "intervention",
        "pre_test_status": "completed",
        "pre_test_verified": True,
        "post_test_status": "recording",
        "post_test_verified": False,
        "practice_sessions_count": 2,
        "active_practice_minutes": 28.0,
        "is_withdrawn": False,
        "enrolled_at": "2026-10-25T09:30:00Z",
    },
]

DRILLDOWN_DATA = {
    "participant_id": "demo-part-1",
    "research_code": "SL-2026-0042",
    "study_group": "intervention",
    "is_withdrawn": False,
    "enrolled_at": "2026-10-24T10:00:00Z",
    "timeline": [
        {
            "event_type": "assessment_post",
            "title": "Submitted Post-Test Recording (pair_commute_work)",
            "timestamp": "2026-10-28T09:30:00Z",
            "status": "completed",
            "is_verified": True,
            "word_count": 120,
        },
        {
            "event_type": "practice_session",
            "title": "Tutoring Turn (Past Tense Narration)",
            "timestamp": "2026-10-27T10:15:00Z",
            "status": "completed",
            "active_minutes": 15.2,
            "turns_count": 5,
        },
        {
            "event_type": "practice_session",
            "title": "Tutoring Turn (Subject-Verb Agreement)",
            "timestamp": "2026-10-26T14:00:00Z",
            "status": "completed",
            "active_minutes": 14.8,
            "turns_count": 4,
        },
        {
            "event_type": "practice_session",
            "title": "Tutoring Turn (Word Order & Questions)",
            "timestamp": "2026-10-25T11:20:00Z",
            "status": "completed",
            "active_minutes": 12.5,
            "turns_count": 4,
        },
        {
            "event_type": "assessment_pre",
            "title": "Submitted Baseline Pre-Test Recording (pair_commute_work)",
            "timestamp": "2026-10-24T10:45:00Z",
            "status": "completed",
            "is_verified": True,
            "word_count": 128,
        },
    ],
    "assessments": [
        {
            "assessment_id": "demo-post-id",
            "assessment_type": "post",
            "status": "completed",
            "is_verified": True,
            "word_count": 120,
            "created_at": "2026-10-28T09:30:00Z",
        },
        {
            "assessment_id": "demo-pre-id",
            "assessment_type": "pre",
            "status": "completed",
            "is_verified": True,
            "word_count": 128,
            "created_at": "2026-10-24T10:45:00Z",
        },
    ],
    "practice_history": {
        "total_sessions": 3,
        "sessions": [
            {
                "session_id": "sess-1",
                "topic": "Past Tense Narration",
                "active_duration_seconds": 912,
                "turns_count": 5,
                "status": "completed",
                "start_time": "2026-10-27T10:15:00Z",
            },
        ],
        "correction_metrics": {
            "overall_rate_pct": 68.2,
            "category_breakdown": {},
        },
    },
    "patterns": [
        {
            "fingerprint": "she_go_to_market",
            "category_code": "SVA",
            "normalised_form": "she go to market",
            "raw_utterance": "yesterday she go to market",
            "recurrence_count": 3,
            "first_seen": "2026-10-25T14:30:00Z",
            "last_seen": "2026-10-27T10:15:00Z",
        },
        {
            "fingerprint": "i_am_agree_with_you",
            "category_code": "AUX",
            "normalised_form": "i am agree with you",
            "raw_utterance": "i am agree with you",
            "recurrence_count": 2,
            "first_seen": "2026-10-26T09:00:00Z",
            "last_seen": "2026-10-27T10:45:00Z",
        },
    ],
}


async def main():
    print("Checking if Next.js server is running...")
    is_running = False
    try:
        req = urllib.request.urlopen(f"{BASE_URL}/api/v1/health", timeout=1)
        if req.status == 200:
            is_running = True
    except Exception:
        pass

    web_proc = None
    if not is_running:
        print("Starting Next.js dev server on port 3000...")
        web_proc = subprocess.Popen(
            "npm run dev",
            cwd=r"D:\syntaxlens\apps\web",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    server_ready = False
    for attempt in range(40):
        try:
            req = urllib.request.urlopen(BASE_URL, timeout=1)
            if req.status == 200:
                server_ready = True
                break
        except Exception:
            time.sleep(1)

    if not server_ready:
        print("Waiting extra 3 seconds for server...")
        time.sleep(3)

    print("Next.js server ready! Launching headless Edge...")
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)

        async def route_handler(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_ADMIN))
            elif "/dashboard/participant" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(PARTICIPANT_HOME_DATA))
            elif "/dashboard/progress" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(PARTICIPANT_PROGRESS_DATA))
            elif "/dashboard/researcher/participants/demo-part-1" in url or "/dashboard/researcher/participants/" in url and not url.endswith("/participants"):
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(DRILLDOWN_DATA))
            elif "/dashboard/researcher/participants" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(PARTICIPANTS_ROSTER))
            elif "/dashboard/researcher" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(RESEARCHER_DASHBOARD_DATA))
            else:
                await route.continue_()

        # 1. Student Home Desktop (1280x900)
        context_dt = await browser.new_context(viewport={"width": 1280, "height": 900})
        page_dt = await context_dt.new_page()
        await page_dt.route("**/api/v1/**", route_handler)
        await page_dt.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        await page_dt.wait_for_timeout(1000)
        p1 = ARTIFACT_DIR / "student_home_desktop.png"
        await page_dt.screenshot(path=str(p1), full_page=True)
        print(f"Captured: {p1}")

        # 2. Student Home Mobile (360x800)
        context_m = await browser.new_context(viewport={"width": 360, "height": 800})
        page_m = await context_m.new_page()
        await page_m.route("**/api/v1/**", route_handler)
        await page_m.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        await page_m.wait_for_timeout(1000)
        p2 = ARTIFACT_DIR / "student_home_360.png"
        await page_m.screenshot(path=str(p2), full_page=True)
        print(f"Captured: {p2}")

        # 3. Student Progress Desktop (1280x950)
        page_prog_dt = await context_dt.new_page()
        await page_prog_dt.route("**/api/v1/**", route_handler)
        await page_prog_dt.goto(f"{BASE_URL}/dashboard/progress", wait_until="networkidle")
        await page_prog_dt.wait_for_timeout(1000)
        p3 = ARTIFACT_DIR / "student_progress_desktop.png"
        await page_prog_dt.screenshot(path=str(p3), full_page=True)
        print(f"Captured: {p3}")

        # 4. Student Progress Mobile (360x800)
        page_prog_m = await context_m.new_page()
        await page_prog_m.route("**/api/v1/**", route_handler)
        await page_prog_m.goto(f"{BASE_URL}/dashboard/progress", wait_until="networkidle")
        await page_prog_m.wait_for_timeout(1000)
        p4 = ARTIFACT_DIR / "student_progress_360.png"
        await page_prog_m.screenshot(path=str(p4), full_page=True)
        print(f"Captured: {p4}")

        # 5. Researcher Dashboard Desktop (1280x1100)
        context_rd = await browser.new_context(viewport={"width": 1280, "height": 1100})
        page_rd = await context_rd.new_page()
        await page_rd.route("**/api/v1/**", route_handler)
        await page_rd.goto(f"{BASE_URL}/admin/dashboard", wait_until="networkidle")
        await page_rd.wait_for_timeout(1000)
        p5 = ARTIFACT_DIR / "researcher_dashboard_desktop.png"
        await page_rd.screenshot(path=str(p5), full_page=True)
        print(f"Captured: {p5}")

        # 6. Researcher Dashboard Mobile (360x850)
        page_rd_m = await context_m.new_page()
        await page_rd_m.route("**/api/v1/**", route_handler)
        await page_rd_m.goto(f"{BASE_URL}/admin/dashboard", wait_until="networkidle")
        await page_rd_m.wait_for_timeout(1000)
        p6 = ARTIFACT_DIR / "researcher_dashboard_360.png"
        await page_rd_m.screenshot(path=str(p6), full_page=True)
        print(f"Captured: {p6}")

        # 7. Researcher Participant Drilldown Desktop (1280x950)
        page_dd = await context_dt.new_page()
        await page_dd.route("**/api/v1/**", route_handler)
        await page_dd.goto(f"{BASE_URL}/admin/dashboard/participant/demo-part-1", wait_until="networkidle")
        await page_dd.wait_for_timeout(1000)
        p7 = ARTIFACT_DIR / "researcher_drilldown_desktop.png"
        await page_dd.screenshot(path=str(p7), full_page=True)
        print(f"Captured: {p7}")

        await browser.close()

    if web_proc:
        try:
            subprocess.call(f"taskkill /F /T /PID {web_proc.pid}", shell=True)
        except Exception:
            pass

    print("All screenshots successfully captured!")


if __name__ == "__main__":
    asyncio.run(main())
