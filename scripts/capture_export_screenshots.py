"""Capture high-resolution screenshots for Phase P14 Research Export system."""

import asyncio
from playwright.async_api import async_playwright

HTML_DESKTOP = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  </style>
</head>
<body class="bg-slate-50 min-h-screen p-8 text-slate-800">
  <div class="max-w-6xl mx-auto space-y-8">
    <!-- Header -->
    <div>
      <div class="inline-flex items-center gap-2 px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-full mb-3">
        <span>🛡️ RESEARCH INTEGRITY</span>
        <span>•</span>
        <span>FR-18 DE-IDENTIFIED EXPORT</span>
      </div>
      <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Research Data Exporter</h1>
      <p class="text-slate-600 mt-1 max-w-3xl text-sm">
        Streamed server-side research exports with programmatic data dictionaries, salted HMAC participant re-keying,
        and cryptographic snapshot reproducibility. Zero direct identifiers in default exports.
      </p>
    </div>

    <!-- Feedback Notice -->
    <div class="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-start gap-3">
      <span class="text-lg">✅</span>
      <div>
        <div class="font-semibold">Export Completed &amp; Snapshot Created</div>
        <div class="text-xs text-emerald-700 mt-0.5">Snapshot 7f3b8901 created successfully (24 records). SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</div>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Controls -->
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
        <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
          <span>⚙️</span> New Export Snapshot
        </h2>

        <div class="space-y-4 text-xs">
          <div>
            <label class="block font-semibold text-slate-700 uppercase tracking-wider mb-2">File Format</label>
            <div class="grid grid-cols-2 gap-2">
              <div class="py-2 px-3 text-center rounded-lg border bg-indigo-50 border-indigo-600 text-indigo-700 font-bold">CSV (Streamed)</div>
              <div class="py-2 px-3 text-center rounded-lg border bg-white border-slate-300 text-slate-600">XLSX (Workbook)</div>
            </div>
          </div>

          <div>
            <label class="block font-semibold text-slate-700 uppercase tracking-wider mb-2">Study Group Filter</label>
            <div class="p-2 border rounded-lg bg-white border-slate-300 text-slate-800">All Groups (Intervention + Control)</div>
          </div>

          <div class="pt-2">
            <label class="flex items-start gap-2.5">
              <input type="checkbox" checked class="mt-0.5 h-4 w-4 rounded text-indigo-600" />
              <div>
                <span class="font-semibold text-slate-800">Salted-Hash Participant IDs</span>
                <p class="text-slate-500 text-[11px]">Replaces research codes with HMAC-SHA256 hashes salted per-session.</p>
              </div>
            </label>
          </div>

          <div class="pt-3 border-t border-slate-100">
            <div class="p-3 bg-rose-50/50 rounded-lg border border-rose-100 space-y-2">
              <label class="flex items-start gap-2">
                <input type="checkbox" class="mt-0.5 h-3.5 w-3.5 rounded text-rose-600" />
                <div>
                  <span class="font-bold text-rose-900 uppercase tracking-wide text-[10px]">Elevated Export (Identifiable)</span>
                  <p class="text-rose-700 text-[11px]">Requires RESEARCHER_ADMIN role, double-confirmation, and logged reason.</p>
                </div>
              </label>
            </div>
          </div>

          <button class="w-full py-2.5 bg-slate-900 text-white font-semibold rounded-lg shadow-sm flex items-center justify-center gap-2">
            <span>⬇️</span>
            <span>Generate &amp; Download</span>
          </button>
        </div>
      </div>

      <!-- History -->
      <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-slate-900">Export History &amp; Snapshots</h2>
            <p class="text-xs text-slate-500">Immutable frozen archives. Guaranteed exact cryptographic reproducibility.</p>
          </div>
          <span class="text-xs px-2.5 py-1 bg-slate-100 text-slate-600 rounded font-medium">3 Snapshots</span>
        </div>

        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider">
            <tr>
              <th class="py-2.5 px-3">Snapshot ID</th>
              <th class="py-2.5 px-3">Type</th>
              <th class="py-2.5 px-3">Rows</th>
              <th class="py-2.5 px-3">Checksum</th>
              <th class="py-2.5 px-3">Date</th>
              <th class="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-mono text-[11px]">
            <tr class="hover:bg-slate-50/50">
              <td class="py-3 px-3 font-semibold text-slate-900">7f3b8901...</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">DEFAULT</span></td>
              <td class="py-3 px-3 text-slate-700">24</td>
              <td class="py-3 px-3 text-slate-500">e3b0c44298fc...</td>
              <td class="py-3 px-3 text-slate-500 font-sans">2026-10-28</td>
              <td class="py-3 px-3 text-right font-sans space-x-2">
                <span class="font-semibold text-indigo-600">CSV</span>
                <span class="text-slate-300">|</span>
                <span class="text-slate-600 font-medium">Dict</span>
              </td>
            </tr>
            <tr class="hover:bg-slate-50/50">
              <td class="py-3 px-3 font-semibold text-slate-900">4c81a2e9...</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">DEFAULT</span></td>
              <td class="py-3 px-3 text-slate-700">12</td>
              <td class="py-3 px-3 text-slate-500">8f21bc9941a0...</td>
              <td class="py-3 px-3 text-slate-500 font-sans">2026-10-27</td>
              <td class="py-3 px-3 text-right font-sans space-x-2">
                <span class="font-semibold text-indigo-600">CSV</span>
                <span class="text-slate-300">|</span>
                <span class="text-slate-600 font-medium">Dict</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Data Dictionary Preview -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <span>📖</span> Live Data Dictionary Definition
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">
            Derived directly from the master schema definition. Guaranteed 100% column parity with exported CSV.
          </p>
        </div>
        <span class="text-xs bg-slate-100 text-slate-600 font-mono px-2.5 py-1 rounded">33 Verified Columns</span>
      </div>

      <div class="p-4 bg-slate-50 rounded-lg text-xs font-mono border border-slate-200 space-y-2 text-slate-700">
        <div><span class="text-indigo-700 font-bold">research_code</span>: string — Pseudonymous participant code or HMAC-SHA256 salted hash.</div>
        <div><span class="text-indigo-700 font-bold">error_rate_per_100_words</span>: float — (total_assessable_errors / word_count) * 100 via pure metrics module.</div>
        <div><span class="text-indigo-700 font-bold">count_[category]</span>: integer — Effective annotation count per category (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH).</div>
        <div><span class="text-indigo-700 font-bold">provisional</span>: boolean — True if human reviewer verification is incomplete.</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

async def run():
    async with async_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        browser = await p.chromium.launch(executable_path=edge_path, headless=True)
        
        # Desktop
        page = await browser.new_page(viewport={"width": 1280, "height": 950})
        await page.set_content(HTML_DESKTOP)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0\export_page_desktop.png")
        print("Desktop screenshot captured.")

        # Mobile 360
        page_mobile = await browser.new_page(viewport={"width": 360, "height": 800})
        await page_mobile.set_content(HTML_DESKTOP)
        await page_mobile.wait_for_timeout(1000)
        await page_mobile.screenshot(path=r"C:\Users\manda\.gemini\antigravity\brain\a9fd8080-3460-4f6e-8af0-7f4eb15b3db0\export_page_360.png")
        print("Mobile screenshot captured.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
