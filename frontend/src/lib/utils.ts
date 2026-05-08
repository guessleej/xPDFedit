import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}m ${s}s`
}

export const STATUS_LABEL: Record<string, string> = {
  queued: '排隊中',
  running: '執行中',
  done: '完成',
  failed: '失敗',
  cancelled: '已取消',
}

export const STATUS_BADGE: Record<string, string> = {
  queued: 'badge-yellow',
  running: 'badge-blue',
  done: 'badge-green',
  failed: 'badge-red',
  cancelled: 'badge-gray',
}

export const CATEGORY_LABEL: Record<string, string> = {
  pdf: 'PDF 工具',
  convert: '格式轉換',
  security: '資安防護',
  ai: 'AI 智能',
  general: '其他',
}

export const CATEGORY_COLOR: Record<string, string> = {
  pdf: 'bg-blue-600',
  convert: 'bg-purple-600',
  security: 'bg-red-600',
  ai: 'bg-violet-600',
  general: 'bg-slate-500',
}
