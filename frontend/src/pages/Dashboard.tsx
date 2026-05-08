import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Users, Wrench, CheckCircle, XCircle, Clock, TrendingUp,
  ArrowRight, FileText, Zap, Shield
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { adminApi, jobsApi, toolsApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { formatDate, STATUS_BADGE, STATUS_LABEL } from '../lib/utils'

export function Dashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()

  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.stats,
    enabled: !!user?.is_superadmin,
    refetchInterval: 30000,
  })

  const { data: recentJobs } = useQuery({
    queryKey: ['recent-jobs'],
    queryFn: () => jobsApi.list({ page: 1, page_size: 8 }),
    refetchInterval: 10000,
  })

  const { data: toolsData } = useQuery({
    queryKey: ['tools-list'],
    queryFn: toolsApi.list,
  })

  const quickTools = toolsData?.tools?.slice(0, 6) || []
  const TOOL_COLOR: Record<string, string> = {
    blue: 'tool-blue', green: 'tool-green', red: 'tool-red', purple: 'tool-purple',
    orange: 'tool-orange', cyan: 'tool-cyan', yellow: 'tool-yellow', pink: 'tool-pink',
    indigo: 'tool-indigo', teal: 'tool-teal', rose: 'tool-rose', violet: 'tool-violet',
    amber: 'tool-amber', sky: 'tool-sky', lime: 'tool-lime', slate: 'tool-slate',
  }

  return (
    <div className="space-y-6 animate-in">
      {/* 頁首 */}
      <div>
        <h1 className="page-title">
          歡迎回來，{user?.display_name || user?.username} 👋
        </h1>
        <p className="page-subtitle">
          {new Intl.DateTimeFormat('zh-TW', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(new Date())}
        </p>
      </div>

      {/* 統計卡片（管理員才顯示） */}
      {user?.is_superadmin && stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { icon: Users,       label: '使用者',  value: stats.users,           color: 'bg-blue-50 text-blue-600' },
            { icon: Wrench,      label: '工具數',  value: stats.tools,           color: 'bg-purple-50 text-purple-600' },
            { icon: CheckCircle, label: '完成作業', value: stats.jobs.done,       color: 'bg-green-50 text-green-600' },
            { icon: XCircle,     label: '失敗作業', value: stats.jobs.failed,     color: 'bg-red-50 text-red-600' },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="stat-card">
              <div className={`stat-icon ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{value}</p>
                <p className="text-sm text-slate-500 mt-0.5">{label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* 作業趨勢圖 */}
        {user?.is_superadmin && stats?.job_trend?.length ? (
          <div className="card p-5 xl:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-brand-600" />
                <h2 className="text-sm font-semibold text-slate-900">近期作業趨勢</h2>
              </div>
              <span className="text-xs text-slate-400">最近 7 天</span>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={stats.job_trend} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{ border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
                  labelFormatter={v => `日期：${v}`}
                  formatter={(v) => [`${v} 件`, '作業數']}
                />
                <Area type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} fill="url(#grad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          /* 非管理員：顯示快速工具 */
          <div className="card p-5 xl:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-brand-600" />
                <h2 className="text-sm font-semibold text-slate-900">快速開始</h2>
              </div>
              <button onClick={() => navigate('/tools')} className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
                全部工具 <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {quickTools.map(tool => (
                <button
                  key={tool.tool_id}
                  onClick={() => navigate(`/tools/${tool.tool_id}`)}
                  className="flex items-center gap-2.5 p-3 rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 transition-all text-left group"
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${TOOL_COLOR[tool.color] || 'tool-blue'}`}>
                    <FileText className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-medium text-slate-700 group-hover:text-brand-700 leading-tight">{tool.name_zh}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 最近作業 */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-600" />
              <h2 className="text-sm font-semibold text-slate-900">最近作業</h2>
            </div>
            <button onClick={() => navigate('/jobs')} className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
              全部 <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            {recentJobs?.jobs?.length === 0 && (
              <div className="text-center py-6">
                <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-400">尚無作業記錄</p>
                <button onClick={() => navigate('/tools')} className="text-xs text-brand-600 mt-1 hover:underline">
                  開始使用工具 →
                </button>
              </div>
            )}
            {recentJobs?.jobs?.map(job => (
              <button
                key={job.id}
                onClick={() => navigate('/jobs')}
                className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors text-left"
              >
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  job.status === 'done' ? 'bg-green-500' :
                  job.status === 'failed' ? 'bg-red-500' :
                  job.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-yellow-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-700 truncate">{job.input_filename}</p>
                  <p className="text-[11px] text-slate-400 truncate">{job.tool_id} · {formatDate(job.queued_at)}</p>
                </div>
                <span className={`text-[10px] font-medium flex-shrink-0 ${
                  job.status === 'done' ? 'text-green-600' :
                  job.status === 'failed' ? 'text-red-600' :
                  job.status === 'running' ? 'text-blue-600' : 'text-yellow-600'
                }`}>
                  {STATUS_LABEL[job.status]}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 快速工具（管理員版） */}
      {user?.is_superadmin && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-brand-600" />
              <h2 className="text-sm font-semibold text-slate-900">常用工具</h2>
            </div>
            <button onClick={() => navigate('/tools')} className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
              全部工具 <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {quickTools.map(tool => (
              <button
                key={tool.tool_id}
                onClick={() => navigate(`/tools/${tool.tool_id}`)}
                className="flex flex-col items-center gap-2 p-4 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 transition-all group"
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${TOOL_COLOR[tool.color] || 'tool-blue'}`}>
                  <FileText className="w-5 h-5" />
                </div>
                <span className="text-xs font-medium text-slate-600 group-hover:text-brand-700 text-center leading-tight">
                  {tool.name_zh}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
