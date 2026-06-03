"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  Cloud, LayoutDashboard, FolderOpen, BarChart3,
  Share2, Settings, LogOut, HardDrive, Bell, ChevronRight
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import toast from "react-hot-toast";

const NAV = [
  { href: "/dashboard",           icon: LayoutDashboard, label: "Overview" },
  { href: "/dashboard/files",     icon: FolderOpen,      label: "My Files" },
  { href: "/dashboard/analytics", icon: BarChart3,       label: "Analytics" },
  { href: "/dashboard/shared",    icon: Share2,          label: "Shared Links" },
  { href: "/dashboard/settings",  icon: Settings,        label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) router.push("/auth/login");
  }, [isAuthenticated, router]);

  const handleLogout = async () => {
    try { await authApi.logout(); } catch {}
    logout();
    toast.success("Signed out");
    router.push("/auth/login");
  };

  if (!isAuthenticated || !user) return null;

  const usedPct = Math.min(100, (user.storage_used_bytes / user.storage_quota_bytes) * 100);

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-surface-border bg-surface-card">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-surface-border">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shadow-glow">
            <Cloud className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-lg">CloudStore</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link key={href} href={href}
                className={`sidebar-link ${active ? "active" : ""}`}>
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
                {active && <ChevronRight className="w-3.5 h-3.5 ml-auto text-brand-400" />}
              </Link>
            );
          })}
        </nav>

        {/* Storage meter */}
        <div className="px-4 py-4 border-t border-surface-border">
          <div className="glass rounded-xl p-3">
            <div className="flex items-center gap-2 mb-2.5">
              <HardDrive className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-xs text-slate-400 font-medium">Storage</span>
              <span className="ml-auto text-xs text-slate-500">{usedPct.toFixed(0)}%</span>
            </div>
            <div className="w-full h-1.5 bg-surface-hover rounded-full overflow-hidden">
              <div
                className="h-full progress-fill rounded-full transition-all duration-500"
                style={{ width: `${usedPct}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-1.5">
              <span>{formatBytes(user.storage_used_bytes)}</span>
              <span>{formatBytes(user.storage_quota_bytes)}</span>
            </div>
          </div>
        </div>

        {/* User */}
        <div className="px-4 py-4 border-t border-surface-border">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-brand-300">
                {user.username?.[0]?.toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-white truncate">{user.username}</div>
              <div className="text-xs text-slate-500 truncate">{user.email}</div>
            </div>
          </div>
          <button onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                       text-slate-400 hover:text-white hover:bg-surface-hover transition-all">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-surface-border bg-surface-card/60 backdrop-blur-sm flex-shrink-0">
          <h1 className="text-lg font-semibold text-white">
            {NAV.find(n => pathname === n.href || (n.href !== "/dashboard" && pathname.startsWith(n.href)))?.label ?? "Dashboard"}
          </h1>
          <div className="flex items-center gap-3">
            <button className="relative w-9 h-9 rounded-xl glass flex items-center justify-center hover:bg-surface-hover transition-colors">
              <Bell className="w-4 h-4 text-slate-400" />
              <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-brand-500 rounded-full" />
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
