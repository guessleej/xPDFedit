import { Outlet, Navigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '../../stores/authStore'

export function Layout() {
  const { isAuthenticated } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
        <div className="flex-1 p-6 lg:p-8 animate-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
