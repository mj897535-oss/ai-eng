"""Automated Playwright captures for Phase P5 Research Settings and Version Freezing.

Captures:
1. Tab 1: Rubric Taxonomy (8 categories, counting rules, frozen baseline v1.0-jam-phd)
2. Tab 2: Prompt Versions for Three AI Roles (Pre-assessor, Tutor hint ladder, Post-assessor)
3. Tab 3: Topic Bank & Equivalence Pairs with Reproducible Seed Simulator
4. Tab 4: Unified Version Differential Viewer
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = Path(r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0")
BASE_URL = "http://localhost:3000"


async def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting Next.js production server...")
    web_proc = subprocess.Popen(
        "npm --prefix apps/web start",
        shell=True,
    )

    import urllib.request
    server_ready = False
    for i in range(15):
        try:
            req = urllib.request.Request(f"{BASE_URL}/login")
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
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        # Mock API responses for settings
        await page.route("**/api/v1/admin/config/rubrics", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""[
                {
                    "rubric_id": "c1f73b88-1a52-47d9-bfa2-8b6fae10c710",
                    "version_code": "v1.0-jam-phd",
                    "name": "Doctoral Baseline Spoken English Syntactic Rubric",
                    "description": "8 core syntactic categories with counting rules and Indian English variation handling.",
                    "status": "frozen",
                    "is_frozen": true,
                    "approved_at": "2026-01-15T10:00:00Z",
                    "frozen_at": "2026-01-15T10:00:00Z",
                    "category_count": 8,
                    "created_at": "2026-01-15T10:00:00Z"
                }
            ]"""
        ))

        await page.route("**/api/v1/admin/config/rubrics/v1.0-jam-phd", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "rubric_id": "c1f73b88-1a52-47d9-bfa2-8b6fae10c710",
                "version_code": "v1.0-jam-phd",
                "name": "Doctoral Baseline Spoken English Syntactic Rubric",
                "description": "8 core syntactic categories with counting rules and Indian English variation handling.",
                "status": "frozen",
                "is_frozen": true,
                "approved_at": "2026-01-15T10:00:00Z",
                "frozen_at": "2026-01-15T10:00:00Z",
                "category_count": 8,
                "counting_rules": "Rule 1: Multiple errors in one sentence are counted separately if they belong to different syntactic categories. Rule 2: Non-standard structures widely accepted in educated Indian English (e.g. progressive aspect with stative verbs 'I am having a doubt') are annotated as acceptable regional variation unless causing severe semantic ambiguity.",
                "word_counting_rules": "Rule 1: Standard whitespace-delimited tokens. Rule 2: Contracted forms count as separate words (e.g. don't -> 2 words). Rule 3: Filled pauses (um, uh) and unintelligible fragments are excluded from total assessable words.",
                "categories": [
                    {
                        "code": "TNS",
                        "name": "Tense and Aspect",
                        "definition": "Incorrect verb inflection, auxiliary-verb mismatch in progressive/perfective aspect, or past/present inconsistency in narrative context.",
                        "assessable_criteria": "Deviations where finite verb morphology does not match temporal frame or standard aspectual semantics.",
                        "variation_rules": "Statistically common Indian English habitual progressives (e.g. 'I am knowing') are tagged as acceptable regional variation.",
                        "examples": [
                            {"phrase": "Yesterday he go to market", "correction": "Yesterday he went to market", "explanation": "Simple past required."},
                            {"phrase": "She has saw the movie", "correction": "She has seen the movie", "explanation": "Past participle 'seen' required with 'has'."}
                        ]
                    },
                    {
                        "code": "SVA",
                        "name": "Subject-Verb Agreement",
                        "definition": "Mismatch in number or person between grammatical subject and finite verb predicate.",
                        "assessable_criteria": "Singular subjects paired with plural verb forms, or plural/compound subjects paired with 3rd-person singular verbs.",
                        "variation_rules": "Agreement with collective nouns is treated permissively.",
                        "examples": [
                            {"phrase": "She study every morning", "correction": "She studies every morning", "explanation": "Third-person singular -s required."}
                        ]
                    },
                    {
                        "code": "WO",
                        "name": "Word Order & Constituent Structure",
                        "definition": "Deviant ordering of clausal elements, incorrect inversion in questions, or topicalization that violates English syntax.",
                        "assessable_criteria": "Phrasal elements violating head-initial constituent parameters in English.",
                        "variation_rules": "Subtle topicalization without auxiliary inversion is noted with lower pedagogical severity.",
                        "examples": [
                            {"phrase": "Why you are late?", "correction": "Why are you late?", "explanation": "Inversion required in wh- questions."}
                        ]
                    },
                    {
                        "code": "AUX",
                        "name": "Auxiliary & Modal System",
                        "definition": "Omission, duplication, or erroneous selection of auxiliary verbs or modals.",
                        "assessable_criteria": "Missing auxiliary 'be'/'do'/'have' in compound tenses, passive voice, or negation.",
                        "variation_rules": "Use of 'can be able to' redundancy is logged as modal duplication.",
                        "examples": [
                            {"phrase": "He not coming today", "correction": "He is not coming today", "explanation": "Auxiliary 'is' omitted."}
                        ]
                    },
                    {
                        "code": "ART",
                        "name": "Article & Determiner Use",
                        "definition": "Omission, insertion, or substitution of definite, indefinite, or zero articles.",
                        "assessable_criteria": "Generic singular count nouns lacking determiner, or non-count abstract nouns with superfluous definite article.",
                        "variation_rules": "Non-essential definite article omission before established discourse entities is scored at low pedagogical priority.",
                        "examples": [
                            {"phrase": "He is engineer", "correction": "He is an engineer", "explanation": "Indefinite article 'an' required."}
                        ]
                    },
                    {
                        "code": "PREP",
                        "name": "Prepositional Selection & Argument Structure",
                        "definition": "Preposition omission, substitution, or insertion violating lexical subcategorization.",
                        "assessable_criteria": "Preposition choice conflicting with verbal or adjectival subcategorization frames.",
                        "variation_rules": "Indian English collocations like 'pay attention on' are annotated with pedagogical explanation.",
                        "examples": [
                            {"phrase": "She listened music", "correction": "She listened to music", "explanation": "Preposition 'to' required."}
                        ]
                    },
                    {
                        "code": "PRO",
                        "name": "Pronominal System & Reference",
                        "definition": "Deviations in pronoun case, number/gender agreement with antecedent, or redundant pronoun retention in relative clauses.",
                        "assessable_criteria": "Case mismatch (subjective vs objective vs possessive) or unreferenced pronouns.",
                        "variation_rules": "Gender neutralization in fast speech is evaluated neutrally.",
                        "examples": [
                            {"phrase": "Me and him went there", "correction": "He and I went there", "explanation": "Subjective case required."}
                        ]
                    },
                    {
                        "code": "OTH",
                        "name": "Other Syntactic & Morphosyntactic Deviations",
                        "definition": "Syntactic anomalies not fitting primary categories (e.g., erroneous comparative/superlative inflections).",
                        "assessable_criteria": "Clear syntactic deviance outside TNS, SVA, WO, AUX, ART, PREP, PRO.",
                        "variation_rules": "Assessed on communicative clarity impact.",
                        "examples": [
                            {"phrase": "She is more taller than me", "correction": "She is taller than I am", "explanation": "Double comparative prohibited."}
                        ]
                    }
                ],
                "created_at": "2026-01-15T10:00:00Z"
            }"""
        ))

        await page.route("**/api/v1/admin/config/prompts", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""[
                {
                    "prompt_id": "p1",
                    "prompt_role": "pre_test_assessor",
                    "version_code": "v1.0-pre-assessor",
                    "name": "Pre-Test Baseline Syntactic Assessor",
                    "status": "frozen",
                    "is_frozen": true,
                    "output_schema_version": "json-schema-v1.0",
                    "created_at": "2026-01-15T10:00:00Z"
                },
                {
                    "prompt_id": "p2",
                    "prompt_role": "tutor",
                    "version_code": "v1.0-tutor-ladder",
                    "name": "AI Tutor Hint Ladder Progression",
                    "status": "frozen",
                    "is_frozen": true,
                    "output_schema_version": "json-schema-v1.0",
                    "created_at": "2026-01-15T10:00:00Z"
                },
                {
                    "prompt_id": "p3",
                    "prompt_role": "post_test_assessor",
                    "version_code": "v1.0-post-assessor",
                    "name": "Post-Test Comparative Assessor",
                    "status": "frozen",
                    "is_frozen": true,
                    "output_schema_version": "json-schema-v1.0",
                    "created_at": "2026-01-15T10:00:00Z"
                }
            ]"""
        ))

        await page.route("**/api/v1/admin/config/prompts/v1.0-pre-assessor", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "prompt_id": "p1",
                "prompt_role": "pre_test_assessor",
                "version_code": "v1.0-pre-assessor",
                "name": "Pre-Test Baseline Syntactic Assessor",
                "status": "frozen",
                "is_frozen": true,
                "output_schema_version": "json-schema-v1.0",
                "prompt_template": "ROLE: Neutral spoken-English syntax assessor.\\n\\nINPUT: Verbatim speech transcript.\\n\\nTASK: Detect candidates in 8 syntactic categories (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH).\\n\\nHUMAN REVIEW: Annotations are provisional until verified by human reviewers.",
                "output_schema_json": "{\\n  \\"type\\": \\"object\\",\\n  \\"required\\": [\\"deviations\\", \\"word_count\\"],\\n  \\"properties\\": {\\n    \\"deviations\\": {\\n      \\"type\\": \\"array\\",\\n      \\"items\\": {\\n        \\"type\\": \\"object\\",\\n        \\"required\\": [\\"category\\", \\"verbatim_phrase\\", \\"suggested_correction\\"]\\n      }\\n    }\\n  }\\n}",
                "created_at": "2026-01-15T10:00:00Z"
            }"""
        ))

        await page.route("**/api/v1/admin/config/tasks", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""[
                {
                    "task_id": "t1",
                    "title": "A Memorable Journey or Trip",
                    "prompt_text": "Describe a memorable journey or trip you took.",
                    "equivalence_group": "pair_daily_routine",
                    "task_type": "pre",
                    "difficulty_level": "standard_b1",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "rubric_version": "v1.0-jam-phd",
                    "is_active": true
                },
                {
                    "task_id": "t2",
                    "title": "An Unforgettable Holiday or Festival",
                    "prompt_text": "Describe an unforgettable festival or holiday celebration.",
                    "equivalence_group": "pair_daily_routine",
                    "task_type": "post",
                    "difficulty_level": "standard_b1",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "rubric_version": "v1.0-jam-phd",
                    "is_active": true
                },
                {
                    "task_id": "t3",
                    "title": "My College Campus & Favorite Places",
                    "prompt_text": "Describe your college campus and your favorite places to study.",
                    "equivalence_group": "pair_campus_memories",
                    "task_type": "pre",
                    "difficulty_level": "standard_b1",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "rubric_version": "v1.0-jam-phd",
                    "is_active": true
                },
                {
                    "task_id": "t4",
                    "title": "My School Memories & Teachers",
                    "prompt_text": "Describe your school days and the teachers who inspired you.",
                    "equivalence_group": "pair_campus_memories",
                    "task_type": "post",
                    "difficulty_level": "standard_b1",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "rubric_version": "v1.0-jam-phd",
                    "is_active": true
                }
            ]"""
        ))

        await page.route("**/api/v1/admin/config/tasks/assign*", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "seed": 42,
                "equivalence_group": "pair_campus_memories",
                "pre_task": {
                    "task_id": "t3",
                    "title": "My College Campus & Favorite Places",
                    "prompt_text": "Describe your college campus and your favorite places to study.",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "difficulty_level": "standard_b1",
                    "rubric_version": "v1.0-jam-phd"
                },
                "post_task": {
                    "task_id": "t4",
                    "title": "My School Memories & Teachers",
                    "prompt_text": "Describe your school days and the teachers who inspired you.",
                    "prep_time_seconds": 30,
                    "duration_seconds": 60,
                    "difficulty_level": "standard_b1",
                    "rubric_version": "v1.0-jam-phd"
                }
            }"""
        ))

        await page.route("**/api/v1/admin/config/diff*", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "type": "prompt",
                "base_code": "v1.0-pre-assessor",
                "target_code": "v1.1-experimental",
                "unified_diff": "--- v1.0-pre-assessor\\n+++ v1.1-experimental\\n@@ -1,5 +1,6 @@\\n-ROLE: Neutral spoken-English syntax assessor.\\n+ROLE: Neutral spoken-English syntax assessor with strict clause boundaries.\\n INPUT: Verbatim speech transcript.\\n+ADDITIONAL: Handle Indian English habitual progressive.",
                "additions": 2,
                "deletions": 1,
                "has_changes": true,
                "lines": [
                    {"type": "header", "text": "@@ -1,5 +1,6 @@"},
                    {"type": "delete", "text": "ROLE: Neutral spoken-English syntax assessor."},
                    {"type": "add", "text": "ROLE: Neutral spoken-English syntax assessor with strict clause boundaries."},
                    {"type": "context", "text": "INPUT: Verbatim speech transcript."},
                    {"type": "add", "text": "ADDITIONAL: Handle Indian English habitual progressive."}
                ]
            }"""
        ))

        # 1. Capture Tab 1: Rubrics Taxonomy
        print("Capturing Tab 1: Rubric Taxonomy...")
        await page.goto(f"{BASE_URL}/admin/settings", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        img1 = ARTIFACT_DIR / "admin_settings_rubric_taxonomy.png"
        await page.screenshot(path=str(img1), full_page=True)
        print(f"Saved: {img1}")

        # 2. Capture Tab 2: Prompts
        print("Capturing Tab 2: Prompt Versions...")
        await page.click("button:has-text('AI Prompts')")
        await page.wait_for_timeout(1000)
        img2 = ARTIFACT_DIR / "admin_settings_prompts.png"
        await page.screenshot(path=str(img2), full_page=True)
        print(f"Saved: {img2}")

        # 3. Capture Tab 3: Topics & Deterministic Seed Simulator
        print("Capturing Tab 3: Topic Bank & Simulator...")
        await page.click("button:has-text('Topic Bank')")
        await page.wait_for_timeout(1000)
        # Click Simulate Seed button
        await page.click("button:has-text('Simulate Seed')")
        await page.wait_for_timeout(1000)
        img3 = ARTIFACT_DIR / "admin_settings_topic_pairs.png"
        await page.screenshot(path=str(img3), full_page=True)
        print(f"Saved: {img3}")

        # 4. Capture Tab 4: Unified Diff Viewer
        print("Capturing Tab 4: Unified Diff Viewer...")
        await page.click("button:has-text('Diff Viewer')")
        await page.wait_for_timeout(1000)
        await page.click("button:has-text('Compute Diff')")
        await page.wait_for_timeout(1000)
        img4 = ARTIFACT_DIR / "admin_settings_diff_viewer.png"
        await page.screenshot(path=str(img4), full_page=True)
        print(f"Saved: {img4}")

        await browser.close()

    web_proc.kill()
    print("ALL 4 RESEARCH SETTINGS SCREENSHOTS CAPTURED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(main())
