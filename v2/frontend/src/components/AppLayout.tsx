import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  Hash,
  History,
  House,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Settings2,
  ShieldCheck,
  SmilePlus,
} from 'lucide-react'

import { useAuth } from '../auth/context'

const navigation = [
  { to: '/', label: 'Prehľad', short: 'Prehľad', end: true, icon: LayoutDashboard },
  { to: '/oznamy', label: 'Redakčný pult', short: 'Oznamy', icon: Megaphone },
  { to: '/historia', label: 'História publikácií', short: 'História', icon: History },
]

export function AppLayout() {
  const auth = useAuth()
  if (auth.status !== 'authenticated') return null
  const { user, roles, capabilities } = auth.session
  const canEditContent = capabilities.includes('edit_content')
  const canChannels = capabilities.includes('manage_channels')
  const canSettings = capabilities.includes('manage_settings')
  const canRoles = capabilities.includes('manage_roles')
  const canManageServer = canChannels || canSettings || canRoles

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Preskočiť na obsah
      </a>
      <header className="topbar">
        <NavLink className="brand-link" to="/" aria-label="Carlo – prehľad">
          <div className="brand-mark" aria-hidden="true">
            <House />
          </div>
          <div className="brand-copy">
            <span>Carlo</span>
            <small>Správa oznamov</small>
          </div>
        </NavLink>
        <div className="user-menu">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" />
          ) : (
            <span className="user-avatar" aria-hidden="true">
              {user.display_name.slice(0, 1)}
            </span>
          )}
          <div>
            <strong>{user.display_name}</strong>
            <small>{roleLabel(roles)}</small>
          </div>
          <button
            className="logout-button"
            type="button"
            aria-label="Odhlásiť"
            onClick={() => void auth.signOut()}
          >
            <LogOut aria-hidden="true" />
            <span>Odhlásiť</span>
          </button>
        </div>
      </header>
      <div className="workspace">
        <nav className="sidebar" aria-label="Hlavná navigácia">
          <p className="nav-heading">Publikovanie</p>
          {navigation.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <item.icon aria-hidden="true" />
              <span className="nav-long">{item.label}</span>
              <span className="nav-short">{item.short}</span>
            </NavLink>
          ))}
          {canEditContent && <p className="nav-heading">Správa obsahu</p>}
          {canEditContent && (
            <NavLink to="/audit">
              <History aria-hidden="true" />
              <span className="nav-long">Audit</span>
              <span className="nav-short">Audit</span>
            </NavLink>
          )}
          {canManageServer && <p className="nav-heading">Správa servera</p>}
          {canChannels && (
            <NavLink to="/kanaly">
              <Hash aria-hidden="true" />
              <span className="nav-long">Kanály</span>
              <span className="nav-short">Kanály</span>
            </NavLink>
          )}
          {canRoles && (
            <NavLink to="/roly">
              <ShieldCheck aria-hidden="true" />
              <span className="nav-long">Roly</span>
              <span className="nav-short">Roly</span>
            </NavLink>
          )}
          {canSettings && (
            <NavLink to="/reakcie">
              <SmilePlus aria-hidden="true" />
              <span className="nav-long">Reakcie</span>
              <span className="nav-short">Reakcie</span>
            </NavLink>
          )}
          {canSettings && (
            <NavLink to="/nastavenia">
              <Settings2 aria-hidden="true" />
              <span className="nav-long">Nastavenia</span>
              <span className="nav-short">Nastaviť</span>
            </NavLink>
          )}
          <NavLink className="diagnostic-nav" to="/stav">
            <Activity aria-hidden="true" />
            <span className="nav-long">Stav systému</span>
            <span className="nav-short">Stav</span>
          </NavLink>
        </nav>
        <main id="main-content" className="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function roleLabel(roles: string[]) {
  if (roles.includes('admin')) return 'Admin'
  if (roles.includes('team_mod')) return 'Team Mod'
  if (roles.includes('publisher')) return 'SDB / FMA'
  return 'Člen'
}
