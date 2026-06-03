"use client";
import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import {
  Upload, Search, Download, Trash2, Share2, Eye,
  File, FileText, Image, Video, Music, Archive,
  Shield, GitMerge, MoreVertical, Copy, Check,
  ChevronDown, SortAsc, SortDesc, Filter
} from "lucide-react";
import { filesApi, sharingApi } from "@/lib/api";
import {
  formatBytes, formatRelativeDate, getFileColor,
  getMimeCategory, downloadBlob, copyToClipboard, cn
} from "@/lib/utils";
import type { FileRecord, UploadQueueItem } from "@/types";
import toast from "react-hot-toast";
import { AnimatePresence, motion } from "framer-motion";

// ── File Icon ─────────────────────────────────────────────────────────────────
function FileIcon({ mime, ext, className }: { mime?: string|null; ext?: string|null; className?: string }) {
  const cat = getMimeCategory(mime ?? "");
  const cls = `${className ?? "w-5 h-5"} ${getFileColor(ext ?? "")}`;
  if (cat === "image") return <Image className={cls} />;
  if (cat === "video") return <Video className={cls} />;
  if (cat === "audio") return <Music className={cls} />;
  if (cat === "archive") return <Archive className={cls} />;
  if (cat === "text" || cat === "document") return <FileText className={cls} />;
  return <File className={cls} />;
}

// ── Upload Zone ───────────────────────────────────────────────────────────────
function UploadZone({ onDone }: { onDone: () => void }) {
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);

  const onDrop = useCallback(async (accepted: File[]) => {
    const items: UploadQueueItem[] = accepted.map(f => ({
      id: crypto.randomUUID(), file: f, progress: 0, status: "pending",
    }));
    setQueue(items);

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: "uploading" } : q));
      try {
        const form = new FormData();
        form.append("file", item.file);
        const { data } = await filesApi.upload(form, p => {
          setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, progress: p } : q));
        });
        setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: "done", progress: 100, result: data } : q));
        toast.success(`✅ ${item.file.name} — saved ${formatBytes(data.storage_savings_bytes)} via dedup`);
      } catch (err: any) {
        setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: "error", error: err.response?.data?.detail ?? "Upload failed" } : q));
        toast.error(err.response?.data?.detail ?? "Upload failed");
      }
    }
    onDone();
    setTimeout(() => setQueue([]), 5000);
  }, [onDone]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: true, maxSize: 500 * 1024 * 1024,
  });

  return (
    <div className="space-y-4">
      <div {...getRootProps()} className={cn("upload-zone p-12 text-center", isDragActive && "active")}>
        <input {...getInputProps()} />
        <motion.div animate={{ scale: isDragActive ? 1.04 : 1 }} className="flex flex-col items-center gap-4">
          <div className={cn("w-16 h-16 rounded-2xl flex items-center justify-center transition-all", isDragActive ? "bg-brand-600 shadow-glow-lg" : "bg-brand-600/15 border border-brand-500/25")}>
            <Upload className={cn("w-7 h-7", isDragActive ? "text-white" : "text-brand-400")} />
          </div>
          <div>
            <p className="text-white font-semibold text-lg">{isDragActive ? "Drop files here…" : "Drag & drop files, or click to browse"}</p>
            <p className="text-slate-400 text-sm mt-1">Any file type · Max 500 MB · Encrypted automatically</p>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><Shield className="w-3.5 h-3.5 text-brand-400" /> AES-256</span>
            <span className="flex items-center gap-1.5"><GitMerge className="w-3.5 h-3.5 text-emerald-400" /> Deduplicated</span>
          </div>
        </motion.div>
      </div>

      <AnimatePresence>
        {queue.map((item, i) => (
          <motion.div key={item.id} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="glass rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-brand-600/20 flex items-center justify-center flex-shrink-0">
                <File className="w-4 h-4 text-brand-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white truncate">{item.file.name}</div>
                <div className="text-xs text-slate-500">{formatBytes(item.file.size)}</div>
              </div>
              <span className={cn("text-xs font-medium",
                item.status === "done" ? "text-emerald-400" :
                item.status === "error" ? "text-red-400" : "text-brand-400")}>
                {item.status === "done" ? "Done" : item.status === "error" ? "Failed" : `${item.progress}%`}
              </span>
            </div>
            {item.status === "uploading" && (
              <div className="w-full h-1 bg-surface-hover rounded-full overflow-hidden">
                <motion.div className="h-full progress-fill rounded-full" animate={{ width: `${item.progress}%` }} transition={{ duration: 0.3 }} />
              </div>
            )}
            {item.status === "done" && item.result && (
              <div className="flex gap-3 mt-2 text-xs text-slate-400">
                <span className="text-emerald-400">✓ {item.result.chunk_count} chunks</span>
                <span className="text-emerald-400">✓ {item.result.unique_chunks} unique</span>
                <span className="text-emerald-400">✓ {formatBytes(item.result.storage_savings_bytes)} saved</span>
              </div>
            )}
            {item.status === "error" && <p className="text-xs text-red-400 mt-1">{item.error}</p>}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// ── File Card ─────────────────────────────────────────────────────────────────
function FileCard({ file, onDelete, onShare }: { file: FileRecord; onDelete: () => void; onShare: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleDownload = async () => {
    try {
      const { data } = await filesApi.download(file.id);
      downloadBlob(data, file.original_name);
      toast.success("Download started");
    } catch { toast.error("Download failed"); }
  };

  const copyHash = async () => {
    if (!file.sha256_hash) return;
    await copyToClipboard(file.sha256_hash);
    setCopied(true);
    toast.success("Hash copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} className="card group relative">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center flex-shrink-0">
          <FileIcon mime={file.mime_type} ext={file.extension} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white truncate" title={file.original_name}>{file.original_name}</div>
          <div className="text-xs text-slate-500 mt-0.5">{formatBytes(file.size_bytes)} · {formatRelativeDate(file.created_at)}</div>
        </div>
        <button onClick={() => setMenuOpen(!menuOpen)} className="w-7 h-7 rounded-lg hover:bg-surface-hover flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
          <MoreVertical className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Dropdown */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div initial={{ opacity: 0, scale: 0.95, y: -4 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: -4 }}
            className="absolute right-4 top-14 z-20 glass rounded-xl p-1.5 min-w-[160px] shadow-card border border-surface-border">
            {[
              { icon: Download, label: "Download", onClick: () => { handleDownload(); setMenuOpen(false); } },
              { icon: Share2,   label: "Share",    onClick: () => { onShare(); setMenuOpen(false); } },
              { icon: copied ? Check : Copy, label: copied ? "Copied!" : "Copy Hash", onClick: () => { copyHash(); setMenuOpen(false); } },
              { icon: Trash2,   label: "Delete",   onClick: () => { onDelete(); setMenuOpen(false); }, danger: true },
            ].map(({ icon: Icon, label, onClick, danger }: any) => (
              <button key={label} onClick={onClick}
                className={cn("w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                  danger ? "text-red-400 hover:bg-red-500/10" : "text-slate-300 hover:bg-surface-hover hover:text-white")}>
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {file.is_encrypted && <span className="badge-blue"><Shield className="w-2.5 h-2.5" /> Encrypted</span>}
        {file.storage_savings_bytes > 0 && <span className="badge-green"><GitMerge className="w-2.5 h-2.5" /> {formatBytes(file.storage_savings_bytes)} saved</span>}
        {file.chunk_count > 0 && <span className="badge-slate">{file.chunk_count} chunks</span>}
      </div>

      {/* Hash */}
      {file.sha256_hash && (
        <button onClick={copyHash} className="w-full flex items-center gap-2 bg-surface-hover rounded-lg px-3 py-2 text-left hover:bg-surface-border transition-colors">
          <span className="text-xs text-slate-400 font-mono truncate">{file.sha256_hash.slice(0, 24)}…</span>
          {copied ? <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" /> : <Copy className="w-3 h-3 text-slate-500 flex-shrink-0" />}
        </button>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-surface-border">
        <button onClick={handleDownload} className="flex-1 btn btn-secondary btn-sm gap-1.5">
          <Download className="w-3.5 h-3.5" /> Download
        </button>
        <button onClick={onShare} className="flex-1 btn btn-secondary btn-sm gap-1.5">
          <Share2 className="w-3.5 h-3.5" /> Share
        </button>
        <button onClick={onDelete} className="btn btn-danger btn-sm w-8">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </motion.div>
  );
}

// ── Share Modal ───────────────────────────────────────────────────────────────
function ShareModal({ fileId, onClose }: { fileId: string; onClose: () => void }) {
  const [hours, setHours] = useState(24);
  const [maxDl, setMaxDl] = useState<number | "">("");
  const [label, setLabel] = useState("");
  const [link, setLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const create = async () => {
    setLoading(true);
    try {
      const { data } = await sharingApi.create({ file_id: fileId, expires_hours: hours, max_downloads: maxDl || undefined, label: label || undefined });
      setLink(`${window.location.origin}${data.share_url}`);
      toast.success("Share link created!");
    } catch { toast.error("Failed to create share link"); }
    setLoading(false);
  };

  const copy = async () => {
    await copyToClipboard(link);
    setCopied(true);
    toast.success("Link copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}>
      <motion.div initial={{ scale: 0.92, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.92, y: 12 }}
        className="card w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-white mb-5">Share File</h3>
        {!link ? (
          <div className="space-y-4">
            <div>
              <label className="label">Expires in</label>
              <select value={hours} onChange={e => setHours(Number(e.target.value))} className="input">
                {[1,6,12,24,48,72,168].map(h => <option key={h} value={h}>{h < 24 ? `${h}h` : `${h/24}d`}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Max downloads (optional)</label>
              <input type="number" min={1} value={maxDl} onChange={e => setMaxDl(e.target.value ? Number(e.target.value) : "")} placeholder="Unlimited" className="input" />
            </div>
            <div>
              <label className="label">Label (optional)</label>
              <input type="text" value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Shared with team" className="input" />
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
              <button onClick={create} disabled={loading} className="btn-primary flex-1">{loading ? "Creating…" : "Generate Link"}</button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 bg-surface-hover rounded-xl px-3 py-3">
              <span className="text-xs text-slate-300 font-mono flex-1 truncate">{link}</span>
              <button onClick={copy} className={cn("btn btn-sm flex-shrink-0", copied ? "btn-primary" : "btn-secondary")}>
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
            <button onClick={onClose} className="btn-secondary w-full">Done</button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function FilesPage() {
  const qc = useQueryClient();
  const [view, setView] = useState<"grid" | "upload">("grid");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc"|"desc">("desc");
  const [shareId, setShareId] = useState<string|null>(null);

  const { data: files = [], isLoading } = useQuery<FileRecord[]>({
    queryKey: ["files", search, sortBy, sortOrder],
    queryFn: () => filesApi.list({ search: search||undefined, sort_by: sortBy, sort_order: sortOrder }).then(r => r.data),
    refetchInterval: 15_000,
  });

  const { data: stats } = useQuery({
    queryKey: ["file-stats"],
    queryFn: () => filesApi.stats().then(r => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => filesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["files"] });
      qc.invalidateQueries({ queryKey: ["file-stats"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("File deleted");
    },
    onError: () => toast.error("Delete failed"),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">My Files</h2>
          <p className="text-slate-400 text-sm mt-0.5">{stats?.total_files ?? 0} files · {formatBytes(stats?.total_size_bytes ?? 0)}</p>
        </div>
        <button onClick={() => setView(v => v === "upload" ? "grid" : "upload")}
          className={view === "upload" ? "btn-secondary" : "btn-primary"}>
          {view === "upload" ? "← Back to Files" : <><Upload className="w-4 h-4" /> Upload Files</>}
        </button>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Files",         value: stats?.total_files ?? 0,                 cls: "text-white" },
          { label: "Unique Chunks", value: stats?.unique_chunks ?? 0,               cls: "text-brand-400" },
          { label: "Storage Saved", value: formatBytes(stats?.dedup_savings_bytes ?? 0), cls: "text-emerald-400" },
        ].map(({ label, value, cls }) => (
          <div key={label} className="glass rounded-xl px-4 py-3">
            <div className={`text-lg font-bold ${cls}`}>{value}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {view === "upload" ? (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <UploadZone onDone={() => {
              qc.invalidateQueries({ queryKey: ["files"] });
              qc.invalidateQueries({ queryKey: ["file-stats"] });
              qc.invalidateQueries({ queryKey: ["dashboard"] });
            }} />
          </motion.div>
        ) : (
          <motion.div key="grid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
            {/* Toolbar */}
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search files…" className="input pl-10" />
              </div>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="input w-44">
                <option value="created_at">Date</option>
                <option value="original_name">Name</option>
                <option value="size_bytes">Size</option>
                <option value="download_count">Downloads</option>
              </select>
              <button onClick={() => setSortOrder(o => o === "asc" ? "desc" : "asc")} className="btn-secondary w-10 h-10 p-0 flex items-center justify-center">
                {sortOrder === "asc" ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
              </button>
            </div>

            {/* Grid */}
            {isLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array(6).fill(0).map((_,i) => <div key={i} className="h-52 glass rounded-2xl animate-pulse" />)}
              </div>
            ) : files.length === 0 ? (
              <div className="text-center py-24">
                <div className="w-16 h-16 rounded-2xl bg-brand-600/15 flex items-center justify-center mx-auto mb-4">
                  <FolderOpen className="w-8 h-8 text-brand-400" />
                </div>
                <h3 className="text-white font-semibold text-lg">{search ? "No files found" : "No files yet"}</h3>
                <p className="text-slate-400 text-sm mt-2">{search ? "Try a different search term" : "Upload your first file to get started"}</p>
                {!search && <button onClick={() => setView("upload")} className="btn-primary mt-4"><Upload className="w-4 h-4" /> Upload Files</button>}
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <AnimatePresence>
                  {files.map(f => (
                    <FileCard key={f.id} file={f}
                      onDelete={() => deleteMutation.mutate(f.id)}
                      onShare={() => setShareId(f.id)} />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {shareId && <ShareModal fileId={shareId} onClose={() => setShareId(null)} />}
      </AnimatePresence>
    </div>
  );
}

// ── Missing icon import fix ───────────────────────────────────────────────────
function FolderOpen({ className }: { className?: string }) {
  return <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.75h16.5m-16.5 0a2.25 2.25 0 01-2.25-2.25V6a2.25 2.25 0 012.25-2.25h4.5l2.25 2.25H18a2.25 2.25 0 012.25 2.25v1.5m-16.5 0v9a2.25 2.25 0 002.25 2.25h12a2.25 2.25 0 002.25-2.25v-9" /></svg>;
}
