import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { Loading } from './components/ui'

/** Route-level code splitting: each page (and its chart deps) loads on demand. */
const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))
const CompanyExplorer = lazy(() => import('./pages/CompanyExplorer').then((m) => ({ default: m.CompanyExplorer })))
const CompanyDetail = lazy(() => import('./pages/CompanyDetail').then((m) => ({ default: m.CompanyDetail })))
const FilingSearch = lazy(() => import('./pages/FilingSearch').then((m) => ({ default: m.FilingSearch })))
const Compare = lazy(() => import('./pages/Compare').then((m) => ({ default: m.Compare })))
const PeerGroups = lazy(() => import('./pages/PeerGroups').then((m) => ({ default: m.PeerGroups })))
const Macro = lazy(() => import('./pages/Macro').then((m) => ({ default: m.Macro })))
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })))
const NotFound = lazy(() => import('./pages/NotFound').then((m) => ({ default: m.NotFound })))

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          path="/*"
          element={
            <Suspense fallback={<div className="page"><Loading /></div>}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/companies" element={<CompanyExplorer />} />
                <Route path="/companies/:id" element={<CompanyDetail />} />
                <Route path="/search" element={<FilingSearch />} />
                <Route path="/compare" element={<Compare />} />
                <Route path="/peers" element={<PeerGroups />} />
                <Route path="/macro" element={<Macro />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/explore" element={<Navigate to="/companies" replace />} />
                <Route path="/metadata" element={<Navigate to="/companies" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          }
        />
      </Route>
    </Routes>
  )
}
