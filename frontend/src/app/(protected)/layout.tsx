import { AppShell } from "@/components/layouts/app-shell";
import AuthGuard from "@/components/layouts/auth-guard";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
