import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { AuthProvider } from '../auth/AuthContext'
import { useAuth } from '../auth/context'
import { AppLayout } from '../components/AppLayout'
import { ErrorBoundary } from '../components/ErrorBoundary'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'

const AnnouncementsPage = lazy(() =>
  import('../pages/AnnouncementsPage').then((module) => ({ default: module.AnnouncementsPage })),
)
const AuditPage = lazy(() =>
  import('../pages/AuditPage').then((module) => ({ default: module.AuditPage })),
)
const PublicationHistoryPage = lazy(() =>
  import('../pages/PublicationHistoryPage').then((module) => ({
    default: module.PublicationHistoryPage,
  })),
)
const StatusPage = lazy(() =>
  import('../pages/StatusPage').then((module) => ({ default: module.StatusPage })),
)
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then((module) => ({ default: module.SettingsPage })),
)
const ChannelsPage = lazy(() =>
  import('../pages/DiscordAdministrationPages').then((module) => ({
    default: module.ChannelsPage,
  })),
)
const RolesPage = lazy(() =>
  import('../pages/DiscordAdministrationPages').then((module) => ({ default: module.RolesPage })),
)
const ReactionsPage = lazy(() =>
  import('../pages/DiscordAdministrationPages').then((module) => ({
    default: module.ReactionsPage,
  })),
)

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'oznamy', element: <AnnouncementsPage /> },
      { path: 'manualne-udalosti', element: <Navigate to="/oznamy" replace /> },
      { path: 'info', element: <Navigate to="/oznamy" replace /> },
      { path: 'audit', element: <AuditPage /> },
      { path: 'historia', element: <PublicationHistoryPage /> },
      { path: 'stav', element: <StatusPage /> },
      { path: 'nastavenia', element: <SettingsPage /> },
      { path: 'kanaly', element: <ChannelsPage /> },
      { path: 'roly', element: <RolesPage /> },
      { path: 'reakcie', element: <ReactionsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

function AuthenticatedApp() {
  const auth = useAuth()
  return auth.status === 'authenticated' ? (
    <Suspense fallback={<div className="route-loader">Načítavam pracovisko…</div>}>
      <RouterProvider router={router} />
    </Suspense>
  ) : (
    <LoginPage />
  )
}

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </ErrorBoundary>
  )
}
