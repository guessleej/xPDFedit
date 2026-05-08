import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Wrench, ClipboardList,
  Settings, LogOut, User,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { authApi } from '../../lib/api'
import { LogoMark } from '../LogoMark'
import toast from 'react-hot-toast'

const NAV = [
  { to: '/',        icon: LayoutDashboard, label: '儀表板' },
  { to: '/tools',   icon: Wrench,          label: '工具箱' },
  { to: '/jobs',    icon: ClipboardList,   label: '我的作業' },
]

const ADMIN_NAV = [
  { to: '/admin',   icon: Settings,  label: '系統管理' },
]

export function Sidebar() {
  const { user, logout, refreshToken } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch {}
    logout()
    navigate('/login')
    toast.success('已安全登出')
  }

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-sidebar text-white flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/[0.07]">
        <LogoMark size={36} className="flex-shrink-0" />
        <div>
          <div className="text-[15px] font-bold text-white leading-tight tracking-wide">xPDFedit</div>
          <div className="text-[10px] text-slate-600 leading-tight tracking-wider">xCloudinfo</div>
        </div>
      </div>

      {/* 主導覽 */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-3 pb-2">主選單</p>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? 'active' : ''}`
            }
          >
            <Icon className="icon" />
            <span className="flex-1">{label}</span>
          </NavLink>
        ))}

        {user?.is_superadmin && (
          <>
            <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-3 pt-4 pb-2">管理</p>
            {ADMIN_NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
              >
                <Icon className="icon" />
                <span className="flex-1">{label}</span>
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* 使用者資訊 */}
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-sidebar-hover transition-colors">
          <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-600/25 flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-brand-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.display_name || user?.username}</p>
            <p className="text-xs text-slate-500 truncate">{user?.username}@{user?.realm}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-md text-slate-500 hover:text-white hover:bg-red-600/20 transition-colors"
            title="登出"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
