import { Suspense, useRef, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity,
  Hash,
  History,
  House,
  LayoutDashboard,
  LogOut,
  Menu,
  Megaphone,
  Settings2,
  ShieldCheck,
  SmilePlus,
} from 'lucide-react'

import { useAuth } from '../auth/context'
import { LoadingState } from './AsyncState'
import { Button, buttonVariants } from './ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog'

const navigation = [
  { to: '/', label: 'Prehľad', short: 'Prehľad', end: true, icon: LayoutDashboard },
  { to: '/oznamy', label: 'Redakčný pult', short: 'Oznamy', icon: Megaphone },
  { to: '/historia', label: 'História publikácií', short: 'História', icon: History },
]

export function AppLayout() {
  const auth = useAuth()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [sessionCheckFailed, setSessionCheckFailed] = useState(false)
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null)
  const sessionCheckButtonRef = useRef<HTMLButtonElement>(null)
  if (auth.status !== 'authenticated') return null
  const { user, roles, capabilities } = auth.session
  const canEditContent = capabilities.includes('edit_content')
  const canChannels = capabilities.includes('manage_channels')
  const canSettings = capabilities.includes('manage_settings')
  const canRoles = capabilities.includes('manage_roles')
  const canManageServer = canChannels || canSettings || canRoles
  const secondaryRouteActive = [
    '/audit',
    '/kanaly',
    '/roly',
    '/reakcie',
    '/nastavenia',
    '/stav',
  ].some((path) => location.pathname.startsWith(path))
  const returnTo = `${window.location.pathname}${window.location.search}`
  const loginUrl = `/api/v1/auth/discord/login?return_to=${encodeURIComponent(returnTo)}`

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
        <nav className="sidebar desktop-navigation" aria-label="Hlavná navigácia">
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
          <Suspense fallback={<LoadingState label="Načítavam pracovisko…" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <nav className="mobile-navigation" aria-label="Hlavná mobilná navigácia">
        {navigation.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <item.icon aria-hidden="true" />
            <span>{item.short}</span>
          </NavLink>
        ))}
        <Button
          ref={mobileMenuButtonRef}
          variant="ghost"
          className={secondaryRouteActive ? 'active' : undefined}
          aria-expanded={mobileMenuOpen}
          aria-haspopup="dialog"
          onClick={() => setMobileMenuOpen(true)}
        >
          <Menu aria-hidden="true" />
          <span>Viac</span>
        </Button>
      </nav>
      <Dialog open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <DialogContent
          className="mobile-navigation-dialog"
          finalFocus={() => mobileMenuButtonRef.current}
        >
          <DialogHeader>
            <DialogTitle>Ďalšie časti Carla</DialogTitle>
            <DialogDescription>
              Správa obsahu, servera a kontrola technického stavu.
            </DialogDescription>
          </DialogHeader>
          <div className="mobile-navigation-sections">
            {canEditContent && (
              <MobileNavigationSection title="Správa obsahu">
                <MobileNavigationLink to="/audit" label="Audit" icon={History} close={closeMenu} />
              </MobileNavigationSection>
            )}
            {canManageServer && (
              <MobileNavigationSection title="Správa servera">
                {canChannels && (
                  <MobileNavigationLink to="/kanaly" label="Kanály" icon={Hash} close={closeMenu} />
                )}
                {canRoles && (
                  <MobileNavigationLink
                    to="/roly"
                    label="Roly a oprávnenia"
                    icon={ShieldCheck}
                    close={closeMenu}
                  />
                )}
                {canSettings && (
                  <MobileNavigationLink
                    to="/reakcie"
                    label="Automatické reakcie"
                    icon={SmilePlus}
                    close={closeMenu}
                  />
                )}
                {canSettings && (
                  <MobileNavigationLink
                    to="/nastavenia"
                    label="Nastavenia"
                    icon={Settings2}
                    close={closeMenu}
                  />
                )}
              </MobileNavigationSection>
            )}
            <MobileNavigationSection title="Pomoc a diagnostika">
              <MobileNavigationLink
                to="/stav"
                label="Stav systému"
                icon={Activity}
                close={closeMenu}
              />
            </MobileNavigationSection>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={auth.sessionExpired} onOpenChange={() => undefined}>
        <DialogContent
          className="session-expired-dialog"
          showCloseButton={false}
          initialFocus={() => sessionCheckButtonRef.current}
        >
          <DialogHeader>
            <DialogTitle>Relácia vypršala</DialogTitle>
            <DialogDescription>
              Rozpracované hodnoty zostali v tejto karte a Carlo ich neodoslal. Prihláste sa v novej
              karte, potom sa sem vráťte a overte prihlásenie.
            </DialogDescription>
          </DialogHeader>
          {sessionCheckFailed && (
            <p className="session-check-error" role="alert">
              Prihlásenie ešte nie je aktívne. Dokončite ho v novej karte a skúste overenie znova.
            </p>
          )}
          <div className="session-expired-actions">
            <a
              className={buttonVariants({ variant: 'outline' })}
              href={loginUrl}
              target="_blank"
              rel="noreferrer"
            >
              Prihlásiť sa v novej karte
            </a>
            <Button
              ref={sessionCheckButtonRef}
              onClick={async () => {
                setSessionCheckFailed(false)
                const refreshed = await auth.refreshSession()
                setSessionCheckFailed(!refreshed)
              }}
            >
              Overiť prihlásenie
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )

  function closeMenu() {
    setMobileMenuOpen(false)
  }
}

function MobileNavigationSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mobile-navigation-section">
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  )
}

function MobileNavigationLink({
  to,
  label,
  icon: Icon,
  close,
}: {
  to: string
  label: string
  icon: typeof Activity
  close: () => void
}) {
  return (
    <NavLink to={to} onClick={close}>
      <Icon aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  )
}

function roleLabel(roles: string[]) {
  if (roles.includes('admin')) return 'Admin'
  if (roles.includes('team_mod')) return 'Team Mod'
  if (roles.includes('publisher')) return 'SDB / FMA'
  return 'Člen'
}
