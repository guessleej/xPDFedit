import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, X, ChevronLeft, Loader2, CheckCircle,
  ArrowRight, AlertCircle, Info, ChevronUp, ChevronDown, PlusCircle,
} from 'lucide-react'
import { toolsApi, jobsApi, type ToolParam } from '../lib/api'
import { formatFileSize } from '../lib/utils'
import toast from 'react-hot-toast'

export function ToolExecute() {
  const { toolId } = useParams<{ toolId: string }>()
  const navigate = useNavigate()
  // 單檔模式
  const [file, setFile] = useState<File | null>(null)
  // 多檔模式
  const [multiFiles, setMultiFiles] = useState<File[]>([])
  const [params, setParams] = useState<Record<string, unknown>>({})

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
      a.download = filename || 'output.pdf'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      toast.error('下載失敗，請重試')
    }
  }
  const [submitting, setSubmitting] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)

  const { data: tool, isLoading } = useQuery({
    queryKey: ['tool', toolId],
    queryFn: () => toolsApi.get(toolId!),
    enabled: !!toolId,
  })

  const initParams = useCallback((toolParams: ToolParam[]) => {
    const defaults: Record<string, unknown> = {}
    toolParams.forEach(p => { if (p.default !== undefined) defaults[p.name] = p.default })
    setParams(defaults)
  }, [])
  void initParams // suppress unused warning

  // ── 單檔 dropzone ─────────────────────────────────────────────────────────
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => { if (accepted[0]) setFile(accepted[0]) },
    multiple: false,
    maxSize: 500 * 1024 * 1024,
  })

  // ── 多檔 dropzone ─────────────────────────────────────────────────────────
  const { getRootProps: getMultiRootProps, getInputProps: getMultiInputProps, isDragActive: isMultiDragActive } = useDropzone({
    onDrop: (accepted) => {
      setMultiFiles(prev => {
        const existing = new Set(prev.map(f => f.name + f.size))
        const newFiles = accepted.filter(f => !existing.has(f.name + f.size))
        return [...prev, ...newFiles]
      })
    },
    multiple: true,
    maxSize: 500 * 1024 * 1024,
    accept: { 'application/pdf': ['.pdf'] },
  })

  const moveFile = (idx: number, dir: -1 | 1) => {
    setMultiFiles(prev => {
      const next = [...prev]
      const target = idx + dir
      if (target < 0 || target >= next.length) return prev
      ;[next[idx], next[target]] = [next[target], next[idx]]
      return next
    })
  }

  const removeFile = (idx: number) => setMultiFiles(prev => prev.filter((_, i) => i !== idx))

  const handleSubmit = async () => {
    if (!toolId) return
    const isMulti = tool?.multi_file

    if (isMulti) {
      if (multiFiles.length < 2) { toast.error('PDF 合併至少需要 2 個檔案'); return }
    } else {
      if (!file) { toast.error('請先選擇檔案'); return }
    }

    setSubmitting(true)
    try {
      const result = await toolsApi.submit(toolId, isMulti ? multiFiles : file!, params)
      setJobId(result.job_id)
      toast.success('作業已提交，正在處理中...')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '提交失敗，請稍後重試')
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    )
  }

  if (!tool) {
    return (
      <div className="card p-12 text-center">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-slate-500">找不到工具 {toolId}</p>
        <button onClick={() => navigate('/tools')} className="btn-primary mt-4">返回工具箱</button>
      </div>
    )
  }

  if (jobId) {
    return <JobResult jobId={jobId} toolName={tool.name_zh} onNew={() => { setJobId(null); setFile(null); setMultiFiles([]) }} />
  }

  const canSubmit = tool.multi_file ? multiFiles.length >= 2 : !!file

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in">
      {/* 麵包屑 */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <button onClick={() => navigate('/tools')} className="hover:text-brand-600 flex items-center gap-1">
          <ChevronLeft className="w-4 h-4" />工具箱
        </button>
        <span>/</span>
        <span className="text-slate-900 font-medium">{tool.name_zh}</span>
      </div>

      {/* 工具標題 */}
      <div className="card p-5 flex items-start gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 tool-${tool.color}`}>
          <FileText className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-slate-900">{tool.name_zh}</h1>
          <p className="text-sm text-slate-400">{tool.name_en}</p>
          <p className="text-sm text-slate-600 mt-1.5">{tool.description_zh}</p>
        </div>
        {tool.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 flex-shrink-0">
            {tool.tags.slice(0, 3).map(tag => (
              <span key={tag} className="badge-gray text-[11px]">{tag}</span>
            ))}
          </div>
        )}
      </div>

      {/* 上傳區域 */}
      {tool.multi_file ? (
        <MultiFileUpload
          files={multiFiles}
          isDragActive={isMultiDragActive}
          getRootProps={getMultiRootProps}
          getInputProps={getMultiInputProps}
          onMove={moveFile}
          onRemove={removeFile}
        />
      ) : (
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Upload className="w-4 h-4 text-brand-600" />上傳檔案
          </h2>
          {!file ? (
            <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
              <input {...getInputProps()} />
              <Upload className="w-8 h-8 text-slate-400 mx-auto mb-3" />
              <p className="text-sm text-slate-600 font-medium">
                {isDragActive ? '放開以上傳' : '拖曳檔案到此，或點擊選擇'}
              </p>
              <p className="text-xs text-slate-400 mt-1">支援所有檔案格式，最大 500MB</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-brand-50 border border-brand-200">
              <div className="w-10 h-10 rounded-lg bg-brand-100 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-brand-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{file.name}</p>
                <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
              </div>
              <button onClick={() => setFile(null)} className="p-1.5 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-500 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* 參數設定 */}
      {tool.params?.length > 0 && (
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Info className="w-4 h-4 text-brand-600" />參數設定
          </h2>
          <div className="space-y-4">
            {tool.params.map(param => (
              <ParamField
                key={param.name}
                param={param}
                value={params[param.name]}
                onChange={v => setParams(prev => ({ ...prev, [param.name]: v }))}
              />
            ))}
          </div>
        </div>
      )}

      {/* 提交按鈕 */}
      <div className="flex items-center justify-end gap-3">
        <button onClick={() => navigate('/tools')} className="btn-secondary">取消</button>
        <button onClick={handleSubmit} disabled={!canSubmit || submitting} className="btn-primary">
          {submitting ? (
            <><Loader2 className="w-4 h-4 animate-spin" />提交中...</>
          ) : (
            <>開始處理<ArrowRight className="w-4 h-4" /></>
          )}
        </button>
      </div>
    </div>
  )
}

// ── 多檔案上傳元件 ──────────────────────────────────────────────────────────
function MultiFileUpload({
  files, isDragActive, getRootProps, getInputProps, onMove, onRemove,
}: {
  files: File[]
  isDragActive: boolean
  getRootProps: () => any
  getInputProps: () => any
  onMove: (idx: number, dir: -1 | 1) => void
  onRemove: (idx: number) => void
}) {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <Upload className="w-4 h-4 text-brand-600" />選擇 PDF 檔案
          {files.length > 0 && (
            <span className="text-xs font-normal text-slate-500 ml-1">（{files.length} 個，依序合併）</span>
          )}
        </h2>
        {files.length < 2 && (
          <p className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-lg">至少需要 2 個檔案</p>
        )}
      </div>

      {/* 已選檔案清單 */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, idx) => (
            <div key={`${f.name}-${f.size}-${idx}`}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-200 group">
              {/* 順序標籤 */}
              <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center flex-shrink-0">
                {idx + 1}
              </span>
              {/* 檔案資訊 */}
              <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-100 flex items-center justify-center flex-shrink-0">
                <FileText className="w-4 h-4 text-red-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{f.name}</p>
                <p className="text-xs text-slate-400">{formatFileSize(f.size)}</p>
              </div>
              {/* 上移 / 下移 */}
              <div className="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => onMove(idx, -1)} disabled={idx === 0}
                  className="p-0.5 rounded hover:bg-slate-200 disabled:opacity-30 text-slate-500">
                  <ChevronUp className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => onMove(idx, 1)} disabled={idx === files.length - 1}
                  className="p-0.5 rounded hover:bg-slate-200 disabled:opacity-30 text-slate-500">
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
              </div>
              {/* 移除 */}
              <button onClick={() => onRemove(idx)}
                className="p-1.5 rounded-lg hover:bg-red-100 text-slate-300 hover:text-red-500 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 拖放區 */}
      <div {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${files.length > 0 ? 'py-4' : ''}`}>
        <input {...getInputProps()} />
        <PlusCircle className={`mx-auto mb-2 text-slate-400 ${files.length > 0 ? 'w-6 h-6' : 'w-8 h-8 mb-3'}`} />
        <p className={`text-slate-600 font-medium ${files.length > 0 ? 'text-xs' : 'text-sm'}`}>
          {isDragActive ? '放開以加入' : files.length > 0 ? '拖曳或點擊繼續新增 PDF' : '拖曳 PDF 到此，或點擊選擇（可多選）'}
        </p>
        {files.length === 0 && <p className="text-xs text-slate-400 mt-1">支援多選，最大 500MB / 每檔</p>}
      </div>
    </div>
  )
}

// ── 參數欄位 ────────────────────────────────────────────────────────────────
function ParamField({ param, value, onChange }: { param: ToolParam; value: unknown; onChange: (v: unknown) => void }) {
  const baseClass = "input"
  const label = (
    <label className="block text-xs font-medium text-slate-700 mb-1.5">
      {param.label_zh}
      {param.required && <span className="text-red-500 ml-1">*</span>}
      {param.description && <span className="text-slate-400 font-normal ml-1">— {param.description}</span>}
    </label>
  )

  if (param.type === 'select') return (
    <div>{label}
      <select className={baseClass} value={String(value ?? param.default ?? '')} onChange={e => onChange(e.target.value)}>
        {param.options?.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
    </div>
  )

  if (param.type === 'boolean') return (
    <div className="flex items-center gap-3">
      <button type="button" role="switch" aria-checked={Boolean(value ?? param.default)}
        onClick={() => onChange(!Boolean(value ?? param.default))}
        className={`relative w-10 h-5 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30 ${Boolean(value ?? param.default) ? 'bg-brand-600' : 'bg-slate-200'}`}>
        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${Boolean(value ?? param.default) ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
      <span className="text-sm text-slate-700">{param.label_zh}</span>
    </div>
  )

  if (param.type === 'password') return (
    <div>{label}
      <input type="password" className={baseClass} placeholder={param.placeholder || ''}
        value={String(value ?? '')} onChange={e => onChange(e.target.value)} autoComplete="new-password" />
    </div>
  )

  if (param.type === 'integer' || param.type === 'number') return (
    <div>{label}
      <input type="number" className={baseClass} placeholder={param.placeholder || ''}
        min={param.min_val} max={param.max_val} value={String(value ?? param.default ?? '')}
        onChange={e => onChange(param.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value))} />
    </div>
  )

  return (
    <div>{label}
      <input type="text" className={baseClass} placeholder={param.placeholder || ''}
        value={String(value ?? param.default ?? '')} onChange={e => onChange(e.target.value)} />
    </div>
  )
}

// ── 作業結果 ────────────────────────────────────────────────────────────────
function JobResult({ jobId, toolName, onNew }: { jobId: string; toolName: string; onNew: () => void }) {
  const navigate = useNavigate()
  const { data: job, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId),
    refetchInterval: (query) => {
      const d = query.state.data
      if (!d || d.status === 'running' || d.status === 'queued') return 1500
      return false
    },
  })

  if (isLoading || !job) {
    return (
      <div className="max-w-lg mx-auto card p-10 text-center space-y-4">
        <Loader2 className="w-10 h-10 animate-spin text-brand-500 mx-auto" />
        <p className="text-slate-600 font-medium">取得作業狀態...</p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto space-y-5 animate-in">
      <div className="card p-8 text-center space-y-5">
        {(job.status === 'queued' || job.status === 'running') && (
          <>
            <div className="w-16 h-16 mx-auto rounded-full bg-brand-50 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">{job.status === 'queued' ? '排隊等待中' : '處理中...'}</p>
              <p className="text-sm text-slate-500 mt-1">{toolName}</p>
            </div>
            <div className="space-y-1">
              <div className="progress-bar"><div className="progress-fill" style={{ width: `${job.progress || 10}%` }} /></div>
              <p className="text-xs text-slate-400">{job.progress || 0}%</p>
            </div>
          </>
        )}

        {job.status === 'done' && (
          <>
            <div className="w-16 h-16 mx-auto rounded-full bg-green-50 flex items-center justify-center">
              <CheckCircle className="w-9 h-9 text-green-500" />
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">處理完成！</p>
              <p className="text-sm text-slate-500 mt-1">{job.output_filename}</p>
            </div>
            {job.metadata && Object.keys(job.metadata).length > 0 && (
              <div className="bg-slate-50 rounded-xl p-4 text-left space-y-1">
                {Object.entries(job.metadata).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-slate-500">{k}</span>
                    <span className="text-slate-700 font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
            <DownloadButton jobId={jobId} filename={job.output_filename || 'output.pdf'} />
          </>
        )}

        {job.status === 'failed' && (
          <>
            <div className="w-16 h-16 mx-auto rounded-full bg-red-50 flex items-center justify-center">
              <AlertCircle className="w-9 h-9 text-red-400" />
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">處理失敗</p>
              {job.error_message && (
                <p className="text-sm text-red-500 mt-2 bg-red-50 rounded-lg p-3 text-left">{job.error_message}</p>
              )}
            </div>
          </>
        )}

        <div className="flex gap-3 pt-2">
          <button onClick={onNew} className="btn-secondary flex-1 justify-center">再處理一個</button>
          <button onClick={() => navigate('/jobs')} className="btn-ghost flex-1 justify-center">查看所有作業</button>
        </div>
      </div>
    </div>
  )
}

// ── 下載按鈕（帶 JWT）───────────────────────────────────────────────────────
function DownloadButton({ jobId, filename }: { jobId: string; filename: string }) {
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    setLoading(true)
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
    } finally {
      setLoading(false)
    }
  }

  return (
    <button onClick={handleClick} disabled={loading} className="btn-primary w-full justify-center">
      {loading ? <><Loader2 className="w-4 h-4 animate-spin" />下載中...</> : '下載結果'}
    </button>
  )
}
