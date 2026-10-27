"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { apiFetch } from "@/lib/api";

interface RubricCategory {
  code: string;
  name: string;
  definition: string;
  assessable_criteria: string;
  variation_rules: string;
  is_expanded?: boolean;
  examples?: Array<{ phrase: string; correction: string; explanation?: string }>;
}

interface RubricItem {
  rubric_id: string;
  version_code: string;
  name: string;
  description?: string | null;
  status: "draft" | "approved" | "frozen";
  is_frozen: boolean;
  approved_at?: string | null;
  frozen_at?: string | null;
  category_count: number;
  created_at: string;
}

interface RubricDetail extends RubricItem {
  categories: RubricCategory[];
  counting_rules: string;
  word_counting_rules: string;
  change_notes?: string | null;
}

interface PromptItem {
  prompt_id: string;
  prompt_role: "pre_test_assessor" | "tutor" | "post_test_assessor";
  version_code: string;
  name: string;
  status: "draft" | "approved" | "frozen";
  is_frozen: boolean;
  output_schema_version: string;
  created_at: string;
}

interface PromptDetail extends PromptItem {
  prompt_template: string;
  output_schema_json: string;
  change_notes?: string | null;
}

interface TaskItem {
  task_id: string;
  title: string;
  prompt_text: string;
  equivalence_group: string;
  task_type: string;
  difficulty_level: string;
  prep_time_seconds: number;
  duration_seconds: number;
  rubric_version: string;
  is_active: boolean;
}

interface PeriodItem {
  period_id: string;
  period_code: string;
  name: string;
  description?: string | null;
  rubric_version_code: string;
  pre_prompt_version_code: string;
  tutor_prompt_version_code: string;
  post_prompt_version_code: string;
  status: string;
  is_frozen: boolean;
  is_active: boolean;
  start_date: string;
}

interface DiffLine {
  type: "add" | "delete" | "header" | "context";
  text: string;
}

interface DiffResult {
  type: string;
  base_code: string;
  target_code: string;
  unified_diff: string;
  additions: number;
  deletions: number;
  has_changes: boolean;
  lines: DiffLine[];
}

export default function ResearchSettingsPage() {
  const [activeTab, setActiveTab] = useState<string>("rubrics");

  // Rubrics state
  const [rubrics, setRubrics] = useState<RubricItem[]>([]);
  const [selectedRubric, setSelectedRubric] = useState<RubricDetail | null>(null);
  const [loadingRubrics, setLoadingRubrics] = useState<boolean>(true);

  // Prompts state
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [loadingPrompts, setLoadingPrompts] = useState<boolean>(false);

  // Topics state
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loadingTasks, setLoadingTasks] = useState<boolean>(false);
  const [testParticipantId, setTestParticipantId] = useState<string>("SL-2026-0001");
  const [testSeed, setTestSeed] = useState<string>("42");
  const [assignmentResult, setAssignmentResult] = useState<any | null>(null);
  const [assigning, setAssigning] = useState<boolean>(false);

  // Periods state
  const [periods, setPeriods] = useState<PeriodItem[]>([]);
  const [loadingPeriods, setLoadingPeriods] = useState<boolean>(false);

  // Diff state
  const [diffType, setDiffType] = useState<string>("rubric");
  const [baseCode, setBaseCode] = useState<string>("v1.0-jam-phd");
  const [targetCode, setTargetCode] = useState<string>("v1.0-jam-phd");
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [diffLoading, setDiffLoading] = useState<boolean>(false);

  // Freeze Modal State
  const [freezeModalOpen, setFreezeModalOpen] = useState<boolean>(false);
  const [itemToFreeze, setItemToFreeze] = useState<{ type: string; code: string } | null>(null);
  const [freezeSubmitting, setFreezeSubmitting] = useState<boolean>(false);

  // Initial load
  useEffect(() => {
    fetchRubrics();
  }, []);

  const fetchRubrics = async () => {
    setLoadingRubrics(true);
    try {
      const data = await apiFetch<RubricItem[]>("/api/v1/admin/config/rubrics");
      setRubrics(data);
      if (data.length > 0 && data[0]) {
        fetchRubricDetail(data[0].version_code);
      }
    } catch (e) {
      console.error("Failed to load rubrics", e);
    } finally {
      setLoadingRubrics(false);
    }
  };

  const fetchRubricDetail = async (code: string) => {
    try {
      const detail = await apiFetch<RubricDetail>(`/api/v1/admin/config/rubrics/${code}`);
      setSelectedRubric(detail);
    } catch (e) {
      console.error("Failed to load rubric detail", e);
    }
  };

  const fetchPrompts = async () => {
    setLoadingPrompts(true);
    try {
      const data = await apiFetch<PromptItem[]>("/api/v1/admin/config/prompts");
      setPrompts(data);
      if (data.length > 0 && data[0]) {
        fetchPromptDetail(data[0].version_code);
      }
    } catch (e) {
      console.error("Failed to load prompts", e);
    } finally {
      setLoadingPrompts(false);
    }
  };

  const fetchPromptDetail = async (code: string) => {
    try {
      const detail = await apiFetch<PromptDetail>(`/api/v1/admin/config/prompts/${code}`);
      setSelectedPrompt(detail);
    } catch (e) {
      console.error("Failed to load prompt detail", e);
    }
  };

  const fetchTasks = async () => {
    setLoadingTasks(true);
    try {
      const data = await apiFetch<TaskItem[]>("/api/v1/admin/config/tasks");
      setTasks(data);
    } catch (e) {
      console.error("Failed to load tasks", e);
    } finally {
      setLoadingTasks(false);
    }
  };

  const fetchPeriods = async () => {
    setLoadingPeriods(true);
    try {
      const data = await apiFetch<PeriodItem[]>("/api/v1/admin/config/periods");
      setPeriods(data);
    } catch (e) {
      console.error("Failed to load periods", e);
    } finally {
      setLoadingPeriods(false);
    }
  };

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    if (tabId === "rubrics" && rubrics.length === 0) fetchRubrics();
    if (tabId === "prompts" && prompts.length === 0) fetchPrompts();
    if (tabId === "topics" && tasks.length === 0) fetchTasks();
    if (tabId === "periods" && periods.length === 0) fetchPeriods();
  };

  const handleTestAssignment = async () => {
    setAssigning(true);
    try {
      const res = await apiFetch<any>(
        `/api/v1/admin/config/tasks/assign?participant_id=${encodeURIComponent(testParticipantId)}&seed=${testSeed}`
      );
      setAssignmentResult(res);
    } catch (e: any) {
      alert("Assignment error: " + (e?.message || "Failed"));
    } finally {
      setAssigning(false);
    }
  };

  const handleRunDiff = async () => {
    setDiffLoading(true);
    try {
      const res = await apiFetch<DiffResult>(
        `/api/v1/admin/config/diff?type=${diffType}&base_code=${baseCode}&target_code=${targetCode}`
      );
      setDiffResult(res);
    } catch (e: any) {
      alert("Diff error: " + (e?.message || "Failed"));
    } finally {
      setDiffLoading(false);
    }
  };

  const handleFreezeConfirm = async () => {
    if (!itemToFreeze) return;
    setFreezeSubmitting(true);
    try {
      if (itemToFreeze.type === "rubric") {
        await apiFetch(`/api/v1/admin/config/rubrics/${itemToFreeze.code}/freeze`, { method: "POST" });
        await fetchRubrics();
      } else if (itemToFreeze.type === "prompt") {
        await apiFetch(`/api/v1/admin/config/prompts/${itemToFreeze.code}/freeze`, { method: "POST" });
        await fetchPrompts();
      }
      setFreezeModalOpen(false);
      setItemToFreeze(null);
    } catch (e: any) {
      alert("Freeze failed: " + (e?.message || "Unknown error"));
    } finally {
      setFreezeSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      {/* Top Banner Navigation */}
      <div className="max-w-7xl mx-auto mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
            <Link href="/admin/users" className="hover:underline">Researchers</Link>
            <span>/</span>
            <Link href="/admin/participants" className="hover:underline">Participants</Link>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-200 font-medium">Research Settings</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Versioned Research Configuration
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Strictly immutable, version-controlled scoring rubrics, AI prompt templates, topic banks, and assessment periods (SRS FR-05, FR-08, FR-20).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/admin/audit">
            <Button variant="outline" size="sm">Audit Log</Button>
          </Link>
          <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs px-3 py-1.5 rounded-md font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Active Period: period-2026-spring (Frozen)
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto">
        {/* Navigation Tabs */}
        <div className="mb-6">
          <Tabs value={activeTab} onValueChange={handleTabChange}>
            <TabsList className="grid grid-cols-2 sm:grid-cols-5 w-full">
              <TabsTrigger value="rubrics">Rubrics (8 Cats)</TabsTrigger>
              <TabsTrigger value="prompts">AI Prompts (3 Roles)</TabsTrigger>
              <TabsTrigger value="topics">Topic Bank Pairs</TabsTrigger>
              <TabsTrigger value="periods">Study Periods</TabsTrigger>
              <TabsTrigger value="diff">Diff Viewer</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* --- TAB 1: RUBRIC TAXONOMY --- */}
        {activeTab === "rubrics" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Rubrics List Sidebar */}
            <Card className="p-4 lg:col-span-1">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold">Rubric Versions</h2>
                <Chip variant="neutral" size="sm">{rubrics.length} Available</Chip>
              </div>

              {loadingRubrics ? (
                <div className="py-8 text-center text-sm text-slate-500">Loading rubrics...</div>
              ) : (
                <div className="space-y-2">
                  {rubrics.map((r) => (
                    <button
                      key={r.version_code}
                      onClick={() => fetchRubricDetail(r.version_code)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        selectedRubric?.version_code === r.version_code
                          ? "border-sky-500 bg-sky-50/60 dark:bg-sky-950/30 ring-1 ring-sky-500"
                          : "border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-sky-700 dark:text-sky-300">
                          {r.version_code}
                        </span>
                        <Chip
                          variant={r.is_frozen ? "primary" : "warning"}
                          size="sm"
                        >
                          {r.is_frozen ? "Frozen (Immutable)" : "Draft"}
                        </Chip>
                      </div>
                      <div className="text-sm font-medium mt-1 truncate">{r.name}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center justify-between">
                        <span>{r.category_count} Categories</span>
                        <span>{new Date(r.created_at).toLocaleDateString()}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Card>

            {/* Rubric Details & Categories */}
            <div className="lg:col-span-2 space-y-6">
              {selectedRubric ? (
                <>
                  <Card className="p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold font-serif">{selectedRubric.name}</h2>
                          <Chip variant={selectedRubric.is_frozen ? "primary" : "warning"}>
                            {selectedRubric.is_frozen ? "Frozen & Immutable" : "Draft"}
                          </Chip>
                        </div>
                        <p className="text-xs font-mono text-slate-500 mt-1">
                          Version Code: {selectedRubric.version_code} | Approved: {selectedRubric.approved_at ? new Date(selectedRubric.approved_at).toLocaleDateString() : "Pending"}
                        </p>
                      </div>

                      {!selectedRubric.is_frozen && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setItemToFreeze({ type: "rubric", code: selectedRubric.version_code });
                            setFreezeModalOpen(true);
                          }}
                        >
                          Permanently Freeze Rubric
                        </Button>
                      )}
                    </div>

                    {/* Research Immutability Guarantee Banner */}
                    {selectedRubric.is_frozen && (
                      <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-md text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2">
                        <span className="font-bold text-amber-600 dark:text-amber-400">RESEARCH INTEGRITY:</span>
                        <span>This rubric version is permanently frozen. Database triggers strictly prevent any UPDATE or DELETE operations. Any methodological modification requires creating a new version.</span>
                      </div>
                    )}

                    {/* Counting Rules */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                      <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                          Counting Rules
                        </h3>
                        <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                          {selectedRubric.counting_rules}
                        </p>
                      </div>

                      <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                          Word Counting Rules
                        </h3>
                        <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                          {selectedRubric.word_counting_rules}
                        </p>
                      </div>
                    </div>
                  </Card>

                  {/* Categories Taxonomy Cards */}
                  <div>
                    <h3 className="text-base font-semibold mb-3">
                      Taxonomy Categories ({selectedRubric.categories.length})
                    </h3>
                    <div className="grid grid-cols-1 gap-4">
                      {selectedRubric.categories.map((cat) => (
                        <Card key={cat.code} className="p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold px-2 py-1 bg-slate-200 dark:bg-slate-800 rounded">
                                {cat.code}
                              </span>
                              <h4 className="text-sm font-semibold">{cat.name}</h4>
                              {cat.is_expanded && (
                                <Chip variant="neutral" size="sm">Expanded Code</Chip>
                              )}
                            </div>
                          </div>

                          <div className="mt-3 text-xs space-y-2 text-slate-700 dark:text-slate-300">
                            <div>
                              <span className="font-semibold text-slate-900 dark:text-slate-100">Definition: </span>
                              {cat.definition}
                            </div>
                            <div>
                              <span className="font-semibold text-slate-900 dark:text-slate-100">Assessable Criteria: </span>
                              {cat.assessable_criteria}
                            </div>
                            <div className="p-2 bg-slate-100 dark:bg-slate-900/60 rounded border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400">
                              <span className="font-semibold text-slate-800 dark:text-slate-200">Regional Variation Rule: </span>
                              {cat.variation_rules}
                            </div>

                            {cat.examples && cat.examples.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                                <span className="font-semibold text-slate-500">Benchmark Examples:</span>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                                  {cat.examples.map((ex, i) => (
                                    <div key={i} className="text-[11px] p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-800">
                                      <div className="text-rose-600 dark:text-rose-400 font-mono">✗ &quot;{ex.phrase}&quot;</div>
                                      <div className="text-emerald-600 dark:text-emerald-400 font-mono mt-0.5">✓ &quot;{ex.correction}&quot;</div>
                                      {ex.explanation && (
                                        <div className="text-slate-500 mt-1 italic">{ex.explanation}</div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState title="No Rubric Selected" description="Select a rubric from the left panel to inspect details." />
              )}
            </div>
          </div>
        )}

        {/* --- TAB 2: PROMPT VERSIONS --- */}
        {activeTab === "prompts" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="p-4 lg:col-span-1">
              <h2 className="text-base font-semibold mb-4">AI Prompt Roles</h2>
              {loadingPrompts ? (
                <div className="py-8 text-center text-sm text-slate-500">Loading prompts...</div>
              ) : (
                <div className="space-y-3">
                  {prompts.map((p) => (
                    <button
                      key={p.version_code}
                      onClick={() => fetchPromptDetail(p.version_code)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        selectedPrompt?.version_code === p.version_code
                          ? "border-sky-500 bg-sky-50/60 dark:bg-sky-950/30 ring-1 ring-sky-500"
                          : "border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <Chip variant="neutral" size="sm">
                          {p.prompt_role.replace(/_/g, " ").toUpperCase()}
                        </Chip>
                        <Chip variant={p.is_frozen ? "primary" : "warning"} size="sm">
                          {p.is_frozen ? "Frozen" : "Draft"}
                        </Chip>
                      </div>
                      <div className="text-sm font-medium mt-2">{p.name}</div>
                      <div className="text-xs font-mono text-slate-500 mt-1">{p.version_code}</div>
                    </button>
                  ))}
                </div>
              )}
            </Card>

            <div className="lg:col-span-2">
              {selectedPrompt ? (
                <Card className="p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
                    <div>
                      <h3 className="text-xl font-bold font-serif">{selectedPrompt.name}</h3>
                      <p className="text-xs font-mono text-slate-500 mt-1">
                        Role: {selectedPrompt.prompt_role} | Schema: {selectedPrompt.output_schema_version}
                      </p>
                    </div>
                    <Chip variant={selectedPrompt.is_frozen ? "primary" : "warning"}>
                      {selectedPrompt.is_frozen ? "Frozen & Immutable" : "Draft"}
                    </Chip>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                      Prompt Template Instructions
                    </h4>
                    <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed">
                      {selectedPrompt.prompt_template}
                    </pre>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                      Output JSON Schema Validation Contract
                    </h4>
                    <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono whitespace-pre-wrap overflow-x-auto">
                      {selectedPrompt.output_schema_json}
                    </pre>
                  </div>
                </Card>
              ) : (
                <EmptyState title="No Prompt Selected" description="Select an AI prompt role to inspect its template and schema." />
              )}
            </div>
          </div>
        )}

        {/* --- TAB 3: TOPIC BANK & DETERMINISTIC SEED TESTER --- */}
        {activeTab === "topics" && (
          <div className="space-y-6">
            {/* Reproducible Assignment Tester */}
            <Card className="p-6 bg-slate-900 text-slate-100 border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-sky-400" />
                    Reproducible Seed Assignment Simulator (FR-05, FR-20)
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Equivalence groups match pre and post test difficulty exactly. Hashing guarantees identical assignment on re-tests.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Input
                    placeholder="Participant ID"
                    value={testParticipantId}
                    onChange={(e) => setTestParticipantId(e.target.value)}
                    className="w-36 bg-slate-950 border-slate-700 text-white text-xs"
                  />
                  <Input
                    placeholder="Seed (int)"
                    value={testSeed}
                    onChange={(e) => setTestSeed(e.target.value)}
                    className="w-24 bg-slate-950 border-slate-700 text-white text-xs"
                  />
                  <Button
                    size="sm"
                    onClick={handleTestAssignment}
                    disabled={assigning}
                  >
                    {assigning ? "Assigning..." : "Simulate Seed"}
                  </Button>
                </div>
              </div>

              {assignmentResult && (
                <div className="mt-4 p-4 bg-slate-950/80 border border-slate-800 rounded-lg">
                  <div className="text-xs text-sky-400 font-mono mb-2">
                    Equivalence Group Assigned: <span className="font-bold underline">{assignmentResult.equivalence_group}</span> (Recorded Seed: {assignmentResult.seed})
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    <div className="p-3 bg-slate-900 border border-slate-800 rounded">
                      <div className="text-[11px] font-semibold text-sky-300 uppercase">Pre-Test Topic (Task 1)</div>
                      <div className="text-sm font-bold text-white mt-1">{assignmentResult.pre_task.title}</div>
                      <div className="text-xs text-slate-300 mt-1 italic">&quot;{assignmentResult.pre_task.prompt_text}&quot;</div>
                      <div className="text-[11px] text-slate-400 mt-2">Prep: 30s | Duration: 60s | Diff: {assignmentResult.pre_task.difficulty_level}</div>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded">
                      <div className="text-[11px] font-semibold text-emerald-300 uppercase">Post-Test Topic (Task 2)</div>
                      <div className="text-sm font-bold text-white mt-1">{assignmentResult.post_task.title}</div>
                      <div className="text-xs text-slate-300 mt-1 italic">&quot;{assignmentResult.post_task.prompt_text}&quot;</div>
                      <div className="text-[11px] text-slate-400 mt-2">Prep: 30s | Duration: 60s | Diff: {assignmentResult.post_task.difficulty_level}</div>
                    </div>
                  </div>
                </div>
              )}
            </Card>

            {/* Topic Bank List */}
            <Card className="p-6">
              <h3 className="text-base font-semibold mb-4">Topic Bank Pool ({tasks.length} Active Tasks)</h3>
              {loadingTasks ? (
                <div className="py-8 text-center text-sm text-slate-500">Loading topic bank...</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 uppercase font-mono">
                      <tr>
                        <th className="p-3">Equivalence Group</th>
                        <th className="p-3">Role</th>
                        <th className="p-3">Topic Title</th>
                        <th className="p-3">Prompt Text</th>
                        <th className="p-3">Duration</th>
                        <th className="p-3">Rubric</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      {tasks.map((t) => (
                        <tr key={t.task_id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                          <td className="p-3 font-mono font-bold text-sky-600 dark:text-sky-400">
                            {t.equivalence_group}
                          </td>
                          <td className="p-3">
                            <Chip size="sm" variant={t.task_type === "pre" ? "primary" : "neutral"}>
                              {t.task_type.toUpperCase()}
                            </Chip>
                          </td>
                          <td className="p-3 font-medium text-slate-900 dark:text-slate-100">{t.title}</td>
                          <td className="p-3 text-slate-600 dark:text-slate-400 italic max-w-xs truncate">{t.prompt_text}</td>
                          <td className="p-3 font-mono">{t.prep_time_seconds}s prep / {t.duration_seconds}s speak</td>
                          <td className="p-3 font-mono text-slate-500">{t.rubric_version}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* --- TAB 4: ASSESSMENT PERIODS --- */}
        {activeTab === "periods" && (
          <Card className="p-6">
            <h3 className="text-base font-semibold mb-4">Assessment Periods</h3>
            {loadingPeriods ? (
              <div className="py-8 text-center text-sm text-slate-500">Loading periods...</div>
            ) : (
              <div className="space-y-4">
                {periods.map((p) => (
                  <div key={p.period_code} className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-sky-600">{p.period_code}</span>
                          <h4 className="text-sm font-bold">{p.name}</h4>
                          <Chip variant={p.is_frozen ? "primary" : "warning"} size="sm">
                            {p.is_frozen ? "Frozen Cohort" : "Draft"}
                          </Chip>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">{p.description}</p>
                      </div>

                      <div className="text-xs text-slate-500 font-mono">
                        Start: {new Date(p.start_date).toLocaleDateString()}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 text-xs">
                      <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded">
                        <span className="text-slate-500 block">Rubric:</span>
                        <span className="font-mono font-bold">{p.rubric_version_code}</span>
                      </div>
                      <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded">
                        <span className="text-slate-500 block">Pre Assessor:</span>
                        <span className="font-mono font-bold">{p.pre_prompt_version_code}</span>
                      </div>
                      <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded">
                        <span className="text-slate-500 block">AI Tutor Prompt:</span>
                        <span className="font-mono font-bold">{p.tutor_prompt_version_code}</span>
                      </div>
                      <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded">
                        <span className="text-slate-500 block">Post Assessor:</span>
                        <span className="font-mono font-bold">{p.post_prompt_version_code}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* --- TAB 5: UNIFIED DIFF VIEWER --- */}
        {activeTab === "diff" && (
          <div className="space-y-6">
            <Card className="p-6">
              <h3 className="text-base font-semibold mb-4">Version Differential Inspector</h3>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
                <div>
                  <label className="text-xs font-semibold text-slate-500 block mb-1">Entity Type</label>
                  <select
                    value={diffType}
                    onChange={(e) => {
                      setDiffType(e.target.value);
                      if (e.target.value === "rubric") {
                        setBaseCode("v1.0-jam-phd");
                        setTargetCode("v1.0-jam-phd");
                      } else {
                        setBaseCode("v1.0-pre-assessor");
                        setTargetCode("v1.0-post-assessor");
                      }
                    }}
                    className="w-full text-xs p-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
                  >
                    <option value="rubric">Rubric Version</option>
                    <option value="prompt">AI Prompt Version</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-500 block mb-1">Base Version Code</label>
                  <Input
                    value={baseCode}
                    onChange={(e) => setBaseCode(e.target.value)}
                    className="text-xs font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-500 block mb-1">Target Version Code</label>
                  <Input
                    value={targetCode}
                    onChange={(e) => setTargetCode(e.target.value)}
                    className="text-xs font-mono"
                  />
                </div>

                <div>
                  <Button onClick={handleRunDiff} disabled={diffLoading} className="w-full" size="sm">
                    {diffLoading ? "Computing Diff..." : "Compute Diff"}
                  </Button>
                </div>
              </div>
            </Card>

            {diffResult && (
              <Card className="p-6">
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3 mb-4">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-sky-600">
                      {diffResult.base_code} → {diffResult.target_code}
                    </span>
                    <span className="text-xs text-emerald-600 font-mono">+{diffResult.additions} lines</span>
                    <span className="text-xs text-rose-600 font-mono">-{diffResult.deletions} lines</span>
                  </div>
                  <Chip variant={diffResult.has_changes ? "warning" : "success"} size="sm">
                    {diffResult.has_changes ? "Modifications Detected" : "Identical Versions"}
                  </Chip>
                </div>

                <div className="font-mono text-xs bg-slate-900 text-slate-200 rounded-lg p-4 overflow-x-auto space-y-0.5">
                  {diffResult.lines.length === 0 ? (
                    <div className="text-slate-400 py-4 text-center">No diff output (files identical)</div>
                  ) : (
                    diffResult.lines.map((line, idx) => (
                      <div
                        key={idx}
                        className={`px-2 py-0.5 rounded ${
                          line.type === "add"
                            ? "bg-emerald-950/70 text-emerald-300"
                            : line.type === "delete"
                            ? "bg-rose-950/70 text-rose-300"
                            : line.type === "header"
                            ? "bg-sky-950 text-sky-300 font-bold"
                            : "text-slate-400"
                        }`}
                      >
                        {line.type === "add" && "+ "}
                        {line.type === "delete" && "- "}
                        {line.text}
                      </div>
                    ))
                  )}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Freeze Confirmation Modal */}
      <Dialog open={freezeModalOpen} onOpenChange={setFreezeModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-rose-600 dark:text-rose-400">
              Irreversible Freeze Confirmation
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently freeze {itemToFreeze?.type} <strong>{itemToFreeze?.code}</strong>?
              <br /><br />
              Once frozen, PostgreSQL database triggers will permanently block any future edits or deletion. This operation cannot be reversed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFreezeModalOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleFreezeConfirm} disabled={freezeSubmitting}>
              {freezeSubmitting ? "Freezing..." : "Yes, Freeze Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
