import { useAuth } from '../auth/context'
import { Button, buttonVariants } from '../components/ui/button'

export function LoginPage() {
  const auth = useAuth()
  const returnTo = `${window.location.pathname}${window.location.search}`
  const loginUrl = `/api/v1/auth/discord/login?return_to=${encodeURIComponent(returnTo)}`

  if (auth.status === 'loading') {
    return (
      <main className="auth-page" aria-live="polite">
        <div className="auth-card auth-loading">
          <span className="loading-orb" aria-hidden="true" />
          <p>Overujem prihlásenie…</p>
        </div>
      </main>
    )
  }

  if (auth.status === 'error') {
    return (
      <main className="auth-page">
        <div className="auth-card" role="alert">
          <p className="eyebrow">Spojenie zlyhalo</p>
          <h1>Carlo sa nedá načítať</h1>
          <p>{auth.error.message}</p>
          <Button type="button" onClick={auth.retry}>
            Skúsiť znova
          </Button>
        </div>
      </main>
    )
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark brand-mark-large" aria-hidden="true">
          D
        </div>
        <p className="eyebrow">Carlo</p>
        <h1>Oznamy pripravené bez ručnej roboty</h1>
        {auth.sessionExpired ? (
          <div className="session-expired-message" role="alert">
            <strong>Relácia vypršala</strong>
            <p>
              Rozpracované hodnoty sme neodoslali. Prihláste sa znova a Carlo obnoví uložený návrh
              tam, kde je to možné.
            </p>
          </div>
        ) : (
          <p>Prihláste sa cez Discord. Prístup dostanú iba členovia servera s povolenou rolou.</p>
        )}
        <a className={`${buttonVariants()} discord-button`} href={loginUrl}>
          Prihlásiť cez Discord
        </a>
        <small>Bot nikdy neposiela Discord prihlasovacie údaje do tejto stránky.</small>
      </section>
    </main>
  )
}
