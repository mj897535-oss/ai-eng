"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Button,
  Select,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Chip,
  Card,
  CardContent,
  EmptyState,
} from "@/components/ui";
import { apiFetch, AuditLogItem, PaginatedResponse } from "@/lib/api";

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(25);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [selectedAction, setSelectedAction] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedOutcome, setSelectedOutcome] = useState("");
  const [actionList, setActionList] = useState<string[]>([]);
  const [roleList, setRoleList] = useState<string[]>([]);

  // Fetch audit logs
  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
      });
      if (selectedAction) params.set("action", selectedAction);
      if (selectedRole) params.set("role", selectedRole);
      if (selectedOutcome) params.set("outcome", selectedOutcome);

      const res = await apiFetch<PaginatedResponse<AuditLogItem>>(`/admin/audit-logs?${params.toString()}`);
      setLogs(res.items);
      setTotal(res.total);
      if (res.distinct_actions) setActionList(res.distinct_actions);
      if (res.distinct_roles) setRoleList(res.distinct_roles);
    } catch (err: any) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, selectedAction, selectedRole, selectedOutcome]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* Top Academic Navigation Bar */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-3 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-serif flex items-center justify-center font-bold">
              S
            </div>
            <span className="font-semibold text-lg tracking-tight">SyntaxLens</span>
            <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-mono">
              Researcher Admin
            </span>
          </div>

          <nav className="flex items-center gap-6 text-sm font-medium">
            <a href="/admin/users" className="text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400">
              Users & Cohort
            </a>
            <a href="/admin/audit" className="text-indigo-600 dark:text-indigo-400 font-semibold border-b-2 border-indigo-600 pb-1">
              Audit Trail
            </a>
            <a href="/design" className="text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400">
              Design System
            </a>
            <button
              onClick={() => {
                apiFetch("/auth/logout", { method: "POST" }).finally(() => {
                  window.location.href = "/login";
                });
              }}
              className="text-xs text-rose-600 dark:text-rose-400 hover:underline"
            >
              Sign Out
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">Research Provenance & Audit Trail</h1>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                Append-Only Verified
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Non-negotiable PhD empirical audit log. Every authentication, submission, review decision, and audio access is permanently recorded.
            </p>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            {total} total event records
          </div>
        </div>

        {/* Filter Controls Card */}
        <Card className="mb-6 border-slate-200 dark:border-slate-800">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <Select
                  label="Filter by Action"
                  value={selectedAction}
                  onChange={(e) => {
                    setSelectedAction(e.target.value);
                    setOffset(0);
                  }}
                  options={[
                    { value: "", label: "All Recorded Actions" },
                    ...actionList.map((a) => ({ value: a, label: a })),
                  ]}
                />
              </div>

              <div>
                <Select
                  label="Filter by Role"
                  value={selectedRole}
                  onChange={(e) => {
                    setSelectedRole(e.target.value);
                    setOffset(0);
                  }}
                  options={[
                    { value: "", label: "All Roles" },
                    ...roleList.map((r) => ({ value: r, label: r })),
                  ]}
                />
              </div>

              <div>
                <Select
                  label="Outcome Status"
                  value={selectedOutcome}
                  onChange={(e) => {
                    setSelectedOutcome(e.target.value);
                    setOffset(0);
                  }}
                  options={[
                    { value: "", label: "All Outcomes" },
                    { value: "success", label: "Success Only" },
                    { value: "failure", label: "Failure Only" },
                  ]}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Audit Log Table */}
        <Card className="border-slate-200 dark:border-slate-800 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">Retrieving audit events...</div>
          ) : logs.length === 0 ? (
            <EmptyState
              title="No audit entries found"
              description="No security or research events match the current filter selection."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelectedAction("");
                    setSelectedRole("");
                    setSelectedOutcome("");
                    setOffset(0);
                  }}
                >
                  Clear Filters
                </Button>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp (UTC)</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Record Type</TableHead>
                  <TableHead>Record ID</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>IP Hash</TableHead>
                  <TableHead>Context</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.log_id}>
                    <TableCell className="font-mono text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {new Date(log.timestamp).toISOString().replace("T", " ").substring(0, 19)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        variant={
                          log.action.includes("failure") || log.outcome === "failure"
                            ? "danger"
                            : log.action.includes("admin") || log.action.includes("created")
                            ? "primary"
                            : "neutral"
                        }
                      >
                        {log.action}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        {log.role || "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {log.record_type}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-500 max-w-[120px] truncate" title={log.record_id}>
                      {log.record_id}
                    </TableCell>
                    <TableCell>
                      <Chip variant={log.outcome === "success" ? "success" : "danger"}>
                        {log.outcome}
                      </Chip>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">
                      {log.ip_hash ? `${log.ip_hash.substring(0, 10)}…` : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 max-w-[200px] truncate" title={log.details || ""}>
                      {log.details || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination Controls */}
          {total > limit && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
              <span className="text-xs text-slate-500">
                Page {currentPage} of {totalPages} ({total} events)
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset + limit >= total}
                  onClick={() => setOffset(offset + limit)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}
