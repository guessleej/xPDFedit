import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 自動附加 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 自動處理 401 → refresh
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const orig = err.config
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/token/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          orig.headers.Authorization = `Bearer ${data.access_token}`
          return api(orig)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

// ── Types ─────────────────────────────────────────────────────────────────────
export interface User {
  id: number
  username: string
  realm: string
  display_name: string
  email?: string
  roles: string[]
  is_superadmin: boolean
  enabled: boolean
  last_login?: string
  created_at: string
}

export interface Tool {
  tool_id: string
  name_zh: string
  name_en: string
  description_zh: string
  category: string
  icon: string
  color: string
  tags: string[]
  enabled: boolean
  multi_file: boolean
  params: ToolParam[]
}

export interface ToolParam {
  name: string
  type: string
  label_zh: string
  label_en: string
  required: boolean
  default?: unknown
  options?: { label: string; value: string }[]
  placeholder?: string
  min_val?: number
  max_val?: number
  description?: string
}

export interface Job {
  id: string
  tool_id: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  progress: number
  input_filename: string
  output_filename?: string
  content_type: string
  params: Record<string, unknown>
  error_message?: string
  metadata?: Record<string, unknown>
  duration_seconds?: number
  queued_at?: string
  started_at?: string
  finished_at?: string
  expires_at?: string
}

export interface Stats {
  users: number
  users_by_realm: Record<string, number>
  jobs: { total: number; done: number; failed: number; running: number }
  tools: number
  job_trend: { date: string; count: number }[]
}

// ── API functions ──────────────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string, realm = 'local') =>
    api.post('/auth/login', { username, password, realm }).then(r => r.data),
  logout: (refresh_token: string) =>
    api.post('/auth/logout', { refresh_token }).then(r => r.data),
  me: () => api.get<User>('/auth/me').then(r => r.data),
  listApiKeys: () => api.get('/auth/api-keys').then(r => r.data),
  createApiKey: (data: { name: string; scopes: string[]; expires_days?: number }) =>
    api.post('/auth/api-keys', data).then(r => r.data),
  revokeApiKey: (id: number) => api.delete(`/auth/api-keys/${id}`).then(r => r.data),
}

export const toolsApi = {
  list: () => api.get<{ tools: Tool[]; total: number }>('/tools').then(r => r.data),
  get: (id: string) => api.get<Tool>(`/tools/${id}`).then(r => r.data),
  submit: (toolId: string, files: File | File[], params: Record<string, unknown>) => {
    const fd = new FormData()
    const fileList = Array.isArray(files) ? files : [files]
    fileList.forEach(f => fd.append('files', f))
    fd.append('params', JSON.stringify(params))
    return api.post<{ job_id: string; status: string }>(`/tools/${toolId}/submit`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }).then(r => r.data)
  },
}

export const jobsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; tool_id?: string }) =>
    api.get<{ jobs: Job[]; total: number; page: number }>('/jobs', { params }).then(r => r.data),
  get: (id: string) => api.get<Job>(`/jobs/${id}`).then(r => r.data),
  download: (id: string) => `/api/v1/jobs/${id}/download`,
  cancel: (id: string) => api.delete(`/jobs/${id}`).then(r => r.data),
}

export const adminApi = {
  stats: () => api.get<Stats>('/admin/stats').then(r => r.data),
  listUsers: (params?: { page?: number; page_size?: number; q?: string }) =>
    api.get('/admin/users', { params }).then(r => r.data),
  createUser: (data: unknown) => api.post('/admin/users', data).then(r => r.data),
  updateUser: (id: number, data: unknown) => api.put(`/admin/users/${id}`, data).then(r => r.data),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`).then(r => r.data),
  listRoles: () => api.get('/admin/roles').then(r => r.data),
  health: () => api.get('/admin/system/health').then(r => r.data),
  listRealms: () => api.get('/admin/realms').then(r => r.data),
  createRealm: (data: unknown) => api.post('/admin/realms', data).then(r => r.data),
  updateRealm: (id: number, data: unknown) => api.put(`/admin/realms/${id}`, data).then(r => r.data),
  deleteRealm: (id: number) => api.delete(`/admin/realms/${id}`).then(r => r.data),
  testRealm: (id: number) => api.post(`/admin/realms/${id}/test`).then(r => r.data),
  listRealmDirectoryUsers: (id: number) => api.get<{ username: string; display_name: string; email: string | null; imported: boolean }[]>(`/admin/realms/${id}/users`).then(r => r.data),
  syncRealmUsers: (id: number, usernames: string[]) => api.post<{ imported: number; skipped: number }>(`/admin/realms/${id}/sync`, { usernames }).then(r => r.data),
}

export const realmApi = {
  listPublic: () => api.get<{ name: string; type: string; label: string }[]>('/auth/realms').then(r => r.data),
}
