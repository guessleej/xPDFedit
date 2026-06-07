import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search as SearchIcon, FileText, Database, ChevronRight, X, Loader2 } from 'lucide-react'
import { searchApi, type SemanticResult } from '../lib/api'
import toast from 'react-hot-toast'

export function Search() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [topK, setTopK] = useState(10)
  const [filenameFilter, setFilenameFilter] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SemanticResult[] | null>(null)
  const [lastQuery, setLastQuery] = useState('')

  // 索引統計
  const { data: stats } = useQuery({
    queryKey: ['search-stats'],
    queryFn: () => searchApi.stats(),
    staleTime: 60_000,
  })

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setIsSearching(true)
    setSubmitted(query.trim())
    try {
      const resp = await searchApi.semantic(query.trim(), topK, filenameFilter || undefined)
      setResults(resp.results)
      setLastQuery(resp.query)
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? '搜尋失敗，請確認語意索引服務是否已啟動'
      toast.error(msg)
      setResults(null)
    } finally {
      setIsSearching(false)
    }
  }, [query, topK, filenameFilter])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const scoreColor = (score: number) => {
    if (score >= 0.85) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
    if (score >= 0.70) return 'bg-blue-500/20 text-blue-300 border-blue-500/30'
    return 'bg-slate-500/20 text-slate-300 border-slate-500/30'
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <SearchIcon className="w-6 h-6 text-brand-400" />
          語意搜尋
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          以自然語言搜尋已索引的文件內容（bge-m3 向量 + Elasticsearch kNN）
        </p>
      </div>

      {/* 索引統計 */}
      {stats && (
        <div className="flex items-center gap-4 p-3 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm">
          <Database className="w-4 h-4 text-teal-400 flex-shrink-0" />
          <span className="text-slate-300">
            已索引 <span className="text-white font-medium">{stats.files.length}</span> 份文件、
            <span className="text-white font-medium">{stats.total_chunks.toLocaleString()}</span> 個段落
          </span>
          {stats.files.length > 0 && (
            <div className="ml-auto flex flex-wrap gap-1 max-w-sm justify-end">
              {stats.files.slice(0, 5).map(f => (
                <button
                  key={f.filename}
                  onClick={() => setFilenameFilter(prev => prev === f.filename ? '' : f.filename)}
                  className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                    filenameFilter === f.filename
                      ? 'bg-brand-600/30 border-brand-500/50 text-brand-300'
                      : 'bg-slate-700/50 border-slate-600/50 text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {f.filename.length > 20 ? f.filename.slice(0, 18) + '…' : f.filename}
                </button>
              ))}
              {stats.files.length > 5 && (
                <span className="text-xs text-slate-500 self-center">+{stats.files.length - 5}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* 搜尋框 */}
      <div className="space-y-3">
        <div className="relative">
          <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="輸入問句或關鍵字，例如：GPU 伺服器的儲存規格"
            className="w-full pl-12 pr-4 py-3 rounded-xl bg-slate-800 border border-slate-700 text-white placeholder-slate-500
                       focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 transition"
          />
        </div>

        <div className="flex items-center gap-3">
          {/* 限定檔名 */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={filenameFilter}
              onChange={e => setFilenameFilter(e.target.value)}
              placeholder="限定檔名（選填）"
              className="w-full px-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-700 text-white
                         placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
            />
            {filenameFilter && (
              <button
                onClick={() => setFilenameFilter('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* 回傳筆數 */}
          <select
            value={topK}
            onChange={e => setTopK(Number(e.target.value))}
            className="px-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-700 text-white
                       focus:outline-none focus:border-brand-500 transition"
          >
            {[5, 10, 20, 50].map(n => (
              <option key={n} value={n}>前 {n} 筆</option>
            ))}
          </select>

          {/* 搜尋按鈕 */}
          <button
            onClick={handleSearch}
            disabled={!query.trim() || isSearching}
            className="px-5 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50
                       disabled:cursor-not-allowed text-white text-sm font-medium transition flex items-center gap-2"
          >
            {isSearching
              ? <><Loader2 className="w-4 h-4 animate-spin" />搜尋中</>
              : <><SearchIcon className="w-4 h-4" />搜尋</>
            }
          </button>
        </div>
      </div>

      {/* 結果 */}
      {results !== null && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <p className="text-slate-400">
              「<span className="text-white">{lastQuery}</span>」共 {results.length} 筆結果
            </p>
            {filenameFilter && (
              <span className="text-xs text-brand-400 bg-brand-600/10 border border-brand-500/20 px-2 py-0.5 rounded">
                限定：{filenameFilter}
              </span>
            )}
          </div>

          {results.length === 0 ? (
            <div className="text-center py-16 text-slate-500">
              <SearchIcon className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>找不到相關段落</p>
              <p className="text-xs mt-1">請嘗試調整問句，或先使用「語意索引」工具建立向量索引</p>
            </div>
          ) : (
            results.map((r, i) => (
              <div
                key={`${r.filename}-${r.page}-${r.chunk}-${i}`}
                className="p-4 rounded-xl bg-slate-800/70 border border-slate-700/60 hover:border-slate-600/60 transition group"
              >
                <div className="flex items-start gap-3">
                  <FileText className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-sm font-medium text-brand-400 truncate max-w-xs">
                        {r.filename}
                      </span>
                      <ChevronRight className="w-3 h-3 text-slate-600 flex-shrink-0" />
                      <span className="text-xs text-slate-500">第 {r.page} 頁，段落 {r.chunk}</span>
                      <span className={`ml-auto text-xs px-2 py-0.5 rounded-full border font-medium ${scoreColor(r.score)}`}>
                        {(r.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed line-clamp-4">
                      {r.text}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 初始空白狀態 */}
      {results === null && !isSearching && (
        <div className="text-center py-20 text-slate-600">
          <SearchIcon className="w-12 h-12 mx-auto mb-4 opacity-20" />
          <p className="text-sm">輸入問句後按 Enter 或點「搜尋」</p>
          {stats?.total_chunks === 0 && (
            <p className="text-xs mt-2 text-slate-700">
              尚無索引資料，請先使用工具箱中的「語意索引」功能建立向量索引
            </p>
          )}
        </div>
      )}
    </div>
  )
}
