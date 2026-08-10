import { useAuth } from '../auth/context'

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
          <h1>Administrácia sa nedá načítať</h1>
          <p>{auth.error.message}</p>
          <button type="button" onClick={auth.retry}>
            Skúsiť znova
          </button>
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
        <p>Prihlás sa cez Discord. Prístup dostanú iba členovia servera s povolenou rolou.</p>
        <a className="primary-button discord-button" href={loginUrl}>
          Prihlásiť cez Discord
        </a>
        <small>Bot nikdy neposiela Discord prihlasovacie údaje do tejto stránky.</small>
      </section>
    </main>
  )
}
