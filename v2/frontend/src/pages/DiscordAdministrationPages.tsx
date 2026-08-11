import { Hash, RefreshCw, ShieldCheck, SmilePlus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import {
  ApiError,
  type AdminSettings,
  type ArchiveRequest,
  type DiscordDirectory,
  getAdminSettings,
  getArchiveRequests,
  getDiscordDirectory,
} from '../api/client'
import { useAuth } from '../auth/context'
import { LoadErrorState, LoadingState } from '../components/AsyncState'
import { Button } from '../components/ui/button'
import { ReactionsPanel } from './ReactionsPanel'
import { ChannelsPanel, NoticeBanner, RolesPanel, type Notice } from './SettingsPage'

export function ChannelsPage() {
  const auth = useAuth()
  const isAdmin =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_roles')
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [archives, setArchives] = useState<ArchiveRequest[]>([])
  const [notice, setNotice] = useState<Notice>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    try {
      const [nextDirectory, nextArchives] = await Promise.all([
        getDiscordDirectory(),
        getArchiveRequests(),
      ])
      setDirectory(nextDirectory)
      setArchives(nextArchives)
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  return (
    <AdministrationPage
      eyebrow="Správa servera"
      title="Kanály"
      description="Vytváranie súkromných projektových priestorov a celý proces archivácie."
      icon={<Hash />}
      notice={notice}
      onReload={load}
    >
      {loading || !directory ? (
        <LoadingState label="Načítavam kanály a otvorené žiadosti…" />
      ) : (
        <ChannelsPanel
          directory={directory}
          archives={archives}
          isAdmin={isAdmin}
          onArchivesChanged={setArchives}
          setNotice={setNotice}
        />
      )}
    </AdministrationPage>
  )
}

export function RolesPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    try {
      setSettings(await getAdminSettings())
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  return (
    <AdministrationPage
      eyebrow="Správa servera"
      title="Roly a oprávnenia"
      description="Vyhľadajte človeka a skontrolujte alebo zmeňte jeho Carlo oprávnenia."
      icon={<ShieldCheck />}
      notice={notice}
      onReload={load}
    >
      {loading || !settings ? (
        <LoadingState label="Načítavam roly…" />
      ) : (
        <RolesPanel publication={settings.publication} setNotice={setNotice} />
      )}
    </AdministrationPage>
  )
}

export function ReactionsPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [nextSettings, nextDirectory] = await Promise.all([
        getAdminSettings(),
        getDiscordDirectory(),
      ])
      setSettings(nextSettings)
      setDirectory(nextDirectory)
    } catch (error) {
      setLoadError(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  return (
    <AdministrationPage
      eyebrow="Správa servera"
      title="Automatické reakcie"
      description="Emoji správanie Carla a kanály, v ktorých má reagovať."
      icon={<SmilePlus />}
      notice={notice}
      onReload={load}
    >
      {loading ? (
        <LoadingState label="Načítavam reakcie a emoji…" />
      ) : loadError || !settings || !directory ? (
        <LoadErrorState
          detail={loadError ?? 'Carlo neposlal úplné nastavenie reakcií.'}
          onRetry={() => void load()}
        />
      ) : (
        <ReactionsPanel
          value={settings.reactions}
          directory={directory}
          onSaved={(reactions) => setSettings({ ...settings, reactions })}
          setNotice={setNotice}
        />
      )}
    </AdministrationPage>
  )
}

function AdministrationPage({
  eyebrow,
  title,
  description,
  icon,
  notice,
  onReload,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  icon: React.ReactNode
  notice: Notice
  onReload: () => Promise<void>
  children: React.ReactNode
}) {
  return (
    <section className="settings-page administration-page">
      <header className="settings-hero administration-hero">
        <div className="administration-title">
          <span className="administration-title-icon">{icon}</span>
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => void onReload()}>
          <RefreshCw /> Obnoviť údaje
        </Button>
      </header>
      {notice && <NoticeBanner notice={notice} />}
      {children}
    </section>
  )
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : 'Údaje sa nepodarilo bezpečne načítať.'
}
