"use client";

import * as React from "react";
import {
  Moon,
  Sun,
  Shield,
  BookOpen,
} from "lucide-react";
import {
  Button,
  Input,
  Select,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  Toast,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Chip,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Skeleton,
  EmptyState,
  ProgressSteps,
} from "@/components/ui";

export default function DesignSystemPage() {
  const [isDark, setIsDark] = React.useState(false);
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [currentStep, setCurrentStep] = React.useState(1);

  React.useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  const assessmentSteps = [
    { id: "1", title: "Protocol Consent" },
    { id: "2", title: "JAM Topic Prep" },
    { id: "3", title: "Audio Recording" },
    { id: "4", title: "Evidence Verification" },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* Top Header */}
      <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-4 sm:px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white shadow-sm">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">SyntaxLens Design System</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Calm, modern academic tokens & accessible component primitives (WCAG 2.2 AA)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDark(!isDark)}
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
              <span className="hidden sm:inline">{isDark ? "Light Mode" : "Dark Mode"}</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-10 space-y-16">
        {/* Visual Foundations & Tokens */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            1. Design Tokens & Academic Palette
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            A calm, distraction-free aesthetic with generous whitespace and confident indigo accenting.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-indigo-600 text-white shadow-sm space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Accent</div>
              <div className="font-bold text-sm">Indigo 600</div>
              <div className="text-xs opacity-75">Primary Action</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 shadow-sm space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Foreground</div>
              <div className="font-bold text-sm">Slate 900</div>
              <div className="text-xs opacity-75">Headings & Body</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Muted</div>
              <div className="font-bold text-sm">Slate 100/800</div>
              <div className="text-xs opacity-75">Cards & Surfaces</div>
            </div>
            <div className="p-4 rounded-xl bg-emerald-500 text-white shadow-sm space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Concordant</div>
              <div className="font-bold text-sm">Emerald 500</div>
              <div className="text-xs opacity-75">Accepted / Correct</div>
            </div>
            <div className="p-4 rounded-xl bg-amber-500 text-white shadow-sm space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Uncertain</div>
              <div className="font-bold text-sm">Amber 500</div>
              <div className="text-xs opacity-75">Review Required</div>
            </div>
            <div className="p-4 rounded-xl bg-rose-500 text-white shadow-sm space-y-1">
              <div className="text-xs font-semibold uppercase opacity-80">Deviation</div>
              <div className="font-bold text-sm">Rose 500</div>
              <div className="text-xs opacity-75">Candidate Error</div>
            </div>
          </div>
        </section>

        {/* Buttons */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            2. Button Variants & States
          </h2>
          <div className="flex flex-wrap gap-4 items-center">
            <Button variant="primary">Primary Action</Button>
            <Button variant="secondary">Secondary Action</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="destructive">Destructive Action</Button>
            <Button variant="primary" isLoading>
              Processing
            </Button>
            <Button variant="primary" disabled>
              Disabled State
            </Button>
          </div>

          <div className="flex flex-wrap gap-4 items-center pt-2">
            <Button size="sm">Small (sm)</Button>
            <Button size="md">Medium (md)</Button>
            <Button size="lg">Large (lg)</Button>
          </div>
        </section>

        {/* Inputs and Selects */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            3. Form Inputs & Selectors
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl">
            <Input
              label="Participant ID"
              placeholder="e.g. SL-2026-001"
              helperText="Unique pseudonymous research identifier."
            />
            <Input
              label="Error State Input"
              defaultValue="Invalid Entry"
              error="A valid research identifier must be provided."
            />
            <Select
              label="Target Syntactic Structure"
              options={[
                { label: "SVA — Subject-Verb Agreement", value: "SVA" },
                { label: "TNS — Tense & Aspect", value: "TNS" },
                { label: "WO — Word Order", value: "WO" },
                { label: "AUX — Auxiliary Usage", value: "AUX" },
                { label: "ART — Article Choice", value: "ART" },
              ]}
              helperText="Prioritized baseline error category."
            />
          </div>
        </section>

        {/* Chips and Badges */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            4. Status Chips & Category Badges
          </h2>
          <div className="flex flex-wrap gap-3 items-center">
            <Chip variant="primary">SVA: Subject-Verb Agreement</Chip>
            <Chip variant="primary">TNS: Tense/Aspect</Chip>
            <Chip variant="neutral">WO: Word Order</Chip>
            <Chip variant="success">Accepted by Reviewer</Chip>
            <Chip variant="warning">Requires Human Audit</Chip>
            <Chip variant="danger">Syntactic Deviation</Chip>
            <Chip variant="unobserved">Not Observed in this Sample</Chip>
          </div>
        </section>

        {/* Progress Steps */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
            <h2 className="text-2xl font-bold tracking-tight">5. Assessment Progress Steps</h2>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
              >
                Previous Step
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(Math.min(assessmentSteps.length - 1, currentStep + 1))}
              >
                Next Step
              </Button>
            </div>
          </div>
          <ProgressSteps steps={assessmentSteps} currentStepIndex={currentStep} />
        </section>

        {/* Dialog / Modal & Toasts */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            6. Modal Dialogs & Feedback Toasts
          </h2>

          <div className="flex flex-wrap gap-4 items-center mb-6">
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="primary">Open Reproducibility Panel</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Reproducibility & Calculation Metadata</DialogTitle>
                  <DialogDescription>
                    All metrics are computed strictly by the pure backend module with frozen rubric hashes.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2 text-sm text-slate-700 dark:text-slate-300">
                  <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-800 font-mono text-xs">
                    Error Rate = (Syntactic Errors ÷ Word Count) × 100
                  </div>
                  <p>
                    <strong>Rubric Version:</strong> <code>v1.0-jam-phd</code>
                  </p>
                  <p>
                    <strong>Denominator:</strong> 128 verbatim words in post-test sample.
                  </p>
                </div>
                <div className="flex justify-end gap-2 mt-4">
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                    Close
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Toast
              id="t1"
              type="info"
              title="Session Initialized"
              description="Connecting to deterministic tutor engine."
            />
            <Toast
              id="t2"
              type="success"
              title="Audio Submitted"
              description="Recorded speech stored in private object storage."
            />
            <Toast
              id="t3"
              type="warning"
              title="Review Pending"
              description="Candidate SVA error flagged for human confirmation."
            />
            <Toast
              id="t4"
              type="error"
              title="Network Drop"
              description="Audio cached in browser; retrying upload..."
            />
          </div>
        </section>

        {/* Tabs and Data Table */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            7. Tabs & Academic Data Table
          </h2>

          <Tabs defaultValue="evidence" className="w-full">
            <TabsList>
              <TabsTrigger value="evidence">Candidate Errors</TabsTrigger>
              <TabsTrigger value="history">Session Logs</TabsTrigger>
              <TabsTrigger value="notes">Methodology</TabsTrigger>
            </TabsList>

            <TabsContent value="evidence" className="pt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead>Verbatim Span</TableHead>
                    <TableHead>Target Form</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Audit Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>
                      <Chip variant="primary">SVA</Chip>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-rose-600 dark:text-rose-400">
                      He go to college
                    </TableCell>
                    <TableCell className="font-mono text-xs text-emerald-600 dark:text-emerald-400">
                      He goes to college
                    </TableCell>
                    <TableCell>96.4%</TableCell>
                    <TableCell>
                      <Chip variant="success">Accepted</Chip>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      <Chip variant="primary">TNS</Chip>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-rose-600 dark:text-rose-400">
                      I have seen him yesterday
                    </TableCell>
                    <TableCell className="font-mono text-xs text-emerald-600 dark:text-emerald-400">
                      I saw him yesterday
                    </TableCell>
                    <TableCell>94.1%</TableCell>
                    <TableCell>
                      <Chip variant="warning">Needs Review</Chip>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      <Chip variant="neutral">OTH</Chip>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-600 dark:text-slate-400">
                      In Pune, I stayed
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">I stayed in Pune</TableCell>
                    <TableCell>82.0%</TableCell>
                    <TableCell>
                      <Chip variant="unobserved">Acceptable Variation</Chip>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="history" className="pt-4 text-sm text-slate-600 dark:text-slate-400">
              <p>Practice session logs showing duration, target categories, and hint ladder attempts.</p>
            </TabsContent>

            <TabsContent value="notes" className="pt-4 text-sm text-slate-600 dark:text-slate-400">
              <p>
                Syntactic error classifications follow the approved PhD research taxonomy. Absence of
                an error does not denote permanent acquisition.
              </p>
            </TabsContent>
          </Tabs>
        </section>

        {/* Cards, Skeletons and Empty State */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight border-b border-slate-200 dark:border-slate-800 pb-2">
            8. Cards, Skeletons & Empty States
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-1">
                  <BookOpen className="w-5 h-5" />
                  <span className="text-xs font-bold uppercase tracking-wider">Hint Ladder L1</span>
                </div>
                <CardTitle>Grammar Guiding Question</CardTitle>
                <CardDescription>Target: Simple Present Tense (SVA)</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  Notice the subject &apos;He&apos; in your sentence. In English, what ending do we add to the verb
                  when talking about someone else in the present tense?
                </p>
              </CardContent>
              <CardFooter className="justify-between">
                <Button variant="ghost" size="sm">
                  Request Rule (L2)
                </Button>
                <Button variant="primary" size="sm">
                  Attempt Answer
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Loading Audio Analysis</CardTitle>
                <CardDescription>Synthesizing candidate spans...</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <div className="pt-2 flex gap-2">
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-20 rounded-full" />
                </div>
              </CardContent>
            </Card>

            <EmptyState
              title="No Syntactic Deviations Observed"
              description="No errors in this category were observed in this spontaneous speech sample."
              action={
                <Button variant="outline" size="sm">
                  View Sample Transcript
                </Button>
              }
            />
          </div>
        </section>
      </main>
    </div>
  );
}
