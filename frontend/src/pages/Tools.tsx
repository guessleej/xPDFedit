import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, FileText, ChevronRight, SlidersHorizontal } from 'lucide-react'
import { toolsApi, type Tool } from '../lib/api'
import { CATEGORY_LABEL } from '../lib/utils'

const TOOL_COLOR_MAP: Record<string, string> = {
  blue: 'tool-blue', green: 'tool-green', red: 'tool-red', purple: 'tool-purple',
  orange: 'tool-orange', cyan: 'tool-cyan', yellow: 'tool-yellow', pink: 'tool-pink',
  indigo: 'tool-indigo', teal: 'tool-teal', rose: 'tool-rose', violet: 'tool-violet',
  amber: 'tool-amber', sky: 'tool-sky', lime: 'tool-lime', slate: 'tool-slate',
}

const CATEGORIES = ['all', 'pdf', 'convert', 'security', 'ai']

export function Tools() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const { data, isLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: toolsApi.list,
    staleTime: 60000,
  })

  const filtered = useMemo(() => {
    let tools = data?.tools || []
    if (category !== 'all') tools = tools.filter(t => t.category === category)
    if (search) {
      const q = search.toLowerCase()
      tools = tools.filter(t =>
        t.name_zh.includes(q) || t.name_en.toLowerCase().includes(q) ||
        t.description_zh.includes(q) || t.tags?.some(tag => tag.toLowerCase().includes(q))
      )
    }
    return tools
  }, [data, search, category])

  const grouped = useMemo(() => {
    const g: Record<string, Tool[]> = {}
    filtered.forEach(t => {
      if (!g[t.category]) g[t.category] = []
      g[t.category].push(t)
    })
    return g
  }, [filtered])

  return (
    <div className="space-y-6 animate-in">
      {/* 頁首 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">工具箱</h1>
          <p className="page-subtitle">共 {data?.total ?? 0} 個文件處理工具</p>
        </div>
      </div>

      {/* 搜尋 + 篩選 */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="搜尋工具名稱、功能..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input pl-9"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <SlidersHorizontal className="w-4 h-4 text-slate-400 flex-shrink-0" />
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                category === cat
                  ? 'bg-brand-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat === 'all' ? '全部' : CATEGORY_LABEL[cat] || cat}
            </button>
          ))}
        </div>
      </div>

      {/* 工具列表 */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card p-5 space-y-3">
              <div className="skeleton w-11 h-11 rounded-xl" />
              <div className="skeleton h-4 w-3/4 rounded" />
              <div className="skeleton h-3 w-full rounded" />
              <div className="skeleton h-3 w-2/3 rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Search className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 font-medium">找不到符合的工具</p>
          <p className="text-sm text-slate-400 mt-1">試試其他關鍵字或類別</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([cat, tools]) => (
            <div key={cat}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm font-semibold text-slate-700">
                  {CATEGORY_LABEL[cat] || cat}
                </span>
                <span className="badge-gray text-[11px]">{tools.length}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {tools.map(tool => (
                  <ToolCard key={tool.tool_id} tool={tool} onClick={() => navigate(`/tools/${tool.tool_id}`)} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ToolCard({ tool, onClick }: { tool: Tool; onClick: () => void }) {
  const colorClass = TOOL_COLOR_MAP[tool.color] || 'tool-blue'

  return (
    <button
      onClick={onClick}
      className="card-hover text-left p-5 flex flex-col gap-3 group"
    >
      <div className="flex items-start justify-between">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
          <FileText className="w-5 h-5" />
        </div>
        <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-brand-500 transition-colors mt-1 flex-shrink-0" />
      </div>

      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-slate-900 group-hover:text-brand-700 transition-colors">
          {tool.name_zh}
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">{tool.name_en}</p>
        <p className="text-xs text-slate-500 mt-1.5 leading-relaxed line-clamp-2">
          {tool.description_zh}
        </p>
      </div>

      {tool.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tool.tags.slice(0, 3).map(tag => (
            <span key={tag} className="badge-gray text-[10px]">{tag}</span>
          ))}
        </div>
      )}
    </button>
  )
}
