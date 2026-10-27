"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { apiFetch } from "@/lib/api";

interface ParticipantItem {
  participant_id: string;
  research_code: string;
  study_group: "intervention" | "control";
  is_group_blinded: boolean;
  is_active: boolean;
  is_withdrawn: boolean;
  age?: number | null;
  age_band?: string | null;
  mother_tongue?: string | null;
  school_medium?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  current_consent_version?: string | null;
  consented_at?: string | null;
  withdrawn_at?: string | null;
  withdrawal_reason?: string | null;
  onboarding_completed: boolean;
  onboarding_step: string;
  created_at: string;
}

interface CSVRowValidation {
  row_number: number;
  research_code: string;
  study_group: string;
  email?: string | null;
  age?: number | null;
  is_valid: boolean;
  error_reason?: string | null;
}

interface CSVImportResult {
  dry_run: boolean;
  total_rows: number;
  valid_count: number;
  rejected_count: number;
  duplicate_count: number;
  valid_rows: CSVRowValidation[];
  rejected_rows: CSVRowValidation[];
  duplicates_found: Array<{ row_number: number; research_code: string; reason: string }>;
  can_commit: boolean;
}

export default function AdminParticipantsPage() {
  const [participants, setParticipants] = useState<ParticipantItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [studyGroupFilter, setStudyGroupFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Create Modal State
  const [createOpen, setCreateOpen] = useState<boolean>(false);
  const [newGroup, setNewGroup] = useState<string>("intervention");
  const [customCode, setCustomCode] = useState<string>("");
  const [motherTongue, setMotherTongue] = useState<string>("");
  const [schoolMedium, setSchoolMedium] = useState<string>("English");
  const [createSubmitting, setCreateSubmitting] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // CSV Import Modal State
  const [importOpen, setImportOpen] = useState<boolean>(false);
  const [csvContent, setCsvContent] = useState<string>("");
  const [importResult, setImportResult] = useState<CSVImportResult | null>(null);
  const [validatingCsv, setValidatingCsv] = useState<boolean>(false);
  const [committingImport, setCommittingImport] = useState<boolean>(false);
  const [importError, setImportError] = useState<string | null>(null);

  const fetchParticipants = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: "20",
      });
      if (search) params.append("search", search);
      if (studyGroupFilter) params.append("study_group", studyGroupFilter);
      if (statusFilter === "active") params.append("is_active", "true");
      if (statusFilter === "inactive") params.append("is_active", "false");
      if (statusFilter === "withdrawn") params.append("is_withdrawn", "true");

      const data = await apiFetch<{ items: ParticipantItem[]; total: number }>(
        `/admin/participants?${params.toString()}`
      );
      setParticipants(data.items);
      setTotalCount(data.total);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchParticipants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, studyGroupFilter, statusFilter]);

  const handleToggleStatus = async (p: ParticipantItem) => {
    try {
      await apiFetch(`/admin/participants/${p.participant_id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !p.is_active }),
      });
      fetchParticipants();
    } catch {
      // handled
    }
  };

  const handleChangeGroup = async (p: ParticipantItem, newG: "intervention" | "control") => {
    try {
      await apiFetch(`/admin/participants/${p.participant_id}/group`, {
        method: "PATCH",
        body: JSON.stringify({ study_group: newG }),
      });
      fetchParticipants();
    } catch {
      // handled
    }
  };

  const handleCreateParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      await apiFetch("/admin/participants", {
        method: "POST",
        body: JSON.stringify({
          research_code: customCode ? customCode.trim() : undefined,
          study_group: newGroup,
          mother_tongue: motherTongue.trim() || undefined,
          school_medium: schoolMedium || undefined,
        }),
      });
      setCreateOpen(false);
      setCustomCode("");
      setMotherTongue("");
      fetchParticipants();
    } catch (err: unknown) {
      const error = err as { message?: string };
      setCreateError(error.message || "Failed to create participant.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  // CSV Dry-Run Preview
  const handleValidateCsv = async () => {
    if (!csvContent.trim()) {
      setImportError("Please paste or provide CSV content.");
      return;
    }
    setValidatingCsv(true);
    setImportError(null);
    try {
      const res = await apiFetch<CSVImportResult>(
        "/admin/participants/import?dry_run=true",
        {
          method: "POST",
          body: JSON.stringify({ csv_content: csvContent }),
        }
      );
      setImportResult(res);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setImportError(error.message || "CSV validation failed.");
    } finally {
      setValidatingCsv(false);
    }
  };

  // CSV Commit Import
  const handleCommitImport = async () => {
    setCommittingImport(true);
    setImportError(null);
    try {
      await apiFetch<CSVImportResult>(
        "/admin/participants/import?dry_run=false",
        {
          method: "POST",
          body: JSON.stringify({ csv_content: csvContent }),
        }
      );
      setImportOpen(false);
      setCsvContent("");
      setImportResult(null);
      fetchParticipants();
    } catch (err: unknown) {
      const error = err as { message?: string };
      setImportError(error.message || "Failed to commit CSV import.");
    } finally {
      setCommittingImport(false);
    }
  };

  const insertSampleCsv = () => {
    setCsvContent(`research_code,study_group,email,age,mother_tongue,school_medium
SL-2026-101,intervention,learner101@syntaxlens.edu,21,Marathi,English
SL-2026-102,control,learner102@syntaxlens.edu,22,Hindi,English
SL-2026-103,intervention,learner103@syntaxlens.edu,20,Telugu,English
`);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-border bg-card px-4 sm:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-bold text-lg text-accent hover:opacity-80 transition-opacity">
            SyntaxLens
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-base font-semibold">Cohort Participants</h1>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/admin/users">
            <Button variant="outline" size="sm">Users</Button>
          </Link>
          <Link href="/admin/audit">
            <Button variant="outline" size="sm">Audit Log</Button>
          </Link>
          <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
            Bulk CSV Import
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            + Enroll Participant
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-8 space-y-6">
        {/* Controls and Search Bar */}
        <Card className="p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="w-full sm:w-72">
            <Input
              placeholder="Search by research code..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <div className="w-40">
              <Select
                value={studyGroupFilter}
                onChange={(e) => setStudyGroupFilter(e.target.value)}
                options={[
                  { value: "", label: "All Groups" },
                  { value: "intervention", label: "AI Intervention" },
                  { value: "control", label: "Control Group" },
                ]}
              />
            </div>
            <div className="w-36">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: "", label: "All Statuses" },
                  { value: "active", label: "Active" },
                  { value: "inactive", label: "Inactive" },
                  { value: "withdrawn", label: "Withdrawn" },
                ]}
              />
            </div>
          </div>
        </Card>

        {/* Participants Table */}
        <Card className="overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-muted-foreground text-sm">
              Loading participants...
            </div>
          ) : participants.length === 0 ? (
            <EmptyState
              title="No participants found"
              description="No participant records match your current filter settings."
              action={
                <Button size="sm" onClick={() => setCreateOpen(true)}>
                  Enroll Participant
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-secondary/40 border-b border-border text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="py-3 px-4">Research Code</th>
                    <th className="py-3 px-4">Study Group</th>
                    <th className="py-3 px-4">Consent Status</th>
                    <th className="py-3 px-4">Language Profile</th>
                    <th className="py-3 px-4">Onboarding</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {participants.map((p) => (
                    <tr key={p.participant_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-semibold text-foreground">
                        {p.research_code}
                      </td>
                      <td className="py-3 px-4">
                        <select
                          className="text-xs bg-secondary/50 border border-border rounded px-2 py-1 font-medium cursor-pointer"
                          value={p.study_group}
                          onChange={(e) => handleChangeGroup(p, e.target.value as "intervention" | "control")}
                        >
                          <option value="intervention">Intervention</option>
                          <option value="control">Control</option>
                        </select>
                      </td>
                      <td className="py-3 px-4">
                        {p.is_withdrawn ? (
                          <Chip variant="danger" size="sm">Withdrawn</Chip>
                        ) : p.current_consent_version ? (
                          <Chip variant="success" size="sm">Consented ({p.current_consent_version})</Chip>
                        ) : (
                          <Chip variant="warning" size="sm">Pending Consent</Chip>
                        )}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground text-xs">
                        {p.mother_tongue || "—"} &bull; {p.school_medium || "—"}
                      </td>
                      <td className="py-3 px-4">
                        {p.onboarding_completed ? (
                          <Chip variant="success" size="sm">Completed</Chip>
                        ) : (
                          <span className="text-xs text-muted-foreground capitalize">
                            {p.onboarding_step}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Chip variant={p.is_active ? "success" : "neutral"} size="sm">
                          {p.is_active ? "Active" : "Inactive"}
                        </Chip>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleStatus(p)}
                        >
                          {p.is_active ? "Deactivate" : "Activate"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="p-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <span>Total Participants: {totalCount}</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={participants.length < 20}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </Card>
      </main>

      {/* SINGLE ENROLLMENT MODAL */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Enroll New Participant</DialogTitle>
            <DialogDescription>
              Assign a unique pseudonymous research ID and designate study group allocation.
            </DialogDescription>
          </DialogHeader>

          {createError && (
            <div className="p-3 rounded bg-danger/10 text-danger text-xs border border-danger/30">
              {createError}
            </div>
          )}

          <form onSubmit={handleCreateParticipant} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1">
                Custom Research Code (optional)
              </label>
              <Input
                placeholder="Leave blank to auto-generate (e.g. SL-2026-0001)"
                value={customCode}
                onChange={(e) => setCustomCode(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Study Group Allocation</label>
              <Select
                value={newGroup}
                onChange={(e) => setNewGroup(e.target.value)}
                options={[
                  { value: "intervention", label: "AI Intervention Group" },
                  { value: "control", label: "Control Group" },
                ]}
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Mother Tongue (optional)</label>
              <Input
                placeholder="e.g. Marathi"
                value={motherTongue}
                onChange={(e) => setMotherTongue(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Medium of School Education</label>
              <Select
                value={schoolMedium}
                onChange={(e) => setSchoolMedium(e.target.value)}
                options={[
                  { value: "English", label: "English Medium" },
                  { value: "Marathi", label: "Marathi Medium" },
                  { value: "Hindi", label: "Hindi Medium" },
                  { value: "Other", label: "Other / Vernacular" },
                ]}
              />
            </div>

            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createSubmitting}>
                {createSubmitting ? "Enrolling..." : "Enroll Participant"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* BULK CSV IMPORT MODAL WITH DRY-RUN PREVIEW */}
      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Bulk CSV Participant Import</DialogTitle>
            <DialogDescription>
              Upload or paste CSV rows. Performs a dry-run validation preview before any records are committed to the study database.
            </DialogDescription>
          </DialogHeader>

          {importError && (
            <div className="p-3 rounded bg-danger/10 text-danger text-xs border border-danger/30">
              {importError}
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Columns: <code>research_code, study_group, email, age, mother_tongue, school_medium</code>
              </span>
              <button
                type="button"
                onClick={insertSampleCsv}
                className="text-xs text-accent underline hover:opacity-80"
              >
                Insert Sample Template
              </button>
            </div>

            <textarea
              className="w-full h-36 font-mono text-xs p-3 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="Paste CSV text here..."
              value={csvContent}
              onChange={(e) => {
                setCsvContent(e.target.value);
                setImportResult(null);
              }}
            />

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleValidateCsv}
                disabled={validatingCsv || !csvContent.trim()}
              >
                {validatingCsv ? "Validating..." : "Validate CSV (Dry Run Preview)"}
              </Button>
            </div>

            {/* DRY-RUN PREVIEW CARD */}
            {importResult && (
              <div className="p-4 rounded-lg border border-border bg-secondary/20 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-border">
                  <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                    Dry Run Validation Summary
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    Total: {importResult.total_rows} rows
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded bg-success/10 border border-success/20 text-success">
                    <span className="font-bold text-sm block">{importResult.valid_count}</span>
                    Valid Rows
                  </div>
                  <div className="p-2 rounded bg-danger/10 border border-danger/20 text-danger">
                    <span className="font-bold text-sm block">{importResult.rejected_count}</span>
                    Rejected Rows
                  </div>
                  <div className="p-2 rounded bg-warning/10 border border-warning/20 text-warning">
                    <span className="font-bold text-sm block">{importResult.duplicate_count}</span>
                    Duplicates Detected
                  </div>
                </div>

                {/* Validation Rows Table */}
                <div className="max-h-48 overflow-y-auto border border-border rounded text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-secondary/40 text-[11px] text-muted-foreground uppercase">
                      <tr>
                        <th className="p-2">Row</th>
                        <th className="p-2">Code</th>
                        <th className="p-2">Group</th>
                        <th className="p-2">Status</th>
                        <th className="p-2">Note / Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {importResult.valid_rows.map((r) => (
                        <tr key={`v-${r.row_number}`} className="bg-success/5">
                          <td className="p-2 font-mono">{r.row_number}</td>
                          <td className="p-2 font-mono font-medium">{r.research_code}</td>
                          <td className="p-2 capitalize">{r.study_group}</td>
                          <td className="p-2 text-success font-semibold">&#10003; Valid</td>
                          <td className="p-2 text-muted-foreground">Ready to commit</td>
                        </tr>
                      ))}
                      {importResult.rejected_rows.map((r) => (
                        <tr key={`r-${r.row_number}`} className="bg-danger/5">
                          <td className="p-2 font-mono">{r.row_number}</td>
                          <td className="p-2 font-mono font-medium">{r.research_code}</td>
                          <td className="p-2 capitalize">{r.study_group}</td>
                          <td className="p-2 text-danger font-semibold">&times; Rejected</td>
                          <td className="p-2 text-danger">{r.error_reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!importResult || importResult.valid_count === 0 || committingImport}
              onClick={handleCommitImport}
            >
              {committingImport ? "Committing Import..." : `Commit Import (${importResult?.valid_count || 0} Participants)`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
