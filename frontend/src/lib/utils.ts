import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number, decimals = 1): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return format(new Date(dateStr), "MMM d, yyyy");
  } catch {
    return "—";
  }
}

export function formatRelativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
  } catch {
    return "—";
  }
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function getMimeCategory(mime: string | null): string {
  if (!mime) return "file";
  if (mime.startsWith("image/")) return "image";
  if (mime.startsWith("video/")) return "video";
  if (mime.startsWith("audio/")) return "audio";
  if (mime.includes("pdf")) return "pdf";
  if (mime.startsWith("text/")) return "text";
  if (mime.includes("zip") || mime.includes("tar") || mime.includes("gz")) return "archive";
  if (mime.includes("spreadsheet") || mime.includes("excel")) return "spreadsheet";
  if (mime.includes("word") || mime.includes("document")) return "document";
  if (mime.includes("presentation")) return "presentation";
  return "file";
}

export function getFileColor(ext: string | null): string {
  const map: Record<string, string> = {
    pdf: "text-red-400",
    jpg: "text-yellow-400", jpeg: "text-yellow-400",
    png: "text-blue-400", gif: "text-blue-400", webp: "text-blue-400",
    mp4: "text-purple-400", mov: "text-purple-400", webm: "text-purple-400",
    mp3: "text-pink-400", wav: "text-pink-400",
    zip: "text-orange-400", tar: "text-orange-400", gz: "text-orange-400",
    doc: "text-sky-400", docx: "text-sky-400",
    xls: "text-green-400", xlsx: "text-green-400",
    txt: "text-slate-400", md: "text-slate-400",
    py: "text-yellow-300", js: "text-yellow-300", ts: "text-blue-300",
    json: "text-green-300",
  };
  return map[ext?.toLowerCase() ?? ""] ?? "text-slate-400";
}

export function truncateHash(hash: string, chars = 8): string {
  if (!hash) return "";
  return `${hash.slice(0, chars)}...${hash.slice(-4)}`;
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
