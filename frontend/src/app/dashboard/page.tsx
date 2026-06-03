"use client";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  FolderOpen, HardDrive, GitMerge, Download,
  Share2, TrendingUp, Shield, Zap, ExternalLink
} from "lucide-react";
import { analyticsApi } from "@/lib/api";
import { formatBytes, formatPercent, formatRelativeDate, getFileColor } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import type { DashboardData } from "@/types";
import { format } from "date-fns";
import Link from "next/link";

const CHART_COLORS = ["#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444","#ec4899"];

function StatCard({ icon: Icon, label, value, sub, iconColor }: any) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconColor}`}>
          <Icon className="w-5 h-5" />
        </div>
        <TrendingUp className="w-4 h-4 text-emerald-400 opacity-60" />
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm font-medium text-white/80 mt-0.5">{label}</div>
        {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 rounded-xl text-xs">
      <div className="text-slate-400 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.stroke || p.fill }} className="flex gap-2">
          <span>{p.name}:</span>
          <span className="text-white font-medium">
            {p.name?.includes("size") ? formatBytes(p.value) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: () => analyticsApi.dashboard().then(r => r.data),
    refetchInterval: 30_000,
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array(4).fill(0).map((_,i) => <div key={i} className="h-32 glass rounded-2xl" />)}
        </div>
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="h-72 glass rounded-2xl" />
          <div className="h-72 glass rounded-2xl" />
        </div>
      </div>
    );
  }

  const { storage, recent_uploads, upload_trend, file_types, total_downloads, total_shares } = data;
  const dedupPie = [
    { name: "Unique", value: storage.unique_chunks },
    { name: "Duplicate", value: storage.duplicate_chunks },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">
          Good {new Date().getHours() < 12 ? "morning" : "afternoon"},{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
            {user?.username}
          </span> 👋
        </h2>
        <p className="text-slate-400 text-sm mt-1">Your storage overview for today.</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FolderOpen}  label="Total Files"     value={storage.total_files}              sub="across all folders"               iconColor="bg-brand-600/20 text-brand-400" />
        <StatCard icon={HardDrive}   label="Storage Used"    value={formatBytes(storage.storage_used_bytes)} sub={`${formatPercent(storage.storage_used_percent)} of quota`} iconColor="bg-purple-600/20 text-purple-400" />
        <StatCard icon={GitMerge}    label="Saved by Dedup"  value={formatBytes(storage.dedup_savings_bytes)} sub={`${formatPercent(storage.dedup_efficiency_percent)} efficiency`} iconColor="bg-emerald-600/20 text-emerald-400" />
        <StatCard icon={Download}    label="Total Downloads" value={total_downloads}                   sub={`${total_shares} share links`}    iconColor="bg-orange-600/20 text-orange-400" />
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Upload trend */}
        <div className="card">
          <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-400" /> Upload Trend (30 Days)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={upload_trend} margin={{ left: -20, right: 0 }}>
              <defs>
                <linearGradient id="uploadGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={v => format(new Date(v), "MMM d")} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="upload_count" name="Uploads"
                stroke="#3b82f6" strokeWidth={2} fill="url(#uploadGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Dedup pie */}
        <div className="card">
          <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
            <GitMerge className="w-4 h-4 text-emerald-400" /> Chunk Deduplication
          </h3>
          <div className="flex items-center gap-6">
            <ResponsiveContainer width="50%" height={200}>
              <PieChart>
                <Pie data={dedupPie} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                  <Cell fill="#3b82f6" />
                  <Cell fill="#334155" />
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
                  {formatPercent(storage.dedup_efficiency_percent)}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">Efficiency</div>
              </div>
              {[
                { label: "Total Chunks",     value: storage.total_chunks,     color: "text-slate-300" },
                { label: "Unique",           value: storage.unique_chunks,    color: "text-brand-400" },
                { label: "Duplicates",       value: storage.duplicate_chunks, color: "text-emerald-400" },
                { label: "IPFS Pinned",      value: storage.ipfs_pinned_chunks, color: "text-purple-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex justify-between text-sm">
                  <span className="text-slate-500">{label}</span>
                  <span className={`font-medium ${color}`}>{value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* File types + Recent */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* File type breakdown */}
        <div className="card">
          <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" /> File Types
          </h3>
          {file_types.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-8">No files uploaded yet</p>
          ) : (
            <div className="space-y-3">
              {file_types.slice(0, 6).map((ft, i) => (
                <div key={ft.extension}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className={`font-medium uppercase ${getFileColor(ft.extension)}`}>.{ft.extension}</span>
                    <span className="text-slate-400">{ft.count} files · {formatBytes(ft.total_size_bytes)}</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-hover rounded-full">
                    <div className="h-full rounded-full transition-all" style={{ width: `${ft.percentage}%`, background: CHART_COLORS[i % CHART_COLORS.length] }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent uploads */}
        <div className="card">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-brand-400" /> Recent Uploads
            </h3>
            <Link href="/dashboard/files" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
              View all <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          {recent_uploads.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-8">No files yet — upload your first!</p>
          ) : (
            <div className="space-y-3">
              {recent_uploads.slice(0, 6).map(f => (
                <div key={f.id} className="flex items-center gap-3 p-2 rounded-xl hover:bg-surface-hover transition-colors">
                  <div className={`w-8 h-8 rounded-lg bg-surface-hover flex items-center justify-center flex-shrink-0 text-xs font-bold ${getFileColor(f.extension)}`}>
                    {(f.extension ?? "?").toUpperCase().slice(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white truncate">{f.original_name}</div>
                    <div className="text-xs text-slate-500">{formatBytes(f.size_bytes)} · {formatRelativeDate(f.created_at)}</div>
                  </div>
                  {f.is_encrypted && <Shield className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
