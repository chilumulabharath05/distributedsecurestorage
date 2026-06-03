// ── Auth ─────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  is_verified: boolean;
  storage_quota_bytes: number;
  storage_used_bytes: number;
  created_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ── Files ─────────────────────────────────────────────────────────────────────
export interface FileRecord {
  id: string;
  owner_id: string;
  original_name: string;
  mime_type: string | null;
  extension: string | null;
  size_bytes: number;
  sha256_hash: string | null;
  status: "uploading" | "processing" | "ready" | "error" | "deleted";
  is_encrypted: boolean;
  is_duplicate: boolean;
  storage_savings_bytes: number;
  is_public: boolean;
  download_count: number;
  folder_path: string;
  tags: string[];
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
  last_accessed_at: string | null;
  chunk_count: number;
  ipfs_folder_cid: string | null;
}

export interface UploadResult {
  file_id: string;
  original_name: string;
  size_bytes: number;
  sha256_hash: string | null;
  chunk_count: number;
  unique_chunks: number;
  duplicate_chunks: number;
  storage_savings_bytes: number;
  dedup_ratio: number;
  ipfs_cids: string[];
  status: string;
  message: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface StorageStats {
  total_files: number;
  total_size_bytes: number;
  storage_used_bytes: number;
  storage_quota_bytes: number;
  storage_used_percent: number;
  total_chunks: number;
  unique_chunks: number;
  duplicate_chunks: number;
  dedup_savings_bytes: number;
  dedup_efficiency_percent: number;
  ipfs_pinned_chunks: number;
}

export interface TrendPoint {
  date: string;
  upload_count: number;
  total_size_bytes: number;
  download_count: number;
}

export interface FileTypeBreakdown {
  extension: string;
  count: number;
  total_size_bytes: number;
  percentage: number;
}

export interface DashboardData {
  storage: StorageStats;
  recent_uploads: FileRecord[];
  upload_trend: TrendPoint[];
  file_types: FileTypeBreakdown[];
  total_downloads: number;
  total_shares: number;
}

// ── Sharing ───────────────────────────────────────────────────────────────────
export interface ShareLink {
  id: string;
  token: string;
  share_url: string;
  permission: "view" | "download";
  expires_at: string | null;
  max_downloads: number | null;
  download_count: number;
  is_active: boolean;
  label: string | null;
  created_at: string | null;
}

// ── UI ────────────────────────────────────────────────────────────────────────
export interface UploadQueueItem {
  id: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  result?: UploadResult;
  error?: string;
}

export type SortOrder = "asc" | "desc";
export type SortField = "created_at" | "original_name" | "size_bytes" | "download_count";
