"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sharingApi } from "@/lib/api";
import {
  Share2, Copy, Trash2, Check, ExternalLink,
  Clock, Download, Shield, AlertCircle
} from "lucide-react";
import { formatRelativeDate, copyToClipboard, cn } from "@/lib/utils";
import type { ShareLink } from "@/types";
import { useState } from "react";
import toast from "react-hot-toast";
import { format, isPast } from "date-fns";

function LinkCard({ link, onRevoke }: { link: ShareLink; onRevoke: () => void }) {
  const [copied, setCopied] = useState(false);
  const url = `${typeof window !== "undefined" ? window.location.origin : ""}${link.share_url}`;
  const expired = link.expires_at ? isPast(new Date(link.expires_at)) : false;
  const limitReached = link.max_downloads ? link.download_count >= link.max_downloads : false;
  const active = link.is_active && !expired && !limitReached;

  const copy = async () => {
    await copyToClipboard(url);
    setCopied(true);
    toast.success("Link copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("card transition-all", !active && "opacity-60")}>
      {/* Status bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className={cn("w-2 h-2 rounded-full", active ? "bg-emerald-400 animate-pulse" : "bg-slate-500")}/>
          <span className={cn("text-xs font-medium", active ? "text-emerald-400" : "text-slate-500")}>
            {expired ? "Expired" : limitReached ? "Limit Reached" : link.is_active ? "Active" : "Revoked"}
          </span>
        </div>
        <span className={cn("badge", link.permission === "download" ? "badge-blue" : "badge-slate")}>
          {link.permission === "download" ? <Download className="w-2.5 h-2.5"/> : <Shield className="w-2.5 h-2.5"/>}
          {link.permission}
        </span>
      </div>

      {/* Label */}
      {link.label && <p className="text-sm font-medium text-white mb-3">{link.label}</p>}

      {/* URL */}
      <div className="flex items-center gap-2 bg-surface-hover rounded-xl px-3 py-2.5 mb-4">
        <ExternalLink className="w-3.5 h-3.5 text-slate-500 flex-shrink-0"/>
        <span className="text-xs text-slate-300 font-mono flex-1 truncate">{url}</span>
        <button onClick={copy}
          className={cn("flex-shrink-0 p-1 rounded-lg transition-colors",
            copied ? "text-emerald-400" : "text-slate-500 hover:text-white")}>
          {copied ? <Check className="w-3.5 h-3.5"/> : <Copy className="w-3.5 h-3.5"/>}
        </button>
      </div>

      {/* Meta */}
      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Downloads</div>
          <div className="text-white font-medium">
            {link.download_count}
            {link.max_downloads && <span className="text-slate-400"> / {link.max_downloads}</span>}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Expires</div>
          <div className="text-white font-medium flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-400"/>
            {link.expires_at
              ? expired
                ? <span className="text-red-400">{format(new Date(link.expires_at), "MMM d")}</span>
                : format(new Date(link.expires_at), "MMM d, HH:mm")
              : "Never"}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Created</div>
          <div className="text-white font-medium">{formatRelativeDate(link.created_at)}</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-4 border-t border-surface-border">
        <button onClick={copy} className="btn-secondary flex-1 btn-sm gap-1.5">
          {copied ? <Check className="w-3.5 h-3.5"/> : <Copy className="w-3.5 h-3.5"/>}
          {copied ? "Copied!" : "Copy Link"}
        </button>
        {link.is_active && (
          <button onClick={onRevoke} className="btn-danger btn-sm gap-1.5">
            <Trash2 className="w-3.5 h-3.5"/> Revoke
          </button>
        )}
      </div>
    </div>
  );
}

export default function SharedLinksPage() {
  const qc = useQueryClient();

  const { data: links = [], isLoading } = useQuery<ShareLink[]>({
    queryKey: ["share-links"],
    queryFn: () => sharingApi.myLinks().then(r => r.data),
    refetchInterval: 30_000,
  });

  const revoke = useMutation({
    mutationFn: (id: string) => sharingApi.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["share-links"] });
      toast.success("Share link revoked");
    },
    onError: () => toast.error("Failed to revoke link"),
  });

  const active = links.filter(l =>
    l.is_active &&
    !(l.expires_at && isPast(new Date(l.expires_at))) &&
    !(l.max_downloads && l.download_count >= l.max_downloads)
  );
  const inactive = links.filter(l => !active.includes(l));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Shared Links</h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {active.length} active · {inactive.length} expired/revoked
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array(6).fill(0).map((_,i)=><div key={i} className="h-52 glass rounded-2xl animate-pulse"/>)}
        </div>
      ) : links.length === 0 ? (
        <div className="text-center py-24">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/15 flex items-center justify-center mx-auto mb-4">
            <Share2 className="w-8 h-8 text-brand-400"/>
          </div>
          <h3 className="text-white font-semibold text-lg">No shared links yet</h3>
          <p className="text-slate-400 text-sm mt-2">
            Go to your files and click "Share" to generate a secure link.
          </p>
        </div>
      ) : (
        <>
          {active.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-3">Active Links ({active.length})</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {active.map(l => (
                  <LinkCard key={l.id} link={l} onRevoke={() => revoke.mutate(l.id)}/>
                ))}
              </div>
            </div>
          )}
          {inactive.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-3">Expired / Revoked ({inactive.length})</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {inactive.map(l => (
                  <LinkCard key={l.id} link={l} onRevoke={() => revoke.mutate(l.id)}/>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
