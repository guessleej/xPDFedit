/**
 * xPDFedit API 客戶端
 * 統一管理所有 API 呼叫、JWT 注入、錯誤處理
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; detail?: unknown };
  meta?: { page?: number; total?: number; request_id?: string };
}

class ApiError extends Error {
  constructor(public code: string, message: string, public detail?: unknown) {
    super(message);
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...((opts.headers as Record<string, string>) ?? {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    ...opts,
  });

  if (res.status === 401) {
    // 嘗試 refresh
    const refreshed = await tryRefresh();
    if (!refreshed) {
      window.location.href = "/login";
      throw new ApiError("UNAUTHORIZED", "請重新登入");
    }
    return request<T>(method, path, body, opts);
  }

  const json: ApiResponse<T> = await res.json();

  if (!json.success || !res.ok) {
    throw new ApiError(
      json.error?.code ?? "UNKNOWN",
      json.error?.message ?? "發生未知錯誤",
      json.error?.detail
    );
  }

  return json.data as T;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/token/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const { data } = await res.json();
    localStorage.setItem("access_token", data.access_token);
    return true;
  } catch {
    return false;
  }
}

// ── Auth API ──────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string, realm = "local") =>
    request<{ access_token: string; refresh_token: string; user: User }>(
      "POST", "/auth/login", { username, password, realm }
    ),

  logout: () => request<void>("POST", "/auth/logout"),

  me: () => request<User>("GET", "/auth/me"),
};

// ── Tools API ─────────────────────────────────────────────
export const toolsApi = {
  list: () => request<Tool[]>("GET", "/tools"),

  get: (toolId: string) => request<Tool>("GET", `/tools/${toolId}`),

  submit: (toolId: string, formData: FormData) =>
    fetch(`${BASE_URL}/tools/${toolId}/submit`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      body: formData,
    }).then((r) => r.json()).then((r) => r.data as Job),
};

// ── Jobs API ──────────────────────────────────────────────
export const jobsApi = {
  list: (page = 1, pageSize = 20) =>
    request<Job[]>("GET", `/jobs?page=${page}&page_size=${pageSize}`),

  get: (jobId: string) => request<Job>("GET", `/jobs/${jobId}`),

  getResultUrl: (jobId: string) => request<{ url: string }>("GET", `/jobs/${jobId}/result`),

  cancel: (jobId: string) => request<void>("DELETE", `/jobs/${jobId}`),
};

// ── Types ─────────────────────────────────────────────────
export interface User {
  user_id: number;
  username: string;
  realm: string;
  display_name: string;
  email?: string;
  roles: string[];
}

export interface Tool {
  tool_id: string;
  name_zh: string;
  name_en: string;
  description_zh: string;
  category: string;
  icon: string;
  params: ToolParam[];
}

export interface ToolParam {
  name: string;
  type: string;
  label_zh: string;
  label_en: string;
  required: boolean;
  default?: unknown;
  options?: { label: string; value: string }[];
}

export interface Job {
  id: string;
  tool_id: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress?: number;
  created_at: string;
  finished_at?: string;
  error_message?: string;
}
