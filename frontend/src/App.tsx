import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router-dom'
import ApiHealthBanner from './ApiHealthBanner'
import CompanyEdgarSummary from './CompanyEdgarSummary'
import CompanyMetadataExplorer from './CompanyMetadataExplorer'
import EdgarDashboard from './EdgarDashboard'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <ApiHealthBanner />
        <nav className="app-nav" aria-label="Primary">
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? 'nav-link nav-link-active' : 'nav-link')}
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/explore"
            className={({ isActive }) => (isActive ? 'nav-link nav-link-active' : 'nav-link')}
          >
            Companies
          </NavLink>
        </nav>
        <Routes>
          <Route path="/" element={<EdgarDashboard />} />
          <Route path="/explore" element={<CompanyMetadataExplorer />} />
          <Route path="/companies/:id" element={<CompanyEdgarSummary />} />
          <Route path="/metadata" element={<Navigate to="/explore" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
