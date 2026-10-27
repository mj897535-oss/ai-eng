"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { apiFetch } from "@/lib/api";

interface ReviewQueueItem {
  assessment_id: string;
  participant_code: string;
  assessment_type: string;
  needs_review_count: number;
  total_annotations: number;
  created_at: string;
}

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const items = await apiFetch<ReviewQueueItem[]>("/assessments/review-queue");
      setQueue(items);
    } catch {
      // Fallback sample data for preview and inspection
      setQueue([
        {
          assessment_id: "a123e456-789b-12d3-a456-426614174000",
          participant_code: "SL-2026-0004",
          assessment_type: "pre_test",
          needs_review_count: 2,
          total_annotations: 4,
          created_at: "2026-10-27T18:20:00Z",
        },
        {
          assessment_id: "b234e567-890c-23d4-b567-537725285111",
          participant_code: "SL-2026-0012",
          assessment_type: "post_test",
          needs_review_count: 1,
          total_annotations: 3,
          created_at: "2026-10-27T19:05:00Z",
        },
        {
          assessment_id: "c345e678-901d-34e5-c678-648836396222",
          participant_code: "SL-2026-0021",
          assessment_type: "pre_test",
          needs_review_count: 3,
          total_annotations: 5,
          created_at: "2026-10-27T19:40:00Z",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <Link href="/admin/pilot" className="hover:underline">Researcher Admin</Link>
              <span>/</span>
              <span className="text-slate-900 dark:text-slate-200 font-medium">Review Queue</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50">
              Human Review Adjudication Queue
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
              Candidate errors automatically routed due to low model confidence (&lt; 0.85), OTH category taxonomy, or dialect ambiguity.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Chip variant="warning" size="sm">
              {queue.reduce((acc, q) => acc + q.needs_review_count, 0)} Flagged Spans Pending
            </Chip>
          </div>
        </div>

        {/* Notice Card */}
        <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-900 dark:text-amber-200 flex items-start gap-3">
          <span className="font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 shrink-0">
            Adjudication Protocol:
          </span>
          <span>
            Candidate spans in this queue are withheld from participants until a calibrated researcher reviews acoustic alignment, rubric code suitability, and Indian English acceptable variations.
          </span>
        </div>

        {/* Queue Table */}
        <Card className="p-0 overflow-hidden bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 dark:bg-slate-950/60">
                <TableHead className="font-mono text-xs">PARTICIPANT ID</TableHead>
                <TableHead className="font-mono text-xs">ASSESSMENT TYPE</TableHead>
                <TableHead className="font-mono text-xs">FLAGGED FOR REVIEW</TableHead>
                <TableHead className="font-mono text-xs">TOTAL ANNOTATIONS</TableHead>
                <TableHead className="font-mono text-xs">SUBMITTED AT</TableHead>
                <TableHead className="text-right font-mono text-xs">ACTION</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-sm text-slate-500">
                    Loading review queue...
                  </TableCell>
                </TableRow>
              ) : queue.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-sm text-slate-500">
                    Review queue is empty. All candidate annotations have been verified or released.
                  </TableCell>
                </TableRow>
              ) : (
                queue.map((item) => (
                  <TableRow key={item.assessment_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                    <TableCell className="font-mono font-bold text-slate-900 dark:text-slate-100">
                      {item.participant_code}
                    </TableCell>
                    <TableCell>
                      <Chip variant="neutral" size="sm" className="capitalize">
                        {item.assessment_type.replace("_", "-")}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300">
                        {item.needs_review_count} flagged
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                      {item.total_annotations} total
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 font-mono">
                      {new Date(item.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/assessment/${item.assessment_id}/report`}>
                        <Button size="sm" variant="outline" className="font-serif text-xs">
                          Launch Evidence Lens &rarr;
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
