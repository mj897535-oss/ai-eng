"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Button,
  Input,
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  EmptyState,
} from "@/components/ui";
import { apiFetch, PaginatedResponse } from "@/lib/api";

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  participant_id?: string | null;
  participant_code?: string | null;
  study_group?: string | null;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");

  // Create User Modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("participant");
  const [newStudyGroup, setNewStudyGroup] = useState("intervention");
  const [newMotherTongue, setNewMotherTongue] = useState("Marathi");
  const [newSchoolMedium, setNewSchoolMedium] = useState("English");
  const [newAge, setNewAge] = useState<number | "">("");
  const [customResearchCode, setCustomResearchCode] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set("query", searchQuery);
      if (selectedRole) params.set("role", selectedRole);
      if (selectedStatus !== "") params.set("is_active", selectedStatus);

      const res = await apiFetch<PaginatedResponse<UserItem>>(`/admin/users?${params.toString()}`);
      setUsers(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error("Failed to load users:", err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedRole, selectedStatus]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Toggle user activation
  const handleToggleStatus = async (user: UserItem) => {
    const confirmMsg = user.is_active
      ? `Deactivate ${user.full_name}? Active sessions will be terminated immediately.`
      : `Reactivate ${user.full_name}?`;

    if (!window.confirm(confirmMsg)) return;

    try {
      await apiFetch(`/admin/users/${user.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      fetchUsers();
    } catch (err: any) {
      alert(err.message || "Failed to update user status.");
    }
  };

  // Create new user
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    setIsCreating(true);

    try {
      await apiFetch("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email: newEmail,
          full_name: newName,
          role: newRole,
          must_change_password: true,
          research_code: customResearchCode || undefined,
          study_group: newStudyGroup,
          mother_tongue: newMotherTongue,
          school_medium: newSchoolMedium,
          age: newAge ? Number(newAge) : undefined,
        }),
      });

      setCreateModalOpen(false);
      // Reset form
      setNewEmail("");
      setNewName("");
      setCustomResearchCode("");
      fetchUsers();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create user.");
    } finally {
      setIsCreating(false);
    }
  };

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
            <a href="/admin/users" className="text-indigo-600 dark:text-indigo-400 font-semibold border-b-2 border-indigo-600 pb-1">
              Users & Cohort
            </a>
            <a href="/admin/audit" className="text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400">
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
            <h1 className="text-2xl font-bold tracking-tight">Cohort User Directory</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {total} total research accounts enrolled. Identity data is partitioned from speech analyses.
            </p>
          </div>

          <Button variant="primary" onClick={() => setCreateModalOpen(true)}>
            + Enroll User
          </Button>
        </div>

        {/* Filter Controls Card */}
        <Card className="mb-6 border-slate-200 dark:border-slate-800">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="sm:col-span-2">
                <Input
                  placeholder="Search by name, email, or research code..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <div>
                <Select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  options={[
                    { value: "", label: "All Roles" },
                    { value: "participant", label: "Participant" },
                    { value: "reviewer", label: "Reviewer" },
                    { value: "researcher_admin", label: "Researcher Admin" },
                  ]}
                />
              </div>

              <div>
                <Select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  options={[
                    { value: "", label: "All Statuses" },
                    { value: "true", label: "Active Only" },
                    { value: "false", label: "Deactivated" },
                  ]}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card className="border-slate-200 dark:border-slate-800 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">Loading cohort accounts...</div>
          ) : users.length === 0 ? (
            <EmptyState
              title="No users match your criteria"
              description="Adjust your search filters or click Enroll User to provision an account."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearchQuery("");
                    setSelectedRole("");
                    setSelectedStatus("");
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
                  <TableHead>Full Name</TableHead>
                  <TableHead>Account / Identifier</TableHead>
                  <TableHead>Research Code</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Study Group</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium text-slate-900 dark:text-slate-100">
                      {u.full_name}
                      {u.must_change_password && (
                        <span className="block text-xs text-amber-600 dark:text-amber-400">
                          Password change required
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-600 dark:text-slate-300 font-mono text-xs">
                      {u.email}
                    </TableCell>
                    <TableCell>
                      {u.participant_code ? (
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
                          {u.participant_code}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        variant={
                          u.role === "researcher_admin"
                            ? "primary"
                            : u.role === "reviewer"
                            ? "warning"
                            : "success"
                        }
                      >
                        {u.role}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      {u.study_group ? (
                        <span className="text-xs font-medium text-slate-600 dark:text-slate-300 capitalize">
                          {u.study_group}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip variant={u.is_active ? "neutral" : "danger"}>
                        {u.is_active ? "Active" : "Deactivated"}
                      </Chip>
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleToggleStatus(u)}
                        className={`text-xs font-medium hover:underline ${
                          u.is_active ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"
                        }`}
                      >
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </main>

      {/* Enroll User Dialog */}
      <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Enroll New Account</DialogTitle>
            <DialogDescription>
              Provision a participant, reviewer, or administrator account. A secure temporary password will be assigned.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateUser} className="space-y-4 py-2">
            {createError && (
              <div role="alert" className="p-3 text-sm rounded-lg border bg-rose-50 text-rose-800 border-rose-200">
                {createError}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Full Name"
                placeholder="Dr. Anita Sharma"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
              <Input
                label="Institutional Email"
                type="email"
                placeholder="anita@university.edu"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
              />
            </div>

            <Select
              label="Account Role"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              options={[
                { value: "participant", label: "Participant (Learner)" },
                { value: "reviewer", label: "Blinded Human Reviewer" },
                { value: "researcher_admin", label: "Lead Researcher Administrator" },
              ]}
            />

            {newRole === "participant" && (
              <div className="border border-slate-200 dark:border-slate-800 rounded-lg p-3 space-y-3 bg-slate-50/50 dark:bg-slate-900/50">
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Participant Protocol Demographics
                </span>

                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Research Code (Optional)"
                    placeholder="Auto-generated if empty"
                    value={customResearchCode}
                    onChange={(e) => setCustomResearchCode(e.target.value)}
                    helperText="e.g. SL-2026-003"
                  />
                  <Select
                    label="Study Group"
                    value={newStudyGroup}
                    onChange={(e) => setNewStudyGroup(e.target.value)}
                    options={[
                      { value: "intervention", label: "Intervention (AI Tutor)" },
                      { value: "control", label: "Control (Baseline Only)" },
                    ]}
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <Input
                    label="Mother Tongue"
                    value={newMotherTongue}
                    onChange={(e) => setNewMotherTongue(e.target.value)}
                  />
                  <Input
                    label="School Medium"
                    value={newSchoolMedium}
                    onChange={(e) => setNewSchoolMedium(e.target.value)}
                  />
                  <Input
                    label="Age"
                    type="number"
                    placeholder="21"
                    value={newAge}
                    onChange={(e) => setNewAge(e.target.value ? Number(e.target.value) : "")}
                  />
                </div>
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isCreating}>
                Enroll User
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
