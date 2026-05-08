import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2, Shield, Zap, Lock } from 'lucide-react'
import { authApi, realmApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import { LogoMark } from '../components/LogoMark'
import toast from 'react-hot-toast'

export function Login() {
  const navigate  = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm]       = useState({ username: '', password: '', realm: 'local' })
  const [showPw, setShowPw]   = useState(false)
  const [loading, setLoading] = useState(false)
  const [realms, setRealms]   = useState<{ name: string; type: string; label: string }[]>([
    { name: 'local', type: 'local', label: '本機帳號' }
  ])

  useEffect(() => {
    realmApi.listPublic().then(list => {
      if (list && list.length > 0) setRealms(list)
    }).catch(() => {})
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.username || !form.password) { toast.error('請填寫帳號與密碼'); return }
    setLoading(true)
    try {
      const data = await authApi.login(form.username, form.password, form.realm)
      localStorage.setItem('access_token', data.access_token)
      const user = await authApi.me()
      setAuth(user, data.access_token, data.refresh_token)
      toast.success(`歡迎回來，${user.display_name || user.username}！`)
      navigate('/')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '帳號或密碼錯誤')
    } finally {
      setLoading(false)
    }
  }

  return (
    /* ── 全頁深色背景 ── */
    <div className="min-h-screen flex items-center justify-center px-6 py-8 relative overflow-hidden"
         style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 0%, #1e0810 0%, #0a0a0f 60%)' }}>

      {/* 背景光點 */}
      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] rounded-full
                      bg-brand-700/15 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-[-5%] right-[15%] w-[350px] h-[350px] rounded-full
                      bg-brand-900/20 blur-[80px] pointer-events-none" />

      {/* ── 主卡片 ── */}
      <div className="relative w-full max-w-[1060px] flex rounded-2xl overflow-hidden
                      shadow-[0_40px_100px_-15px_rgba(0,0,0,0.85)]" style={{ minHeight: 'min(660px, 88vh)' }}>

        {/* ▌左側品牌面板 */}
        <div className="hidden lg:flex flex-col w-[420px] flex-shrink-0 relative overflow-hidden"
             style={{ background: 'linear-gradient(155deg, #c41230 0%, #8a0d22 55%, #5c0817 100%)' }}>

          {/* 面板裝飾 */}
          <div className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-white/5" />
          <div className="absolute -bottom-24 -left-12 w-72 h-72 rounded-full bg-black/20" />
          <div className="absolute inset-0"
               style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)', backgroundSize: '28px 28px' }} />

          {/* 內容 */}
          <div className="relative z-10 flex flex-col h-full px-10 py-12">

            {/* Logo */}
            <div className="flex items-center gap-3 mb-auto">
              <LogoMark size={42} className="flex-shrink-0" />
              <div>
                <p className="text-[15px] font-bold text-white leading-none tracking-wide">xPDFedit</p>
                <p className="text-[10px] text-white/50 tracking-widest mt-1">xCloudinfo</p>
              </div>
            </div>

            {/* 主視覺 */}
            <div className="flex-1 flex flex-col justify-center py-10">
              <h2 className="text-[36px] font-bold text-white leading-[1.2] tracking-tight">
                讓文件處理<br/>
                快一個量級
              </h2>
              <p className="mt-4 text-white/60 text-sm leading-[1.9]">
                整合 30+ PDF 工具，企業級<br/>
                認證與私有化部署。
              </p>

              {/* 特點列 */}
              <div className="mt-8 space-y-4">
                {[
                  { icon: Shield, text: 'LDAP / AD 企業認證' },
                  { icon: Zap,    text: '批次非同步處理引擎' },
                  { icon: Lock,   text: '完整 Docker 私有部署' },
                ].map(({ icon: Icon, text }) => (
                  <div key={text} className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-3.5 h-3.5 text-white/80" />
                    </div>
                    <span className="text-sm text-white/70">{text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 底部 */}
            <p className="text-[11px] text-white/30 tracking-wider">
              © 2025 xCloudinfo
            </p>
          </div>
        </div>

        {/* ▌右側登入面板 */}
        <div className="flex-1 bg-white flex flex-col">

          {/* 頂部空白 */}
          <div className="flex-[1.2]" />

          {/* 表單主體 */}
          <div className="px-10 lg:px-14">

            {/* Mobile logo */}
            <div className="flex items-center gap-3 mb-8 lg:hidden">
              <LogoMark size={34} className="flex-shrink-0" />
              <span className="font-bold text-slate-900">xPDFedit</span>
            </div>

            {/* 標題 */}
            <div className="mb-7">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">歡迎回來</h1>
              <p className="text-slate-400 text-sm mt-1.5">請登入以繼續使用 xPDFedit</p>
            </div>

            {/* 表單 */}
            <form onSubmit={handleSubmit} className="space-y-4">

              {/* Realm */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  登入網域
                </label>
                <div className="relative">
                  <select
                    value={form.realm}
                    onChange={e => setForm(f => ({ ...f, realm: e.target.value }))}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50
                               text-slate-700 text-sm appearance-none pr-9
                               focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400
                               focus:bg-white transition-all"
                  >
                    {realms.map(r => (
                      <option key={r.name} value={r.name}>{r.label}</option>
                    ))}
                  </select>
                  <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none"
                       viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6"/>
                  </svg>
                </div>
              </div>

              {/* Username */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  帳號
                </label>
                <input
                  type="text"
                  value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                  placeholder="輸入帳號"
                  autoComplete="username"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50
                             text-slate-900 text-sm placeholder:text-slate-300
                             focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400
                             focus:bg-white transition-all"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  密碼
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="輸入密碼"
                    autoComplete="current-password"
                    className="w-full px-3.5 py-2.5 pr-11 rounded-lg border border-slate-200 bg-slate-50
                               text-slate-900 text-sm placeholder:text-slate-300
                               focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400
                               focus:bg-white transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500 transition-colors"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* 登入按鈕 */}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 mt-1
                           bg-brand-600 hover:bg-brand-700 active:bg-brand-800
                           text-white text-sm font-semibold tracking-wide
                           py-3 rounded-lg transition-all duration-150
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
                           disabled:opacity-60 disabled:cursor-not-allowed
                           shadow-sm hover:shadow-[0_4px_20px_-4px_rgba(196,18,48,0.5)]"
              >
                {loading
                  ? <><Loader2 className="w-4 h-4 animate-spin" />登入中...</>
                  : '登　入'
                }
              </button>
            </form>

            {/* 預設帳號 */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <p className="text-[11px] text-slate-400 text-center">
                預設&ensp;
                <code className="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">admin</code>
                &ensp;/&ensp;
                <code className="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">admin1234</code>
              </p>
            </div>
          </div>

          {/* 底部空白 */}
          <div className="flex-[1.2]" />

          {/* 右側底部品牌標記 */}
          <div className="px-14 pb-6 flex-shrink-0">
            <div className="flex items-center justify-center gap-1.5">
              <div className="w-1 h-1 rounded-full bg-slate-200" />
              <p className="text-[10px] text-slate-300 tracking-widest uppercase">Powered by xCloudinfo</p>
              <div className="w-1 h-1 rounded-full bg-slate-200" />
            </div>
          </div>
        </div>

      </div>

      {/* 卡片下方版權 */}
      <p className="absolute bottom-5 left-1/2 -translate-x-1/2 text-[11px] text-white/20 tracking-wider whitespace-nowrap">
        © 2025 xCloudinfo · All rights reserved.
      </p>
    </div>
  )
}
