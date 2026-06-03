import axios, { AxiosProgressEvent } from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

// ── Request — attach token ─────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem("cloudstore-auth");
      if (raw) {
        const { state } = JSON.parse(raw);
        if (state?.accessToken) {
          config.headers.Authorization = `Bearer ${state.accessToken}`;
        }
      }
    } catch {}
  }
  return config;
});

// ── Response — handle 401 / token refresh ─────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const raw = localStorage.getItem("cloudstore-auth");
        if (raw) {
          const { state } = JSON.parse(raw);
          if (state?.refreshToken) {
            const { data } = await axios.post(`${BASE}/auth/refresh`, {
              refresh_token: state.refreshToken,
            }, { headers: { Authorization: `Bearer ${state.accessToken}` } });
            const newState = {
              ...state,
              accessToken: data.access_token,
              refreshToken: data.refresh_token,
            };
            localStorage.setItem("cloudstore-auth", JSON.stringify({ state: newState }));
            original.headers.Authorization = `Bearer ${data.access_token}`;
            return api(original);
          }
        }
      } catch {
        if (typeof window !== "undefined") {
          localStorage.removeItem("cloudstore-auth");
          window.location.href = "/auth/login";
        }
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth API ──────────────────────────────────────────────────────────────
export const authApi = {
  register:       (d: any) => api.post("/auth/register", d),
  login:          (d: any) => api.post("/auth/login", d),
  logout:         ()       => api.post("/auth/logout"),
  me:             ()       => api.get("/auth/me"),
  updateProfile:  (d: any) => api.patch("/auth/me", d),
  changePassword: (d: any) => api.post("/auth/change-password", d),
};

// ── Files API ─────────────────────────────────────────────────────────────
export const filesApi = {
  upload: (
    form: FormData,
    onProgress?: (p: number) => void
  ) =>
    api.post("/files/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e: AxiosProgressEvent) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    }),

  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    extension?: string;
    folder_path?: string;
    sort_by?: string;
    sort_order?: string;
  }) => api.get("/files/", { params }),

  get:      (id: string) => api.get(`/files/${id}`),
  stats:    ()           => api.get("/files/stats"),
  update:   (id: string, d: any) => api.patch(`/files/${id}`, d),
  delete:   (id: string) => api.delete(`/files/${id}`),
  chunks:   (id: string) => api.get(`/files/${id}/chunks`),

  download: (id: string) =>
    api.get(`/files/${id}/download`, { responseType: "blob" }),

  preview: (id: string) =>
    api.get(`/files/${id}/preview`, { responseType: "blob" }),
};

// ── Analytics API ─────────────────────────────────────────────────────────
export const analyticsApi = {
  dashboard: ()          => api.get("/analytics/dashboard"),
  activity:  (p?: any)  => api.get("/analytics/activity", { params: p }),
};

// ── Sharing API ───────────────────────────────────────────────────────────
export const sharingApi = {
  create:   (d: any)    => api.post("/share/", d),
  myLinks:  (p?: any)   => api.get("/share/my-links", { params: p }),
  revoke:   (id: string) => api.delete(`/share/${id}`),
  access:   (token: string, password?: string) =>
    api.get(`/share/access/${token}`, { params: { password } }),
};
