import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  ClipboardList, Download, Trash2, RefreshCw, Search,
  Filter, CheckCircle, XCircle, Clock, Loader2, FileText, AlertCircle, Ban,
} from 'lucide-react'
import { jobsApi } from '../lib/api'
import { formatDate, formatDuration, STATUS_BADGE, STATUS_LABEL } from '../lib/utils'
import toast from 'react-hot-toast'

const STATUS_OPTS = ['', 'queued', 'running', 'done', 'failed', 'cancelled'] as const

export function Jobs() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [cancellingIds, setCancellingIds] = useState<Set<string>>(new Set())

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['jobs', page, status],
    queryFn: () => jobsApi.list({ page, page_size: 15, status: status || undefined }),
    refetchInterval: 5000,
  })

  const handleDownload = async (jobId: string, filename: string) => {
    const token = localStorage.getItem('access_token')
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) { toast.error('下載失敗'); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error('下載失敗，請重試')
    }
  }

  const handleForceCancel = async (id: string, status: string) => {
    const isRunning = status === 'running'
    const confirmed = isRunning
      ? confirm('確定要強制終止此執行中的作業？\n\n此操作會立即中斷程序，無法復原。')
      : true

    if (!confirmed) return

    setCancellingIds(prev => new Set(prev).add(id))
    try {
      await jobsApi.cancel(id)
      toast.success(isRunning ? '作業已強制終止' : '作業已取消')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '操作失敗')
    } finally {
      setCancellingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await jobsApi.cancel(id)
      toast.success('作業已刪除')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '刪除失敗')
    }
  }

  const jobs = data?.jobs?.filter(j =>
    !search || j.input_filename.toLowerCase().includes(search.toLowerCase()) ||
    j.tool_id.includes(search)
  ) || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / 15)

  const StatusIcon = ({ status }: { status: string }) => {
    if (status === 'done') return <CheckCircle className="w-4 h-4 text-green-500" />
    if (status === 'failed') return <XCircle className="w-4 h-4 text-red-500" />
    if (status === 'running') return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
    if (status === 'queued') return <Clock className="w-4 h-4 text-yellow-500" />
    if (status === 'cancelled') return <Ban className="w-4 h-4 text-slate-400" />
    return <AlertCircle className="w-4 h-4 text-slate-400" />
  }

  return (
    <div className="space-y-6 animate-in">
      {/* 頁首 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-brand-600" />我的作業
          </h1>
          <p className="page-subtitle">共 {total} 筆記錄</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => refetch()} className="btn-secondary btn-sm">
            <RefreshCw className="w-3.5 h-3.5" />重新整理
          </button>
          <button onClick={() => navigate('/tools')} className="btn-primary btn-sm">
            <FileText className="w-3.5 h-3.5" />新增作業
          </button>
        </div>
      </div>

      {/* 篩選列 */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="搜尋檔名或工具..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
          {STATUS_OPTS.map(s => (
            <button
              key={s}
              onClick={() => { setStatus(s); setPage(1) }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                status === s ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s === '' ? '全部' : STATUS_LABEL[s] || s}
            </button>
          ))}
        </div>
      </div>

      {/* 作業表格 */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16">
            <ClipboardList className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">沒有符合的作業記錄</p>
            <button onClick={() => navigate('/tools')} className="btn-primary mt-4">
              前往工具箱
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>狀態</th>
                  <th>工具</th>
                  <th>檔案名稱</th>
                  <th>提交時間</th>
                  <th>耗時</th>
                  <th className="text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => {
                  const isCancelling = cancellingIds.has(job.id)
                  return (
                    <tr key={job.id} className={job.status === 'running' ? 'bg-blue-50/30' : ''}>
                      {/* 狀態 */}
                      <td>
                        <div className="flex items-center gap-2">
                          <StatusIcon status={job.status} />
                          <span className={`badge ${STATUS_BADGE[job.status] || 'badge-gray'}`}>
                            {STATUS_LABEL[job.status] || job.status}
                          </span>
                        </div>
                      </td>

                      {/* 工具 */}
                      <td>
                        <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                          {job.tool_id}
                        </span>
                      </td>

                      {/* 檔名 */}
                      <td>
                        <div className="flex items-center gap-2 max-w-xs">
                          <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          <span className="truncate text-sm text-slate-700" title={job.input_filename}>
                            {job.input_filename}
                          </span>
                        </div>
                        {job.error_message && (
                          <p className="text-xs text-red-500 mt-0.5 truncate max-w-xs" title={job.error_message}>
                            {job.error_message}
                          </p>
                        )}
                      </td>

                      {/* 時間 */}
                      <td>
                        <span className="text-xs text-slate-500">{formatDate(job.queued_at)}</span>
                      </td>

                      {/* 進度 / 耗時 */}
                      <td>
                        {job.status === 'running' ? (
                          <div className="space-y-1 w-28">
                            <div className="progress-bar">
                              <div className="progress-fill" style={{ width: `${job.progress}%` }} />
                            </div>
                            <span className="text-[11px] text-slate-400">{job.progress}%</span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500">{formatDuration(job.duration_seconds)}</span>
                        )}
                      </td>

                      {/* 操作 */}
                      <td>
                        <div className="flex items-center justify-end gap-1.5">
                          {/* 下載（完成） */}
                          {job.status === 'done' && (
                            <button
                              onClick={() => handleDownload(job.id, job.output_filename || 'output.pdf')}
                              className="btn-sm btn-secondary !px-2.5"
                              title="下載結果"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* 強制終止（執行中） */}
                          {job.status === 'running' && (
                            <button
                              onClick={() => handleForceCancel(job.id, job.status)}
                              disabled={isCancelling}
                              className="btn-sm flex items-center gap-1.5 px-2.5 py-1
                                         bg-red-500 hover:bg-red-600 active:bg-red-700
                                         text-white rounded-lg text-xs font-medium
                                         transition-all disabled:opacity-60 disabled:cursor-not-allowed
                                         shadow-sm"
                              title="強制終止"
                            >
                              {isCancelling
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Ban className="w-3.5 h-3.5" />
                              }
                              強制終止
                            </button>
                          )}

                          {/* 取消（排隊中） */}
                          {job.status === 'queued' && (
                            <button
                              onClick={() => handleForceCancel(job.id, job.status)}
                              disabled={isCancelling}
                              className="btn-sm btn-ghost !px-2.5 text-orange-500 hover:text-orange-700 hover:bg-orange-50"
                              title="取消排隊"
                            >
                              {isCancelling
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <XCircle className="w-3.5 h-3.5" />
                              }
                            </button>
                          )}

                          {/* 刪除（完成 / 失敗 / 已取消） */}
                          {(job.status === 'done' || job.status === 'failed' || job.status === 'cancelled') && (
                            <button
                              onClick={() => handleDelete(job.id)}
                              className="btn-sm btn-ghost !px-2.5 text-slate-400 hover:text-red-500 hover:bg-red-50"
                              title="刪除記錄"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* 分頁 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
            <p className="text-xs text-slate-500">第 {page} / {totalPages} 頁，共 {total} 筆</p>
            <div className="flex gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary btn-sm !px-2.5">‹</button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
                <button key={p} onClick={() => setPage(p)} className={`btn-sm !px-3 ${page === p ? 'btn-primary' : 'btn-secondary'}`}>{p}</button>
              ))}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary btn-sm !px-2.5">›</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
