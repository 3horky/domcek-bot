import { Hash, RefreshCw, ShieldCheck, SmilePlus } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

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
import { UndoHistory } from '../components/UndoHistory'
import { Button } from '../components/ui/button'
import { ReactionsPanel } from './ReactionsPanel'
import { RolesPanel } from './RolesPanel'
import { ChannelsPanel, NoticeBanner, type Notice } from './SettingsPage'

export function ChannelsPage() {
  const auth = useAuth()
  const isAdmin =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_roles')
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [archives, setArchives] = useState<ArchiveRequest[]>([])
  const [notice, setNotice] = useState<Notice>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [undoRevision, setUndoRevision] = useState(0)
  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [nextDirectory, nextArchives] = await Promise.all([
        getDiscordDirectory(),
        getArchiveRequests(),
      ])
      setDirectory(nextDirectory)
      setArchives(nextArchives)
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
      title="Kanály"
      description="Vytváranie súkromných projektových priestorov a celý proces archivácie."
      icon={<Hash />}
      notice={notice}
      onReload={load}
    >
      {loading ? (
        <LoadingState label="Načítavam kanály a otvorené žiadosti…" />
      ) : loadError || !directory ? (
        <LoadErrorState
          detail={loadError ?? 'Carlo neposlal úplný zoznam kanálov.'}
          onRetry={() => void load()}
        />
      ) : (
        <>
          <ChannelsPanel
            directory={directory}
            archives={archives}
            isAdmin={isAdmin}
            onArchivesChanged={setArchives}
            onChanged={async () => {
              await load()
              setUndoRevision((current) => current + 1)
            }}
            setNotice={setNotice}
          />
          <UndoHistory scope="channels" revision={undoRevision} onChanged={load} />
        </>
      )}
    </AdministrationPage>
  )
}

export function RolesPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [undoRevision, setUndoRevision] = useState(0)
  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setSettings(await getAdminSettings())
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
      title="Roly a oprávnenia"
      description="Vyhľadajte človeka a skontrolujte alebo zmeňte jeho Carlo oprávnenia."
      icon={<ShieldCheck />}
      notice={notice}
      onReload={load}
    >
      {loading ? (
        <LoadingState label="Načítavam roly…" />
      ) : loadError || !settings ? (
        <LoadErrorState
          detail={loadError ?? 'Carlo neposlal úplné nastavenie rolí.'}
          onRetry={() => void load()}
        />
      ) : (
        <>
          <RolesPanel
            publication={settings.publication}
            setNotice={setNotice}
            onChanged={() => setUndoRevision((current) => current + 1)}
          />
          <UndoHistory scope="roles" revision={undoRevision} onChanged={load} />
        </>
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
  const [refreshing, setRefreshing] = useState(false)
  const refreshInFlight = useRef(false)
  async function refresh() {
    if (refreshInFlight.current) return
    refreshInFlight.current = true
    setRefreshing(true)
    try {
      await onReload()
    } finally {
      refreshInFlight.current = false
      setRefreshing(false)
    }
  }
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
        <Button variant="outline" disabled={refreshing} onClick={() => void refresh()}>
          <RefreshCw className={refreshing ? 'spin' : undefined} />
          {refreshing ? 'Načítavam aktuálny stav…' : 'Načítať aktuálny stav'}
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
