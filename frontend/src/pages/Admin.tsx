import { useState } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import {
  Settings, Users, Shield, Activity, Plus, Pencil, Trash2,
  Loader2, CheckCircle, X, Search, Server, Wifi,
  Globe, Lock, ChevronDown, ChevronUp, Download,
} from 'lucide-react'
import { adminApi } from '../lib/api'
import { formatDate } from '../lib/utils'
import toast from 'react-hot-toast'

const TABS = [
  { id: 'overview', label: '系統概覽', icon: Activity },
  { id: 'users',    label: '使用者管理', icon: Users },
  { id: 'realms',   label: '認證網域', icon: Globe },
  { id: 'roles',    label: '角色權限', icon: Shield },
]

const ROLE_OPTS = ['viewer', 'operator', 'manager', 'admin']
const ROLE_LABELS: Record<string, string> = {
  superadmin: '超級管理員', admin: '管理員', manager: '管理者',
  operator: '操作員', viewer: '檢視者', guest: '訪客',
}

const REALM_TYPE_BADGE: Record<string, string> = {
  local: 'badge-gray',
  ldap:  'badge-blue',
  ad:    'badge-purple',
}
const REALM_TYPE_LABEL: Record<string, string> = {
  local: '本機',
  ldap:  'LDAP',
  ad:    'AD',
}

const PERM_LABEL: Record<string, string> = {
  '*': '所有權限',
  'tool:*': '工具（全部）', 'tool:read': '工具（檢視）', 'tool:execute': '工具（執行）',
  'document:*': '文件（全部）', 'document:read': '文件（檢視）', 'document:create': '文件（新增）', 'document:delete': '文件（刪除）',
  'job:*': '作業（全部）', 'job:read': '作業（檢視）',
  'user:*': '使用者管理', 'settings:*': '系統設定',
  'audit:read': '稽核（檢視）', 'audit:export': '稽核（匯出）',
}

export function Admin() {
  const [tab, setTab] = useState('overview')
  const [userSearch, setUserSearch] = useState('')
  const [userPage, setUserPage] = useState(1)
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [editUser, setEditUser] = useState<any | null>(null)
  const [showCreateRealm, setShowCreateRealm] = useState(false)
  const [editRealm, setEditRealm] = useState<any | null>(null)
  const [browseRealm, setBrowseRealm] = useState<any | null>(null)

  const qc = useQueryClient()

  const { data: stats } = useQuery({ queryKey: ['admin-stats'], queryFn: adminApi.stats, refetchInterval: 30000 })
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: adminApi.health, refetchInterval: 60000 })
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users', userPage, userSearch],
    queryFn: () => adminApi.listUsers({ page: userPage, page_size: 15, q: userSearch || undefined }),
    enabled: tab === 'users',
  })
  const { data: roles } = useQuery({
    queryKey: ['admin-roles'],
    queryFn: adminApi.listRoles,
    enabled: tab === 'roles',
  })
  const { data: realms, isLoading: realmsLoading } = useQuery({
    queryKey: ['admin-realms'],
    queryFn: adminApi.listRealms,
    enabled: tab === 'realms',
  })

  const deleteUserMut = useMutation({
    mutationFn: (id: number) => adminApi.deleteUser(id),
    onSuccess: () => { toast.success('使用者已刪除'); qc.invalidateQueries({ queryKey: ['admin-users'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail || '刪除失敗'),
  })

  const deleteRealmMut = useMutation({
    mutationFn: (id: number) => adminApi.deleteRealm(id),
    onSuccess: () => { toast.success('認證網域已刪除'); qc.invalidateQueries({ queryKey: ['admin-realms'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail || '刪除失敗'),
  })

  const testRealmMut = useMutation({
    mutationFn: (id: number) => adminApi.testRealm(id),
    onSuccess: (data: any) => {
      if (data.success) toast.success(data.message || '連線成功')
      else toast.error(data.message || '連線失敗')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || '測試失敗'),
  })

  return (
    <div className="space-y-6 animate-in">
      {/* 頁首 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Settings className="w-5 h-5 text-brand-600" />系統管理
          </h1>
          <p className="page-subtitle">使用者管理、認證網域、角色權限</p>
        </div>
        {tab === 'users' && (
          <button onClick={() => setShowCreateUser(true)} className="btn-primary">
            <Plus className="w-4 h-4" />新增使用者
          </button>
        )}
        {tab === 'realms' && (
          <button onClick={() => setShowCreateRealm(true)} className="btn-primary">
            <Plus className="w-4 h-4" />新增網域
          </button>
        )}
      </div>

      {/* Tab 選單 */}
      <div className="flex border-b border-slate-200 gap-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === id
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {/* ── 系統概覽 ── */}
      {tab === 'overview' && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: '總使用者', value: stats?.users ?? '—', sub: `本機 ${stats?.users_by_realm?.local ?? 0}  ·  AD/LDAP ${(stats?.users_by_realm?.ad ?? 0) + (stats?.users_by_realm?.ldap ?? 0)}` },
              { label: '總作業數', value: stats?.jobs.total ?? '—', sub: '累計提交' },
              { label: '完成率', value: stats ? `${Math.round(stats.jobs.done / (stats.jobs.total || 1) * 100)}%` : '—', sub: '成功率' },
              { label: '工具數量', value: stats?.tools ?? '—', sub: '已啟用' },
            ].map(({ label, value, sub }) => (
              <div key={label} className="card p-5">
                <p className="text-2xl font-bold text-slate-900">{value}</p>
                <p className="text-sm text-slate-700 mt-0.5">{label}</p>
                <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
              </div>
            ))}
          </div>

          <div className="card p-5">
            <h2 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />系統健康狀態
            </h2>
            {health ? (
              <div className="space-y-2">
                {[
                  { key: '服務狀態', value: health.status === 'ok' ? '正常運行' : '異常', ok: health.status === 'ok' },
                  { key: '已載入工具', value: `${health.tools_loaded} 個`, ok: health.tools_loaded > 0 },
                  { key: '最後檢查', value: formatDate(health.timestamp), ok: true },
                ].map(({ key, value, ok }) => (
                  <div key={key} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <span className="text-sm text-slate-600">{key}</span>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span className="text-sm font-medium text-slate-800">{value}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />載入中...
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 使用者管理 ── */}
      {tab === 'users' && (
        <div className="space-y-4">
          <div className="card p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                className="input pl-9"
                placeholder="搜尋帳號或顯示名稱..."
                value={userSearch}
                onChange={e => { setUserSearch(e.target.value); setUserPage(1) }}
              />
            </div>
          </div>

          <div className="card overflow-hidden">
            {usersLoading ? (
              <div className="flex items-center justify-center h-40">
                <Loader2 className="w-7 h-7 animate-spin text-brand-500" />
              </div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>帳號</th>
                    <th>顯示名稱</th>
                    <th>認證網域</th>
                    <th>角色</th>
                    <th>狀態</th>
                    <th>最後登入</th>
                    <th className="text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {usersData?.users?.map((u: any) => (
                    <tr key={u.id}>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                            {u.username[0].toUpperCase()}
                          </div>
                          <span className="text-sm font-medium text-slate-800">{u.username}</span>
                          {u.is_superadmin && <span className="badge-purple text-[10px]">超管</span>}
                        </div>
                      </td>
                      <td><span className="text-sm text-slate-600">{u.display_name}</span></td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${REALM_TYPE_BADGE[u.realm_type] || 'badge-gray'}`}>
                            {REALM_TYPE_LABEL[u.realm_type] || u.realm_type}
                          </span>
                          <span className="text-xs font-mono text-slate-400">{u.realm}</span>
                        </div>
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {u.roles.map((r: string) => (
                            <span key={r} className="badge-blue text-[10px]">{ROLE_LABELS[r] || r}</span>
                          ))}
                          {u.roles.length === 0 && <span className="text-xs text-slate-400">—</span>}
                        </div>
                      </td>
                      <td>
                        <span className={u.enabled ? 'badge-green text-[11px]' : 'badge-red text-[11px]'}>
                          {u.enabled ? '啟用' : '停用'}
                        </span>
                      </td>
                      <td><span className="text-xs text-slate-500">{formatDate(u.last_login)}</span></td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => setEditUser(u)} className="btn-ghost btn-sm !px-2" title="編輯">
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => { if (confirm(`確定要刪除使用者 ${u.username}？`)) deleteUserMut.mutate(u.id) }}
                            className="btn-ghost btn-sm !px-2 text-red-400 hover:text-red-600 hover:bg-red-50"
                            title="刪除"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── 認證網域 ── */}
      {tab === 'realms' && (
        <div className="space-y-4">
          {realmsLoading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-7 h-7 animate-spin text-brand-500" />
            </div>
          ) : (
            (realms || []).map((realm: any) => (
              <div key={realm.id} className="card p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      realm.type === 'local' ? 'bg-slate-100 text-slate-600' :
                      realm.type === 'ad'    ? 'bg-purple-50 text-purple-600' :
                                               'bg-blue-50 text-blue-600'
                    }`}>
                      {realm.type === 'local' ? <Lock className="w-5 h-5" /> : <Server className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-slate-900">
                          {realm.display_name || realm.name}
                        </h3>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${REALM_TYPE_BADGE[realm.type] || 'badge-gray'}`}>
                          {REALM_TYPE_LABEL[realm.type] || realm.type}
                        </span>
                        <span className={realm.enabled ? 'badge-green text-[10px]' : 'badge-red text-[10px]'}>
                          {realm.enabled ? '已啟用' : '已停用'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {realm.name} · {realm.user_count} 個使用者
                        {realm.config?.url && <> · {realm.config.url}</>}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {realm.type !== 'local' && (
                      <>
                        <button
                          onClick={() => testRealmMut.mutate(realm.id)}
                          disabled={testRealmMut.isPending}
                          className="btn-secondary btn-sm"
                          title="測試連線"
                        >
                          {testRealmMut.isPending ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Wifi className="w-3.5 h-3.5" />
                          )}
                          測試連線
                        </button>
                        <button
                          onClick={() => setBrowseRealm(realm)}
                          className="btn-secondary btn-sm"
                          title="瀏覽目錄使用者"
                        >
                          <Download className="w-3.5 h-3.5" />
                          瀏覽目錄
                        </button>
                        <button onClick={() => setEditRealm(realm)} className="btn-ghost btn-sm !px-2" title="編輯">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`確定要刪除認證網域「${realm.name}」？`))
                              deleteRealmMut.mutate(realm.id)
                          }}
                          className="btn-ghost btn-sm !px-2 text-red-400 hover:text-red-600 hover:bg-red-50"
                          title="刪除"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* LDAP/AD 設定摘要 */}
                {realm.type !== 'local' && realm.config && Object.keys(realm.config).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-3">
                    {realm.config.url && (
                      <div>
                        <p className="text-[11px] text-slate-400 uppercase tracking-wide">伺服器</p>
                        <p className="text-xs font-mono text-slate-700 mt-0.5">{realm.config.url}</p>
                      </div>
                    )}
                    {realm.config.base_dn && (
                      <div>
                        <p className="text-[11px] text-slate-400 uppercase tracking-wide">Base DN</p>
                        <p className="text-xs font-mono text-slate-700 mt-0.5">{realm.config.base_dn}</p>
                      </div>
                    )}
                    {realm.config.bind_dn && (
                      <div>
                        <p className="text-[11px] text-slate-400 uppercase tracking-wide">服務帳號</p>
                        <p className="text-xs font-mono text-slate-700 mt-0.5">{realm.config.bind_dn}</p>
                      </div>
                    )}
                    {realm.config.user_filter && (
                      <div>
                        <p className="text-[11px] text-slate-400 uppercase tracking-wide">使用者篩選器</p>
                        <p className="text-xs font-mono text-slate-700 mt-0.5">{realm.config.user_filter}</p>
                      </div>
                    )}
                    {realm.config.default_roles && (
                      <div>
                        <p className="text-[11px] text-slate-400 uppercase tracking-wide">預設角色</p>
                        <div className="flex gap-1 mt-0.5 flex-wrap">
                          {(realm.config.default_roles as string[]).map((r: string) => (
                            <span key={r} className="badge-blue text-[10px]">{ROLE_LABELS[r] || r}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* ── 角色權限 ── */}
      {tab === 'roles' && (
        <div className="space-y-4">
          {(roles || []).map((role: any) => (
            <RoleCard key={role.id} role={role} />
          ))}
        </div>
      )}

      {/* Modals */}
      {showCreateUser && (
        <CreateUserModal
          onClose={() => setShowCreateUser(false)}
          onSuccess={() => { setShowCreateUser(false); qc.invalidateQueries({ queryKey: ['admin-users'] }) }}
        />
      )}
      {editUser && (
        <EditUserModal
          user={editUser}
          onClose={() => setEditUser(null)}
          onSuccess={() => { setEditUser(null); qc.invalidateQueries({ queryKey: ['admin-users'] }) }}
        />
      )}
      {showCreateRealm && (
        <RealmModal
          onClose={() => setShowCreateRealm(false)}
          onSuccess={() => { setShowCreateRealm(false); qc.invalidateQueries({ queryKey: ['admin-realms'] }) }}
        />
      )}
      {editRealm && (
        <RealmModal
          realm={editRealm}
          onClose={() => setEditRealm(null)}
          onSuccess={() => { setEditRealm(null); qc.invalidateQueries({ queryKey: ['admin-realms'] }) }}
        />
      )}
      {browseRealm && (
        <DirectoryUsersModal
          realm={browseRealm}
          onClose={() => setBrowseRealm(null)}
          onImported={() => qc.invalidateQueries({ queryKey: ['admin-users'] })}
        />
      )}
    </div>
  )
}

// ── 角色卡片（含權限展開） ─────────────────────────────────────────────────────

function RoleCard({ role }: { role: any }) {
  const [expanded, setExpanded] = useState(false)
  const LEVEL_COLOR = role.level >= 40 ? 'text-red-600 bg-red-50' :
                      role.level >= 30 ? 'text-orange-600 bg-orange-50' :
                      role.level >= 20 ? 'text-blue-600 bg-blue-50' :
                      role.level >= 10 ? 'text-slate-600 bg-slate-100' : 'text-slate-400 bg-slate-50'

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 flex-1">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${LEVEL_COLOR}`}>
            <Shield className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-900">{role.display_name}</h3>
              {role.builtin && <span className="badge-gray text-[10px]">內建</span>}
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${LEVEL_COLOR}`}>
                Level {role.level}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{role.name}</p>
          </div>
        </div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="btn-ghost btn-sm !px-2 text-slate-400"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* 權限摘要（永遠顯示） */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {(role.permissions || []).map((p: string) => (
          <span key={p} className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 text-slate-600 text-[11px] rounded-md font-mono">
            {PERM_LABEL[p] ? (
              <><span className="text-brand-600">{PERM_LABEL[p]}</span><span className="text-slate-400">·{p}</span></>
            ) : p}
          </span>
        ))}
        {(role.permissions || []).length === 0 && (
          <span className="text-xs text-slate-400">無特殊權限</span>
        )}
      </div>

      {/* 展開：詳細說明 */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <p className="text-xs font-medium text-slate-500 mb-2">此角色可執行的操作：</p>
          <div className="grid grid-cols-2 gap-2">
            {[
              { perm: 'tool:read',       label: '檢視工具列表' },
              { perm: 'tool:execute',    label: '執行工具' },
              { perm: 'document:read',   label: '檢視文件' },
              { perm: 'document:create', label: '上傳文件' },
              { perm: 'document:delete', label: '刪除文件' },
              { perm: 'job:read',        label: '檢視作業記錄' },
              { perm: 'job:*',           label: '管理作業（全部）' },
              { perm: 'user:*',          label: '使用者管理' },
              { perm: 'settings:*',      label: '系統設定' },
              { perm: 'audit:read',      label: '稽核日誌（檢視）' },
              { perm: 'audit:export',    label: '稽核日誌（匯出）' },
            ].map(({ perm, label }) => {
              const perms: string[] = role.permissions || []
              const ns = perm.split(':')[0]
              const has = perms.includes('*') || perms.includes(perm) || perms.includes(`${ns}:*`)
              return (
                <div key={perm} className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded ${has ? 'text-green-700 bg-green-50' : 'text-slate-300 bg-slate-50'}`}>
                  <CheckCircle className={`w-3.5 h-3.5 flex-shrink-0 ${has ? 'text-green-500' : 'text-slate-200'}`} />
                  {label}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── 使用者 Modals ──────────────────────────────────────────────────────────────

function CreateUserModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({ username: '', password: '', display_name: '', email: '', roles: ['operator'], realm: 'local' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await adminApi.createUser(form)
      toast.success(`使用者 ${form.username} 已建立`)
      onSuccess()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '建立失敗')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="新增使用者" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">帳號 <span className="text-red-500">*</span></label>
            <input className="input" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">密碼 <span className="text-red-500">*</span></label>
            <input type="password" className="input" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">顯示名稱</label>
            <input className="input" value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">Email</label>
            <input type="email" className="input" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">角色</label>
          <div className="flex flex-wrap gap-2">
            {ROLE_OPTS.map(r => (
              <button
                key={r} type="button"
                onClick={() => setForm(f => ({
                  ...f,
                  roles: f.roles.includes(r) ? f.roles.filter(x => x !== r) : [...f.roles, r]
                }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  form.roles.includes(r) ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {ROLE_LABELS[r] || r}
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">取消</button>
          <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            建立使用者
          </button>
        </div>
      </form>
    </Modal>
  )
}

function EditUserModal({ user, onClose, onSuccess }: { user: any; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({ display_name: user.display_name, email: user.email || '', enabled: user.enabled, roles: user.roles, password: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await adminApi.updateUser(user.id, { ...form, password: form.password || undefined })
      toast.success('使用者已更新')
      onSuccess()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '更新失敗')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title={`編輯：${user.username}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">顯示名稱</label>
            <input className="input" value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">Email</label>
            <input type="email" className="input" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">新密碼（留空不變）</label>
            <input type="password" className="input" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </div>
          <div className="flex items-end pb-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <button type="button" onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}
                className={`relative w-10 h-5 rounded-full transition-colors ${form.enabled ? 'bg-brand-600' : 'bg-slate-200'}`}>
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${form.enabled ? 'translate-x-5' : ''}`} />
              </button>
              <span className="text-sm text-slate-700">{form.enabled ? '帳號啟用' : '帳號停用'}</span>
            </label>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">角色</label>
          <div className="flex flex-wrap gap-2">
            {ROLE_OPTS.map(r => (
              <button key={r} type="button"
                onClick={() => setForm(f => ({ ...f, roles: f.roles.includes(r) ? f.roles.filter((x: string) => x !== r) : [...f.roles, r] }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${form.roles.includes(r) ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {ROLE_LABELS[r] || r}
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">取消</button>
          <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}儲存變更
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── 目錄使用者瀏覽與匯入 Modal ────────────────────────────────────────────────

function DirectoryUsersModal({ realm, onClose, onImported }: {
  realm: any; onClose: () => void; onImported: () => void
}) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [importing, setImporting] = useState(false)

  const { data: dirUsers, isLoading, error } = useQuery({
    queryKey: ['realm-dir-users', realm.id],
    queryFn: () => adminApi.listRealmDirectoryUsers(realm.id),
    staleTime: 30000,
  })

  const filtered = (dirUsers || []).filter(u =>
    u.username.toLowerCase().includes(search.toLowerCase()) ||
    u.display_name.toLowerCase().includes(search.toLowerCase()) ||
    (u.email || '').toLowerCase().includes(search.toLowerCase())
  )

  const notImported = filtered.filter(u => !u.imported)
  const allSelected = notImported.length > 0 && notImported.every(u => selected.has(u.username))

  const toggleAll = () => {
    if (allSelected) {
      setSelected(s => { const n = new Set(s); notImported.forEach(u => n.delete(u.username)); return n })
    } else {
      setSelected(s => { const n = new Set(s); notImported.forEach(u => n.add(u.username)); return n })
    }
  }

  const handleImport = async () => {
    if (selected.size === 0) return
    setImporting(true)
    try {
      const result = await adminApi.syncRealmUsers(realm.id, [...selected])
      toast.success(`已匯入 ${result.imported} 位使用者${result.skipped ? `，${result.skipped} 位已存在` : ''}`)
      setSelected(new Set())
      onImported()
      onClose()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || '匯入失敗')
    } finally {
      setImporting(false)
    }
  }

  return (
    <Modal title={`瀏覽目錄：${realm.display_name || realm.name}`} onClose={onClose} wide>
      <div className="space-y-4">
        {/* 搜尋列 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="搜尋帳號、姓名或 Email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* 使用者列表 */}
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-7 h-7 animate-spin text-brand-500" />
            <span className="ml-3 text-sm text-slate-500">正在從目錄伺服器撈取使用者...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-48 text-red-500 text-sm">
            目錄查詢失敗，請確認連線設定是否正確
          </div>
        ) : (
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            {/* 表頭 */}
            <div className="flex items-center gap-3 px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <button
                onClick={toggleAll}
                className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                  allSelected ? 'bg-brand-600 border-brand-600' : 'border-slate-300 hover:border-brand-400'
                }`}
              >
                {allSelected && <CheckCircle className="w-3 h-3 text-white" />}
              </button>
              <span className="w-36">帳號</span>
              <span className="flex-1">顯示名稱</span>
              <span className="w-48">Email</span>
              <span className="w-16 text-center">狀態</span>
            </div>

            {/* 使用者列表 */}
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <div className="flex items-center justify-center h-24 text-sm text-slate-400">
                  {search ? '無符合條件的使用者' : '目錄中沒有使用者'}
                </div>
              ) : filtered.map(u => (
                <div
                  key={u.username}
                  className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                    u.imported ? 'opacity-50' : 'hover:bg-slate-50 cursor-pointer'
                  } ${selected.has(u.username) ? 'bg-brand-50' : ''}`}
                  onClick={() => {
                    if (u.imported) return
                    setSelected(s => {
                      const n = new Set(s)
                      n.has(u.username) ? n.delete(u.username) : n.add(u.username)
                      return n
                    })
                  }}
                >
                  <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                    u.imported ? 'bg-slate-200 border-slate-200' :
                    selected.has(u.username) ? 'bg-brand-600 border-brand-600' : 'border-slate-300'
                  }`}>
                    {(u.imported || selected.has(u.username)) && (
                      <CheckCircle className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <span className="w-36 text-sm font-mono text-slate-700 truncate">{u.username}</span>
                  <span className="flex-1 text-sm text-slate-600 truncate">{u.display_name}</span>
                  <span className="w-48 text-xs text-slate-400 truncate">{u.email || '—'}</span>
                  <div className="w-16 flex justify-center">
                    {u.imported
                      ? <span className="badge-green text-[10px]">已匯入</span>
                      : <span className="badge-gray text-[10px]">未匯入</span>
                    }
                  </div>
                </div>
              ))}
            </div>

            {/* 底部統計 */}
            <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
              <span>
                共 {filtered.length} 位使用者，已匯入 {filtered.filter(u => u.imported).length} 位
              </span>
              {selected.size > 0 && (
                <span className="text-brand-600 font-medium">已選取 {selected.size} 位</span>
              )}
            </div>
          </div>
        )}

        {/* 操作列 */}
        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">關閉</button>
          <button
            onClick={handleImport}
            disabled={selected.size === 0 || importing}
            className="btn-primary flex-1 justify-center"
          >
            {importing
              ? <><Loader2 className="w-4 h-4 animate-spin" />匯入中...</>
              : <><Download className="w-4 h-4" />匯入選取（{selected.size}）</>
            }
          </button>
        </div>
      </div>
    </Modal>
  )
}


// ── Realm Modal ────────────────────────────────────────────────────────────────

const DEFAULT_LDAP_FILTER = '(uid={username})'
const DEFAULT_AD_FILTER   = '(sAMAccountName={username})'

function RealmModal({ realm, onClose, onSuccess }: { realm?: any; onClose: () => void; onSuccess: () => void }) {
  const isEdit = !!realm
  const [type, setType]  = useState<string>(realm?.type || 'ldap')
  const [form, setForm]  = useState({
    name:          realm?.name || '',
    display_name:  realm?.display_name || realm?.config?.display_name || '',
    enabled:       realm?.enabled ?? true,
    url:           realm?.config?.url || '',
    bind_dn:       realm?.config?.bind_dn || '',
    bind_password: '',
    base_dn:       realm?.config?.base_dn || '',
    user_filter:   realm?.config?.user_filter || (realm?.type === 'ad' ? DEFAULT_AD_FILTER : DEFAULT_LDAP_FILTER),
    display_name_attr: realm?.config?.display_name_attr || (realm?.type === 'ad' ? 'displayName' : 'cn'),
    email_attr:    realm?.config?.email_attr || 'mail',
    default_roles: (realm?.config?.default_roles as string[]) || ['viewer'],
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const config: Record<string, any> = {
        display_name:       form.display_name,
        url:                form.url,
        bind_dn:            form.bind_dn,
        base_dn:            form.base_dn,
        user_filter:        form.user_filter,
        display_name_attr:  form.display_name_attr,
        email_attr:         form.email_attr,
        default_roles:      form.default_roles,
      }
      if (form.bind_password) config.bind_password = form.bind_password

      if (isEdit) {
        await adminApi.updateRealm(realm.id, { display_name: form.display_name, config, enabled: form.enabled })
        toast.success('認證網域已更新')
      } else {
        await adminApi.createRealm({ name: form.name, type, display_name: form.display_name, config, enabled: form.enabled })
        toast.success('認證網域已建立')
      }
      onSuccess()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '操作失敗')
    } finally {
      setLoading(false)
    }
  }

  const F = ({ label, field, type: t = 'text', placeholder = '', required = false }: {
    label: string; field: keyof typeof form; type?: string; placeholder?: string; required?: boolean
  }) => (
    <div>
      <label className="block text-xs font-medium text-slate-700 mb-1.5">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={t}
        className="input"
        value={form[field] as string}
        onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
        placeholder={placeholder}
        required={required}
        autoComplete={t === 'password' ? 'new-password' : undefined}
      />
    </div>
  )

  return (
    <Modal title={isEdit ? `編輯網域：${realm.name}` : '新增認證網域'} onClose={onClose} wide>
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* 基本資訊 */}
        <div className="grid grid-cols-2 gap-4">
          {!isEdit && (
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">網域識別碼 <span className="text-red-500">*</span></label>
              <input className="input font-mono" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') }))}
                placeholder="my-domain" required />
              <p className="text-[11px] text-slate-400 mt-1">僅允許小寫英數字與連字號</p>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">顯示名稱</label>
            <input className="input" value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} placeholder="公司 Active Directory" />
          </div>
          {!isEdit && (
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">網域類型</label>
              <div className="flex gap-2">
                {(['ldap', 'ad'] as const).map(t => (
                  <button key={t} type="button"
                    onClick={() => {
                      setType(t)
                      setForm(f => ({
                        ...f,
                        user_filter: t === 'ad' ? DEFAULT_AD_FILTER : DEFAULT_LDAP_FILTER,
                        display_name_attr: t === 'ad' ? 'displayName' : 'cn',
                      }))
                    }}
                    className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-all ${
                      type === t ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {t === 'ad' ? 'Active Directory' : 'LDAP 目錄'}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <button type="button" onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}
                className={`relative w-10 h-5 rounded-full transition-colors ${form.enabled ? 'bg-brand-600' : 'bg-slate-200'}`}>
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${form.enabled ? 'translate-x-5' : ''}`} />
              </button>
              <span className="text-sm text-slate-700">啟用此網域</span>
            </label>
          </div>
        </div>

        {/* 伺服器連線 */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">伺服器連線</p>
          <div className="grid grid-cols-1 gap-3">
            <F label="LDAP 伺服器 URL" field="url" placeholder="ldap://dc.example.com:389" required />
            <div className="grid grid-cols-2 gap-3">
              <F label="服務帳號 DN (Bind DN)" field="bind_dn" placeholder="cn=svc,dc=example,dc=com" />
              <F label="服務帳號密碼" field="bind_password" type="password" placeholder={isEdit ? '留空保留舊密碼' : ''} />
            </div>
            <F label="搜尋根節點 (Base DN)" field="base_dn" placeholder="dc=example,dc=com" required />
          </div>
        </div>

        {/* 使用者映射 */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">使用者映射</p>
          <div className="grid grid-cols-2 gap-3">
            <F label="使用者篩選器" field="user_filter" placeholder={type === 'ad' ? DEFAULT_AD_FILTER : DEFAULT_LDAP_FILTER} />
            <F label="顯示名稱屬性" field="display_name_attr" placeholder={type === 'ad' ? 'displayName' : 'cn'} />
            <F label="Email 屬性" field="email_attr" placeholder="mail" />
          </div>
        </div>

        {/* 預設角色 */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">首次登入預設角色</p>
          <div className="flex flex-wrap gap-2">
            {ROLE_OPTS.map(r => (
              <button key={r} type="button"
                onClick={() => setForm(f => ({ ...f, default_roles: f.default_roles.includes(r) ? f.default_roles.filter(x => x !== r) : [...f.default_roles, r] }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${form.default_roles.includes(r) ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {ROLE_LABELS[r] || r}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">LDAP/AD 使用者首次登入時自動套用的角色</p>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">取消</button>
          <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {isEdit ? '儲存變更' : '建立網域'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Modal 容器 ────────────────────────────────────────────────────────────────

function Modal({ title, onClose, children, wide }: {
  title: string; onClose: () => void; children: React.ReactNode; wide?: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative card shadow-2xl animate-slide-up w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between p-5 border-b border-slate-200 flex-shrink-0">
          <h3 className="text-base font-semibold text-slate-900">{title}</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}
