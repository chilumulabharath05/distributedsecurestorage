"use client";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { GitMerge, HardDrive, TrendingUp, Zap, Database, Shield } from "lucide-react";
import { analyticsApi } from "@/lib/api";
import { formatBytes, formatPercent, getFileColor } from "@/lib/utils";
import type { DashboardData } from "@/types";
import { format } from "date-fns";

const COLORS = ["#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444","#ec4899","#84cc16"];

const ChartTip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 rounded-xl text-xs border border-surface-border">
      <p className="text-slate-400 mb-1.5">{label}</p>
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-2" style={{ color: p.color || p.fill }}>
          <span>{p.name}:</span>
          <span className="text-white font-medium">
            {typeof p.value === "number" && (p.name?.includes("size") || p.name?.includes("bytes") || p.name?.includes("Bytes"))
              ? formatBytes(p.value)
              : p.value?.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
};

function MetricCard({ icon: Icon, label, value, sub, color }: any) {
  return (
    <div className="card flex flex-col gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-white/80 mt-0.5">{label}</div>
        {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: () => analyticsApi.dashboard().then(r => r.data),
    refetchInterval: 30_000,
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array(4).fill(0).map((_,i)=><div key={i} className="h-32 glass rounded-2xl"/>)}
        </div>
        {Array(3).fill(0).map((_,i)=><div key={i} className="h-72 glass rounded-2xl"/>)}
      </div>
    );
  }

  const { storage, upload_trend, file_types } = data;

  const storagePie = [
    { name: "Used",  value: storage.storage_used_bytes },
    { name: "Free",  value: Math.max(0, storage.storage_quota_bytes - storage.storage_used_bytes) },
  ];
  const chunkPie = [
    { name: "Unique",     value: storage.unique_chunks },
    { name: "Duplicates", value: storage.duplicate_chunks },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Analytics</h2>
        <p className="text-slate-400 text-sm mt-0.5">Deep insights into your storage efficiency</p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Database}  label="Total Chunks"       value={storage.total_chunks.toLocaleString()}          sub={`${storage.unique_chunks} unique`}                      color="bg-brand-600/20 text-brand-400" />
        <MetricCard icon={GitMerge}  label="Dedup Efficiency"   value={formatPercent(storage.dedup_efficiency_percent)} sub={`${formatBytes(storage.dedup_savings_bytes)} saved`}   color="bg-emerald-600/20 text-emerald-400" />
        <MetricCard icon={Shield}    label="IPFS Pinned"         value={storage.ipfs_pinned_chunks.toLocaleString()}     sub="encrypted chunks"                                       color="bg-purple-600/20 text-purple-400" />
        <MetricCard icon={HardDrive} label="Storage Utilization" value={formatPercent(storage.storage_used_percent)}    sub={`${formatBytes(storage.storage_used_bytes)} / ${formatBytes(storage.storage_quota_bytes)}`} color="bg-orange-600/20 text-orange-400" />
      </div>

      {/* Upload trend */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-brand-400" /> Upload & Download Trend (30 Days)
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={upload_trend} margin={{ left: -15, right: 0 }}>
            <defs>
              <linearGradient id="upG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="dlG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#10b981" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false}/>
            <XAxis dataKey="date" tick={{ fill:"#64748b", fontSize:11 }}
              tickFormatter={v=>{ try { return format(new Date(v),"MMM d"); } catch { return v; } }}/>
            <YAxis tick={{ fill:"#64748b", fontSize:11 }}/>
            <Tooltip content={<ChartTip/>}/>
            <Legend wrapperStyle={{ fontSize:"12px", color:"#94a3b8" }}/>
            <Area type="monotone" dataKey="upload_count"   name="Uploads"   stroke="#3b82f6" strokeWidth={2} fill="url(#upG)" dot={false}/>
            <Area type="monotone" dataKey="download_count" name="Downloads" stroke="#10b981" strokeWidth={2} fill="url(#dlG)" dot={false}/>
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Size + pie charts */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Daily size */}
        <div className="card lg:col-span-1">
          <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400"/> Daily Data Volume
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={upload_trend.slice(-14)} margin={{ left:-15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false}/>
              <XAxis dataKey="date" tick={{ fill:"#64748b", fontSize:10 }}
                tickFormatter={v=>{ try { return format(new Date(v),"d"); } catch { return v; } }}/>
              <YAxis tick={{ fill:"#64748b", fontSize:10 }} tickFormatter={v=>formatBytes(v,0)}/>
              <Tooltip content={<ChartTip/>}/>
              <Bar dataKey="total_size_bytes" name="Size (bytes)" fill="#3b82f6" radius={[3,3,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Storage pie */}
        <div className="card">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-purple-400"/> Storage Usage
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={storagePie} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={4} dataKey="value">
                <Cell fill="#3b82f6"/>
                <Cell fill="#334155"/>
              </Pie>
              <Tooltip content={<ChartTip/>}/>
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center mt-1">
            <div className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
              {formatPercent(storage.storage_used_percent)}
            </div>
            <div className="text-xs text-slate-400">{formatBytes(storage.storage_used_bytes)} used</div>
          </div>
        </div>

        {/* Chunk dedup pie */}
        <div className="card">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <GitMerge className="w-4 h-4 text-emerald-400"/> Chunk Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={chunkPie} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={4} dataKey="value">
                <Cell fill="#3b82f6"/>
                <Cell fill="#10b981"/>
              </Pie>
              <Tooltip content={<ChartTip/>}/>
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:"11px", color:"#94a3b8" }}/>
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center mt-1">
            <div className="text-2xl font-bold text-emerald-400">
              {formatPercent(storage.dedup_efficiency_percent)}
            </div>
            <div className="text-xs text-slate-400">{formatBytes(storage.dedup_savings_bytes)} saved</div>
          </div>
        </div>
      </div>

      {/* File type breakdown */}
      <div className="card">
        <h3 className="text-base font-semibold text-white mb-5">File Type Breakdown</h3>
        {data.file_types.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">Upload files to see breakdown</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
            {data.file_types.map((ft, i) => (
              <div key={ft.extension}>
                <div className="flex items-center justify-between text-sm mb-1.5">
                  <span className={`font-medium uppercase ${getFileColor(ft.extension)}`}>.{ft.extension}</span>
                  <span className="text-slate-400 text-xs">{ft.count} files · {formatBytes(ft.total_size_bytes)}</span>
                </div>
                <div className="w-full h-1.5 bg-surface-hover rounded-full">
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{ width:`${ft.percentage}%`, background: COLORS[i % COLORS.length] }}/>
                </div>
                <div className="text-right text-xs text-slate-500 mt-0.5">{ft.percentage.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
