"""Automated Playwright captures for Phase P12: Post-Test Comparative Report & Metrics Engine.

Captures:
1. post_test_comparative_report.png - Full report with Syntax Fingerprint overlay (Sig B) and Reproducibility Panel (Sig E).
2. post_test_comparative_report_provisional.png - Unreviewed provisional warning view.
3. post_test_comparative_report_360.png - Responsive 360px mobile view.
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

COMPARATIVE_DATA_VERIFIED = {
    "is_provisional": False,
    "status_label": "verified",
    "provisional_warning": None,
    "standard_caution": "This is a descriptive comparison and does not by itself show that AI caused the change.",
    "overall_comparison": {
        "pre_word_count": 120,
        "post_word_count": 120,
        "pre_error_count": 8,
        "post_error_count": 3,
        "pre_rate_per_100": 6.67,
        "post_rate_per_100": 2.50,
        "absolute_reduction": 4.17,
        "relative_reduction_pct": 62.52,
        "relative_reduction_status": "defined",
    },
    "pre_summary": {
        "word_count": 120,
        "raw_annotation_count": 9,
        "assessable_error_count": 8,
        "excluded_count": 1,
        "error_rate_per_100": 6.67,
        "is_verified": True,
        "status_label": "verified",
    },
    "post_summary": {
        "word_count": 120,
        "raw_annotation_count": 4,
        "assessable_error_count": 3,
        "excluded_count": 1,
        "error_rate_per_100": 2.50,
        "is_verified": True,
        "status_label": "verified",
    },
    "category_comparisons": {
        "TNS": {
            "category_code": "TNS",
            "category_name": "Tense and Aspect",
            "pre_count": 3,
            "post_count": 1,
            "pre_words": 120,
            "post_words": 120,
            "pre_rate_per_100": 2.50,
            "post_rate_per_100": 0.83,
            "absolute_reduction": 1.67,
            "relative_reduction_pct": 66.8,
            "relative_reduction_status": "defined",
            "pre_status_label": "observed",
            "post_status_label": "observed",
        },
        "SVA": {
            "category_code": "SVA",
            "category_name": "Subject-Verb Agreement",
            "pre_count": 3,
            "post_count": 0,
            "pre_words": 120,
            "post_words": 120,
            "pre_rate_per_100": 2.50,
            "post_rate_per_100": 0.0,
            "absolute_reduction": 2.50,
            "relative_reduction_pct": 100.0,
            "relative_reduction_status": "defined",
            "pre_status_label": "observed",
            "post_status_label": "not observed in this sample",
        },
        "PREP": {
            "category_code": "PREP",
            "category_name": "Prepositions",
            "pre_count": 2,
            "post_count": 1,
            "pre_words": 120,
            "post_words": 120,
            "pre_rate_per_100": 1.67,
            "post_rate_per_100": 0.83,
            "absolute_reduction": 0.84,
            "relative_reduction_pct": 50.3,
            "relative_reduction_status": "defined",
            "pre_status_label": "observed",
            "post_status_label": "observed",
        },
        "ART": {
            "category_code": "ART",
            "category_name": "Articles (Definite / Indefinite / Zero)",
            "pre_count": 0,
            "post_count": 1,
            "pre_words": 120,
            "post_words": 120,
            "pre_rate_per_100": 0.0,
            "post_rate_per_100": 0.83,
            "absolute_reduction": -0.83,
            "relative_reduction_pct": None,
            "relative_reduction_status": "undefined_zero_baseline",
            "pre_status_label": "not observed in this sample",
            "post_status_label": "observed",
        },
    },
    "syntax_fingerprint": [
        {"category_code": "TNS", "category_name": "Tense and Aspect", "pre_rate": 2.5, "post_rate": 0.83, "pre_count": 3, "post_count": 1, "pre_observed": True, "post_observed": True, "pre_status_label": "observed", "post_status_label": "observed"},
        {"category_code": "SVA", "category_name": "Subject-Verb Agreement", "pre_rate": 2.5, "post_rate": 0.0, "pre_count": 3, "post_count": 0, "pre_observed": True, "post_observed": False, "pre_status_label": "observed", "post_status_label": "not observed in this sample"},
        {"category_code": "PREP", "category_name": "Prepositions", "pre_rate": 1.67, "post_rate": 0.83, "pre_count": 2, "post_count": 1, "pre_observed": True, "post_observed": True, "pre_status_label": "observed", "post_status_label": "observed"},
        {"category_code": "ART", "category_name": "Articles", "pre_rate": 0.0, "post_rate": 0.83, "pre_count": 0, "post_count": 1, "pre_observed": False, "post_observed": True, "pre_status_label": "not observed in this sample", "post_status_label": "observed"},
        {"category_code": "WO", "category_name": "Word Order", "pre_rate": 0.0, "post_rate": 0.0, "pre_count": 0, "post_count": 0, "pre_observed": False, "post_observed": False, "pre_status_label": "not observed in this sample", "post_status_label": "not observed in this sample"},
        {"category_code": "AUX", "category_name": "Auxiliary Verbs", "pre_rate": 0.0, "post_rate": 0.0, "pre_count": 0, "post_count": 0, "pre_observed": False, "post_observed": False, "pre_status_label": "not observed in this sample", "post_status_label": "not observed in this sample"},
        {"category_code": "PRO", "category_name": "Pronouns", "pre_rate": 0.0, "post_rate": 0.0, "pre_count": 0, "post_count": 0, "pre_observed": False, "post_observed": False, "pre_status_label": "not observed in this sample", "post_status_label": "not observed in this sample"},
        {"category_code": "OTH", "category_name": "Other Variations", "pre_rate": 0.0, "post_rate": 0.0, "pre_count": 0, "post_count": 0, "pre_observed": False, "post_observed": False, "pre_status_label": "not observed in this sample", "post_status_label": "not observed in this sample"},
    ],
    "reproducibility_panel": {
        "formulas": {
            "error_rate_per_100_words": "(assessable_error_count / total_words) * 100",
            "absolute_reduction": "pre_rate - post_rate",
            "relative_reduction_pct": "((pre_rate - post_rate) / pre_rate) * 100 (defined ONLY if pre_rate > 0)",
            "category_error_rate": "(category_assessable_count / total_words) * 100",
        },
        "pre_inputs": {
            "annotation_set_used": "effective",
            "raw_annotation_count": 9,
            "assessable_error_count": 8,
            "excluded_items_count": 1,
            "total_words": 120,
            "counting_rule": "count_all",
            "rubric_version": "v1.0-jam-phd",
            "prompt_version": "v1.0-assessor",
            "model_version": "mock-syntax-v1",
            "stt_version": "mock-stt-v1",
            "is_verified": True,
        },
        "post_inputs": {
            "annotation_set_used": "effective",
            "raw_annotation_count": 4,
            "assessable_error_count": 3,
            "excluded_items_count": 1,
            "total_words": 120,
            "counting_rule": "count_all",
            "rubric_version": "v1.0-jam-phd",
            "prompt_version": "v1.0-assessor",
            "model_version": "mock-syntax-v1",
            "stt_version": "mock-stt-v1",
            "is_verified": True,
        },
        "verification_status": {
            "is_pre_verified": True,
            "is_post_verified": True,
            "overall_status": "verified",
        },
    },
}

COMPARATIVE_DATA_PROVISIONAL = dict(COMPARATIVE_DATA_VERIFIED)
COMPARATIVE_DATA_PROVISIONAL["is_provisional"] = True
COMPARATIVE_DATA_PROVISIONAL["status_label"] = "provisional"
COMPARATIVE_DATA_PROVISIONAL["provisional_warning"] = "Provisional analysis: human review pending. Post-test candidate annotations have not yet been adjudicated in Reviewer Cockpit."


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

    print("Next.js server ready! Launching headless Edge...")
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)

        # ----------------------------------------------------
        # 1. Verified Comparative Report (with Reproducibility Panel open)
        # ----------------------------------------------------
        context = await browser.new_context(viewport={"width": 1280, "height": 1100})
        page = await context.new_page()

        async def handle_verified_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_PARTICIPANT))
            elif "/comparative-report" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(COMPARATIVE_DATA_VERIFIED))
            else:
                await route.continue_()

        await page.route("**/api/v1/**", handle_verified_routes)
        print("Navigating to http://localhost:3000/assessment/ass-post-9501/comparative...")
        await page.goto(f"{BASE_URL}/assessment/ass-post-9501/comparative", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click Reproducibility Panel button to show drawer
        repro_btn = page.locator("button:has-text('Reproducibility Panel')")
        if await repro_btn.count() > 0:
            await repro_btn.click()
            await page.wait_for_timeout(500)

        verified_path = ARTIFACT_DIR / "post_test_comparative_report.png"
        await page.screenshot(path=str(verified_path), full_page=True)
        print(f"Captured: {verified_path}")

        # ----------------------------------------------------
        # 2. Provisional Comparative Report View
        # ----------------------------------------------------
        async def handle_provisional_routes(route):
            url = route.request.url
            if "/auth/me" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(USER_PARTICIPANT))
            elif "/comparative-report" in url:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(COMPARATIVE_DATA_PROVISIONAL))
            else:
                await route.continue_()

        page_prov = await context.new_page()
        await page_prov.route("**/api/v1/**", handle_provisional_routes)
        await page_prov.goto(f"{BASE_URL}/assessment/ass-post-9501/comparative", wait_until="networkidle")
        await page_prov.wait_for_timeout(1000)

        prov_path = ARTIFACT_DIR / "post_test_comparative_report_provisional.png"
        await page_prov.screenshot(path=str(prov_path), full_page=True)
        print(f"Captured: {prov_path}")

        # ----------------------------------------------------
        # 3. Mobile Viewport (360x850)
        # ----------------------------------------------------
        context_mobile = await browser.new_context(viewport={"width": 360, "height": 850})
        page_mobile = await context_mobile.new_page()
        await page_mobile.route("**/api/v1/**", handle_verified_routes)
        await page_mobile.goto(f"{BASE_URL}/assessment/ass-post-9501/comparative", wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        mobile_path = ARTIFACT_DIR / "post_test_comparative_report_360.png"
        await page_mobile.screenshot(path=str(mobile_path), full_page=True)
        print(f"Captured: {mobile_path}")

        await browser.close()

    try:
        subprocess.call(f"taskkill /F /T /PID {web_proc.pid}", shell=True)
    except Exception:
        pass
    print("Screenshot capture complete.")


if __name__ == "__main__":
    asyncio.run(main())
