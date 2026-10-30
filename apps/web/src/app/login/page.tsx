"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Button,
  Input,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui";
import { apiFetch, UserProfile } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // View state: 'signin' | 'must_change_password' | 'reset_confirm'
  const [viewState, setViewState] = useState<"signin" | "must_change_password" | "reset_confirm">("signin");

  // Sign-in inputs
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Forced password change inputs
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changePwError, setChangePwError] = useState<string | null>(null);

  // Password reset request dialog
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [isResetSubmitting, setIsResetSubmitting] = useState(false);

  // Privacy notice modal
  const [privacyModalOpen, setPrivacyModalOpen] = useState(false);

  // Direct reset confirmation via URL token
  const tokenFromUrl = searchParams.get("reset_token");
  useEffect(() => {
    if (tokenFromUrl) {
      setViewState("reset_confirm");
    }
  }, [tokenFromUrl]);

  // Handle standard sign-in
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      const res = await apiFetch<{ user: UserProfile; csrf_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ identifier, password }),
      });

      if (res.user.must_change_password) {
        setViewState("must_change_password");
        setIsLoading(false);
        return;
      }

      // Redirect based on role
      if (res.user.role === "researcher_admin") {
        router.push("/admin/users");
      } else if (res.user.role === "reviewer") {
        router.push("/reviewer/queue");
      } else {
        router.push("/student/assessment");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Sign-in failed. Please verify your credentials.");
      setIsLoading(false);
    }
  };

  // Handle Google Sign-In
  const handleGoogleSignIn = async () => {
    setIsGoogleLoading(true);
    setErrorMessage(null);

    try {
      const res = await apiFetch<{ user: UserProfile; csrf_token: string }>("/auth/google", {
        method: "POST",
        body: JSON.stringify({
          email: "student_google@syntaxlens.edu",
          name: "Google Participant",
        }),
      });

      if (res.user.role === "researcher_admin") {
        router.push("/admin/dashboard");
      } else if (res.user.role === "reviewer") {
        router.push("/admin/review-queue");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Google sign-in could not be completed.");
    } finally {
      setIsGoogleLoading(false);
    }
  };

  // Handle forced password change
  const handleForcedPasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangePwError(null);

    if (newPassword !== confirmPassword) {
      setChangePwError("Passwords do not match. Please verify.");
      return;
    }

    setIsLoading(true);
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: password,
          new_password: newPassword,
        }),
      });

      // Continue to home
      router.push("/student/assessment");
    } catch (err: any) {
      setChangePwError(err.message || "Failed to update password. Ensure it meets complexity rules.");
      setIsLoading(false);
    }
  };

  // Handle requesting password reset
  const handleResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError(null);
    setResetSuccessMessage(null);
    setIsResetSubmitting(true);

    try {
      const res = await apiFetch<{ message: string }>("/auth/reset-password-request", {
        method: "POST",
        body: JSON.stringify({ identifier: resetIdentifier }),
      });
      setResetSuccessMessage(res.message);
    } catch (err: any) {
      setResetError(err.message || "Could not process password reset request.");
    } finally {
      setIsResetSubmitting(false);
    }
  };

  // Handle completing password reset from email token
  const handleCompleteReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await apiFetch<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          token: tokenFromUrl,
          new_password: newPassword,
        }),
      });
      alert(res.message);
      setViewState("signin");
      router.push("/login");
    } catch (err: any) {
      setErrorMessage(err.message || "Password reset token expired or invalid.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center items-center px-4 py-12 transition-colors">
      <div className="w-full max-w-md">
        {/* Academic Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600 text-white font-serif text-2xl font-bold shadow-sm mb-3">
            S
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            SyntaxLens
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Empirical Speech Syntactic Deviation & Tutoring Research Platform
          </p>
        </div>

        {/* View 1: Standard Sign In */}
        {viewState === "signin" && (
          <Card className="shadow-md border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">Participant & Researcher Sign-In</CardTitle>
              <CardDescription>
                Sign in with your assigned Participant ID (e.g. SL-2026-001) or institutional email.
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleSignIn}>
              <div className="px-6 pt-2 pb-1">
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={isGoogleLoading}
                  className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-medium text-sm shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>{isGoogleLoading ? "Connecting to Google..." : "Continue with Google"}</span>
                </button>

                <div className="relative flex py-3 items-center">
                  <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
                  <span className="flex-shrink mx-3 text-xs uppercase font-semibold text-slate-400">
                    Or continue with credentials
                  </span>
                  <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
                </div>
              </div>
              <CardContent className="space-y-4">
                {errorMessage && (
                  <div
                    role="alert"
                    className="p-3 text-sm rounded-lg border bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/60"
                  >
                    {errorMessage}
                  </div>
                )}

                <Input
                  label="Participant ID or Email"
                  placeholder="SL-2026-001 or name@university.edu"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  autoFocus
                />

                <Input
                  label="Password"
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-slate-500 dark:text-slate-400">
                    Protocols enforce strict server-side blinding.
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setResetSuccessMessage(null);
                      setResetError(null);
                      setResetIdentifier(identifier);
                      setResetDialogOpen(true);
                    }}
                    className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                  >
                    Forgot password?
                  </button>
                </div>
              </CardContent>

              <CardFooter className="flex flex-col gap-3 pt-2">
                <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
                  Sign In
                </Button>

                <div className="text-center pt-2">
                  <button
                    type="button"
                    onClick={() => setPrivacyModalOpen(true)}
                    className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 underline"
                  >
                    Research Privacy & Pseudonymisation Policy
                  </button>
                </div>

                {/* Quick-Fill Seed Test Accounts */}
                <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 text-center">
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
                    Quick-Fill Research Seed Accounts:
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <button
                      type="button"
                      onClick={() => {
                        setIdentifier("researcher@syntaxlens.edu");
                        setPassword("SyntaxLens@2026!");
                      }}
                      className="px-2.5 py-1 text-xs rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition-colors"
                    >
                      Lead Researcher
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIdentifier("reviewer@syntaxlens.edu");
                        setPassword("SyntaxLens@2026!");
                      }}
                      className="px-2.5 py-1 text-xs rounded-md bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors"
                    >
                      Reviewer
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIdentifier("student1@syntaxlens.edu");
                        setPassword("SyntaxLens@2026!");
                      }}
                      className="px-2.5 py-1 text-xs rounded-md bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 transition-colors"
                    >
                      Student 001
                    </button>
                  </div>
                </div>
              </CardFooter>
            </form>
          </Card>
        )}

        {/* View 2: Forced Password Change */}
        {viewState === "must_change_password" && (
          <Card className="shadow-md border-amber-200 dark:border-amber-900/60">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl text-amber-900 dark:text-amber-200">
                First Sign-In: Choose Private Password
              </CardTitle>
              <CardDescription>
                To protect research integrity and participant confidentiality, please choose a permanent secure password.
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleForcedPasswordChange}>
              <CardContent className="space-y-4">
                {changePwError && (
                  <div
                    role="alert"
                    className="p-3 text-sm rounded-lg border bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/60"
                  >
                    {changePwError}
                  </div>
                )}

                <Input
                  label="New Secure Password"
                  type="password"
                  placeholder="Minimum 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  helperText="Must include uppercase, lowercase, number, and symbol."
                />

                <Input
                  label="Confirm New Password"
                  type="password"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </CardContent>

              <CardFooter className="flex flex-col gap-2">
                <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
                  Update Password & Enter Study
                </Button>
              </CardFooter>
            </form>
          </Card>
        )}

        {/* View 3: Reset Token Confirmation */}
        {viewState === "reset_confirm" && (
          <Card className="shadow-md border-indigo-200 dark:border-indigo-900">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">Set New Password</CardTitle>
              <CardDescription>
                Your single-use reset token has been verified. Enter your new password below.
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleCompleteReset}>
              <CardContent className="space-y-4">
                {errorMessage && (
                  <div role="alert" className="p-3 text-sm rounded-lg border bg-rose-50 text-rose-800 border-rose-200">
                    {errorMessage}
                  </div>
                )}

                <Input
                  label="New Password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  helperText="At least 8 characters with upper, lower, digit, and symbol."
                />

                <Input
                  label="Confirm New Password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </CardContent>

              <CardFooter className="flex gap-2">
                <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
                  Confirm New Password
                </Button>
              </CardFooter>
            </form>
          </Card>
        )}
      </div>

      {/* Password Reset Request Dialog */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Enter your Participant ID or email. A single-use secure reset link (valid for 15 minutes) will be sent to the registered address.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleResetRequest} className="space-y-4 py-2">
            {resetSuccessMessage ? (
              <div className="p-3 text-sm rounded-lg border bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/60">
                {resetSuccessMessage}
              </div>
            ) : (
              <>
                {resetError && (
                  <div className="p-3 text-sm rounded-lg border bg-rose-50 text-rose-800 border-rose-200">
                    {resetError}
                  </div>
                )}
                <Input
                  label="Participant ID or Email"
                  placeholder="e.g. SL-2026-001 or email@domain.edu"
                  value={resetIdentifier}
                  onChange={(e) => setResetIdentifier(e.target.value)}
                  required
                />
              </>
            )}

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setResetDialogOpen(false)}>
                Close
              </Button>
              {!resetSuccessMessage && (
                <Button type="submit" variant="primary" isLoading={isResetSubmitting}>
                  Send Reset Link
                </Button>
              )}
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Privacy Notice Modal */}
      <Dialog open={privacyModalOpen} onOpenChange={setPrivacyModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>SyntaxLens Research Privacy Notice</DialogTitle>
            <DialogDescription>
              Approved Ethical Framework for Spoken English Syntax Research (SRS §12–13)
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-h-[60vh] overflow-y-auto pr-2">
            <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
              1. Pseudonymous Identification
            </h4>
            <p>
              Your personal identity (name, email) is isolated in a separate database schema from your speech recordings, transcripts, and syntactic analyses. You are identified in all research tables and academic publications exclusively by a randomized research code (e.g. SL-2026-xxx).
            </p>

            <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
              2. Audio Recording Protection
            </h4>
            <p>
              Audio recordings are stored in private, encrypted object storage. No public URLs exist. Access is granted solely to authorized researchers and blinded reviewers through short-lived presigned URLs. Every access to a recording is permanently recorded in an append-only audit log.
            </p>

            <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
              3. AI Provider Privacy
            </h4>
            <p>
              Zero direct identifiers are ever transmitted to speech-to-text or language model APIs. Only anonymous audio and isolated sentence fragments are processed.
            </p>

            <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
              4. Voluntary Participation & Right to Withdraw
            </h4>
            <p>
              You may withdraw your consent at any time without penalty. Withdrawing consent immediately ceases data collection and excludes your records from future comparative research exports.
            </p>
          </div>

          <DialogFooter>
            <Button variant="primary" onClick={() => setPrivacyModalOpen(false)}>
              I Understand
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-slate-500">Loading sign-in...</div>}>
      <LoginForm />
    </Suspense>
  );
}
