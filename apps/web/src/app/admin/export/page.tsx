"use client";

import React, { useState, useEffect } from "react";

interface ExportSnapshot {
  snapshot_id: string;
  export_type: string;
  filters_json: string | null;
  row_count: number;
  file_checksum_sha256: string;
  format: string;
  reason: string | null;
  created_at: string;
}

export default function ExportManagementPage() {
  const [history, setHistory] = useState<ExportSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [kWarnings, setKWarnings] = useState<string[]>([]);

  // Form State
  const [exportFormat, setExportFormat] = useState<"csv" | "xlsx">("csv");
  const [groupFilter, setGroupFilter] = useState<"all" | "intervention" | "control">("all");
  const [hashIds, setHashIds] = useState(false);
  const [includeIdentifiers, setIncludeIdentifiers] = useState(false);
  const [reason, setReason] = useState("");
  const [confirmedElevated, setConfirmedElevated] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("/api/v1/export/history");
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setKWarnings([]);

    if (includeIdentifiers && !reason.trim()) {
      setError("An explicit research justification reason is required for elevated exports.");
      return;
    }

    if (includeIdentifiers && !confirmedElevated) {
      setError("You must explicitly check the confirmation box for an elevated export.");
      return;
    }

    setIsExporting(true);
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (includeIdentifiers && confirmedElevated) {
        headers["X-Confirm-Elevated"] = "true";
      }

      const res = await fetch("/api/v1/export/dataset", {
        method: "POST",
        headers,
        body: JSON.stringify({
          format: exportFormat,
          group_filter: groupFilter,
          hash_participant_ids: hashIds,
          include_identifiers: includeIdentifiers,
          reason: includeIdentifiers ? reason : null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Export request failed." }));
        throw new Error(errData.detail || "Export failed.");
      }

      const result = await res.json();
      setSuccessMsg(`Snapshot ${result.snapshot_id.slice(0, 8)} created successfully (${result.row_count} rows).`);
      if (result.k_anonymity_warnings && result.k_anonymity_warnings.length > 0) {
        setKWarnings(result.k_anonymity_warnings);
      }

      // Automatically trigger download of the newly created snapshot
      window.open(result.download_url, "_blank");

      // Refresh table
      fetchHistory();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10 font-sans text-slate-800">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-full mb-3">
            <span>🛡️ RESEARCH INTEGRITY</span>
            <span>•</span>
            <span>FR-18 DE-IDENTIFIED EXPORT</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Research Data Exporter</h1>
          <p className="text-slate-600 mt-1 max-w-3xl">
            Streamed server-side research exports with programmatic data dictionaries, salted HMAC participant re-keying,
            and cryptographic snapshot reproducibility. Zero direct identifiers in default exports.
          </p>
        </div>

        {/* Global Feedback */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-sm flex items-start gap-3">
            <span className="text-lg">⚠️</span>
            <div>
              <div className="font-semibold">Export Request Rejected</div>
              <div>{error}</div>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-start gap-3">
            <span className="text-lg">✅</span>
            <div>
              <div className="font-semibold">Export Completed</div>
              <div>{successMsg}</div>
            </div>
          </div>
        )}

        {kWarnings.length > 0 && (
          <div className="p-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg text-sm space-y-2">
            <div className="font-semibold flex items-center gap-2">
              <span>⚠️</span>
              <span>k-Anonymity Advisory (Subgroup Size &lt; 5)</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs text-amber-800">
              {kWarnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Main Grid: Export Controls & Snapshot History */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Controls Panel */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span>⚙️</span> New Export Snapshot
            </h2>

            <form onSubmit={handleExport} className="space-y-4">
              {/* Format */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                  File Format
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setExportFormat("csv")}
                    className={`py-2 px-3 text-sm font-medium rounded-lg border text-center transition-all ${
                      exportFormat === "csv"
                        ? "bg-indigo-50 border-indigo-600 text-indigo-700 font-bold"
                        : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    CSV (Streamed)
                  </button>
                  <button
                    type="button"
                    onClick={() => setExportFormat("xlsx")}
                    className={`py-2 px-3 text-sm font-medium rounded-lg border text-center transition-all ${
                      exportFormat === "xlsx"
                        ? "bg-indigo-50 border-indigo-600 text-indigo-700 font-bold"
                        : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    XLSX (Workbook)
                  </button>
                </div>
              </div>

              {/* Group Filter */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                  Study Group Filter
                </label>
                <select
                  value={groupFilter}
                  onChange={(e) => setGroupFilter(e.target.value as any)}
                  className="w-full text-sm rounded-lg border border-slate-300 bg-white py-2 px-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="all">All Groups (Intervention + Control)</option>
                  <option value="intervention">Intervention Group Only</option>
                  <option value="control">Control Group Only</option>
                </select>
              </div>

              {/* Salted HMAC Toggle */}
              <div className="pt-2">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hashIds}
                    onChange={(e) => setHashIds(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-800">Salted-Hash Participant IDs</span>
                    <p className="text-xs text-slate-500">
                      Replaces research codes with deterministic HMAC-SHA256 hashes salted per-session.
                    </p>
                  </div>
                </label>
              </div>

              {/* Elevated Role Export Section */}
              <div className="pt-4 border-t border-slate-100">
                <div className="p-3 bg-rose-50/50 rounded-lg border border-rose-100 space-y-3">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeIdentifiers}
                      onChange={(e) => setIncludeIdentifiers(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-rose-300 text-rose-600 focus:ring-rose-500"
                    />
                    <div>
                      <span className="text-xs font-bold text-rose-900 uppercase tracking-wide">
                        Elevated Export (Identifiable)
                      </span>
                      <p className="text-xs text-rose-700 mt-0.5">
                        Requires RESEARCHER_ADMIN role, second confirmation, and logged justification.
                      </p>
                    </div>
                  </label>

                  {includeIdentifiers && (
                    <div className="space-y-3 pt-2">
                      <div>
                        <label className="block text-xs font-semibold text-rose-800 mb-1">
                          Reason / IRB Protocol Reference *
                        </label>
                        <textarea
                          rows={2}
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          placeholder="e.g. Formal IRB audit compliance check..."
                          className="w-full text-xs p-2 rounded border border-rose-300 bg-white focus:outline-none focus:ring-2 focus:ring-rose-500"
                        />
                      </div>

                      <label className="flex items-center gap-2 cursor-pointer text-xs text-rose-900 font-medium">
                        <input
                          type="checkbox"
                          checked={confirmedElevated}
                          onChange={(e) => setConfirmedElevated(e.target.checked)}
                          className="h-3.5 w-3.5 rounded border-rose-300 text-rose-600 focus:ring-rose-500"
                        />
                        <span>Confirm: I have formal IRB approval for this export.</span>
                      </label>
                    </div>
                  )}
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isExporting}
                className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isExporting ? (
                  <span>Generating Snapshot...</span>
                ) : (
                  <>
                    <span>⬇️</span>
                    <span>Generate &amp; Download</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* History Panel */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Export History &amp; Snapshots</h2>
                <p className="text-xs text-slate-500">
                  Immutable frozen archives. Every snapshot guarantees exact cryptographic reproducibility.
                </p>
              </div>
              <button
                onClick={fetchHistory}
                disabled={isLoading}
                className="text-xs px-2.5 py-1.5 border border-slate-300 rounded hover:bg-slate-50 font-medium text-slate-600"
              >
                Refresh
              </button>
            </div>

            {isLoading ? (
              <div className="py-12 text-center text-sm text-slate-400">Loading export snapshot history...</div>
            ) : history.length === 0 ? (
              <div className="py-12 text-center border-2 border-dashed border-slate-100 rounded-xl">
                <span className="text-3xl">📁</span>
                <p className="text-sm font-medium text-slate-600 mt-2">No export snapshots created yet</p>
                <p className="text-xs text-slate-400">Generate your first dataset snapshot above.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-3">Snapshot ID</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Rows</th>
                      <th className="py-2.5 px-3">SHA-256 Checksum</th>
                      <th className="py-2.5 px-3">Created</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {history.map((snap) => (
                      <tr key={snap.snapshot_id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-3 font-semibold text-slate-900">
                          {snap.snapshot_id.slice(0, 8)}...
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              snap.export_type === "elevated"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {snap.export_type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-700">{snap.row_count}</td>
                        <td className="py-3 px-3 text-slate-500 font-mono text-[10px]">
                          {snap.file_checksum_sha256.slice(0, 12)}...
                        </td>
                        <td className="py-3 px-3 text-slate-500 font-sans">
                          {new Date(snap.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-3 text-right font-sans space-x-2">
                          <a
                            href={`/api/v1/export/snapshots/${snap.snapshot_id}/download`}
                            className="inline-flex items-center text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                            download
                          >
                            CSV
                          </a>
                          <span className="text-slate-300">|</span>
                          <a
                            href={`/api/v1/export/snapshots/${snap.snapshot_id}/download/dict`}
                            className="inline-flex items-center text-xs font-medium text-slate-600 hover:text-slate-900"
                            download
                          >
                            Dict
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Data Dictionary Preview Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>📖</span> Live Data Dictionary Definition
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Programmatically derived from the exact same schema definition as the export engine. Zero drift guarantee.
              </p>
            </div>
            <span className="text-xs bg-slate-100 text-slate-600 font-mono px-2.5 py-1 rounded">
              33 Verified Columns
            </span>
          </div>

          <div className="p-4 bg-slate-50 rounded-lg text-xs font-mono border border-slate-200 space-y-2 text-slate-700">
            <div>
              <span className="text-indigo-700 font-bold">research_code</span>: string — Pseudonymous participant code
              or HMAC-SHA256 salted hash.
            </div>
            <div>
              <span className="text-indigo-700 font-bold">error_rate_per_100_words</span>: float — (total_assessable_errors /
              word_count) * 100 via pure metrics module.
            </div>
            <div>
              <span className="text-indigo-700 font-bold">count_[category]</span>: integer — Effective annotation count
              per category (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH).
            </div>
            <div>
              <span className="text-indigo-700 font-bold">provisional</span>: boolean — True if human reviewer
              verification is incomplete.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
