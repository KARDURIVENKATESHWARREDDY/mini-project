"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Users, Plus, ChevronLeft, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

interface UserRow {
  id: string; email: string; full_name: string; role: string;
  is_active: boolean; last_login_at?: string; created_at: string;
}

const ROLE_STYLES: Record<string, string> = {
  admin: "text-red-400 bg-red-500/10 border-red-500/30",
  analyst: "text-violet-400 bg-violet-500/10 border-violet-500/30",
  viewer: "text-muted-foreground bg-muted border-border/50",
};

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "viewer" });
  const [creating, setCreating] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["users", page],
    queryFn: () => usersApi.list(page).then((r) => r.data) as Promise<{ total: number; page: number; page_size: number; items: UserRow[] }>,
  });

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    if (!form.email || !form.full_name || !form.password) {
      toast.error("Please fill all required fields.");
      return;
    }
    setCreating(true);
    try {
      await usersApi.create(form);
      toast.success("User created successfully.");
      setForm({ email: "", full_name: "", password: "", role: "viewer" });
      setShowCreate(false);
      qc.invalidateQueries({ queryKey: ["users"] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create user.";
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(user: UserRow) {
    try {
      await usersApi.update(user.id, { is_active: !user.is_active });
      toast.success(`User ${user.is_active ? "deactivated" : "activated"}.`);
      qc.invalidateQueries({ queryKey: ["users"] });
    } catch {
      toast.error("Failed to update user.");
    }
  }

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="p-6 space-y-5 max-w-5xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-400" />
            User Management
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data ? `${data.total} user${data.total !== 1 ? "s" : ""}` : "Loading…"}
          </p>
        </div>
        <button
          id="create-user-btn"
          onClick={() => setShowCreate((s) => !s)}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          New User
        </button>
      </div>

      {/* Create user form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="card-glass p-5 border-emerald-500/30">
              <h2 className="text-sm font-semibold text-foreground mb-4">Create New User</h2>
              <form onSubmit={createUser} className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="md:col-span-2">
                  <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Email *</label>
                  <input
                    id="new-user-email"
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    placeholder="user@anurag.edu.in"
                    className="w-full px-3 py-2 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Full Name *</label>
                  <input
                    id="new-user-name"
                    type="text"
                    value={form.full_name}
                    onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                    placeholder="Jane Doe"
                    className="w-full px-3 py-2 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Password *</label>
                  <input
                    id="new-user-password"
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Role</label>
                  <select
                    id="new-user-role"
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    className="w-full py-2 px-3 text-sm bg-muted/50 border border-border/50 rounded-lg text-foreground focus:outline-none focus:border-emerald-500/50 transition-colors"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="md:col-span-4 flex items-center gap-2">
                  <button
                    id="create-user-submit"
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
                  >
                    {creating ? "Creating…" : "Create User"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreate(false)}
                    className="px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground text-sm transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Users table */}
      <div className="card-glass overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 bg-muted/20">
                {["Name", "Email", "Role", "Active", "Last Login", "Created", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/20">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="skeleton h-4 w-20" /></td>
                      ))}
                    </tr>
                  ))
                : data?.items.map((u) => (
                    <motion.tr
                      key={u.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="border-b border-border/20 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3 text-xs font-medium text-foreground">{u.full_name}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{u.email}</td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase font-semibold tracking-wide ${ROLE_STYLES[u.role] ?? "text-muted-foreground bg-muted border-border"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {u.is_active
                          ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          : <XCircle className="w-4 h-4 text-muted-foreground" />}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{u.last_login_at ? formatDate(u.last_login_at) : "Never"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(u.created_at)}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleActive(u)}
                          className={`text-xs px-2 py-1 rounded-lg transition-colors ${
                            u.is_active
                              ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30"
                              : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30"
                          }`}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </motion.tr>
                  ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
            <p className="text-xs text-muted-foreground">Page {page} of {totalPages}</p>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 text-muted-foreground hover:text-foreground transition-colors">
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-1.5 rounded-lg bg-muted/50 hover:bg-muted disabled:opacity-30 text-muted-foreground hover:text-foreground transition-colors">
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
