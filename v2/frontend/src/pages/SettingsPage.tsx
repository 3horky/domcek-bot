import {
  Archive,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  LoaderCircle,
  MessageSquareMore,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react'
import {
  cloneElement,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'

import {
  ApiError,
  type AdminSettings,
  type ArchiveRequest,
  type CalendarSource,
  type DiscordDirectory,
  type DiscordMemberOption,
  type ManualPublicationPreview,
  type PublicationSettings,
  type ReactionSettings,
  createArchiveRequest,
  createCalendarSource,
  createDiscordChannel,
  confirmManualPublication,
  decideArchiveRequest,
  getAdminSettings,
  getDiscordDirectory,
  prepareManualPublication,
  recoverArchiveRequests,
  searchDiscordMembers,
  setDiscordRole,
  syncCalendarSource,
  testDiscordReaction,
  updateCalendarSource,
  updatePublicationSettings,
  updateReactionSettings,
} from '../api/client'
import { useAuth } from '../auth/context'
import { DiscordPreview } from '../components/DiscordPreview'
import { ChannelMultiPicker, MemberPicker, RolePicker } from '../components/DiscordPickers'
import { Badge } from '../components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Textarea } from '../components/ui/textarea'

const weekdays = ['pondelok', 'utorok', 'streda', 'štvrtok', 'piatok', 'sobota', 'nedeľa']

export type Notice = { kind: 'success' | 'error'; text: string } | null

export function SettingsPage() {
  const auth = useAuth()
  const canAdmin =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_settings')
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<Notice>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const [directoryValue, settingsValue] = await Promise.all([
        getDiscordDirectory(),
        canAdmin ? getAdminSettings() : Promise.resolve(null),
      ])
      setDirectory(directoryValue)
      setSettings(settingsValue)
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setLoading(false)
    }
  }, [canAdmin])

  useEffect(() => {
    let cancelled = false
    void Promise.all([getDiscordDirectory(), canAdmin ? getAdminSettings() : Promise.resolve(null)])
      .then(([directoryValue, settingsValue]) => {
        if (cancelled) return
        setDirectory(directoryValue)
        setSettings(settingsValue)
      })
      .catch((error: unknown) => {
        if (!cancelled) setNotice({ kind: 'error', text: message(error) })
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [canAdmin])

  if (loading) return <SettingsSkeleton />
  if (!directory) return <PageError notice={notice} onRetry={() => void reload()} />

  return (
    <section className="settings-page">
      <header className="settings-hero">
        <div>
          <p className="eyebrow">Riadiace centrum</p>
          <h1>Nastavenia Carla</h1>
          <p>Časovanie, obsah publikovania a zdroje z Google kalendára.</p>
        </div>
        <Button variant="outline" onClick={() => void reload()}>
          <RefreshCw /> Obnoviť údaje
        </Button>
      </header>
      {notice && <NoticeBanner notice={notice} />}
      <Tabs defaultValue="publikovanie" className="settings-workspace">
        <TabsList className="settings-tabs" aria-label="Sekcie nastavení">
          {canAdmin && (
            <TabsTrigger value="publikovanie">
              <Clock3 />
              Publikovanie
            </TabsTrigger>
          )}
          {canAdmin && (
            <TabsTrigger value="kalendare">
              <CalendarDays />
              Kalendáre
            </TabsTrigger>
          )}
        </TabsList>
        {canAdmin && settings && (
          <TabsContent value="publikovanie">
            <PublicationPanel
              value={settings.publication}
              directory={directory}
              onSaved={(value) => {
                setSettings({ ...settings, publication: value })
                setNotice({ kind: 'success', text: 'Publikačné nastavenia sú uložené.' })
              }}
              onError={(text) => setNotice({ kind: 'error', text })}
              onPublished={(text) => setNotice({ kind: 'success', text })}
            />
          </TabsContent>
        )}
        {canAdmin && settings && (
          <TabsContent value="kalendare">
            <CalendarsPanel
              items={settings.calendars}
              onChanged={(items) => setSettings({ ...settings, calendars: items })}
              setNotice={setNotice}
            />
          </TabsContent>
        )}
      </Tabs>
    </section>
  )
}

function PublicationPanel({
  value,
  directory,
  onSaved,
  onError,
  onPublished,
}: {
  value: PublicationSettings
  directory: DiscordDirectory
  onSaved: (value: PublicationSettings) => void
  onError: (text: string) => void
  onPublished: (text: string) => void
}) {
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const [publishPreview, setPublishPreview] = useState<ManualPublicationPreview | null>(null)
  const [publishing, setPublishing] = useState(false)
  const nextLabel = useMemo(() => nextPublicationLabel(draft), [draft])
  async function save() {
    setSaving(true)
    try {
      onSaved(await updatePublicationSettings(draft))
    } catch (error) {
      onError(message(error))
    } finally {
      setSaving(false)
    }
  }
  async function preparePublish() {
    setPublishing(true)
    try {
      setPublishPreview(await prepareManualPublication())
    } catch (error) {
      onError(message(error))
    } finally {
      setPublishing(false)
    }
  }
  async function publish() {
    if (!publishPreview) return
    setPublishing(true)
    try {
      const result = await confirmManualPublication(publishPreview.confirmation_token)
      setPublishPreview(null)
      onPublished(`Publikovanie skončilo stavom ${result.state}.`)
    } catch (error) {
      onError(message(error))
    } finally {
      setPublishing(false)
    }
  }
  return (
    <div className="settings-grid settings-grid-main">
      <div className="settings-stack">
        <Card>
          <CardHeader>
            <CardTitle>Týždenný rytmus</CardTitle>
            <CardDescription>
              Kedy Carlo uzavrie redakciu a zverejní nasledujúcich 14 dní.
            </CardDescription>
          </CardHeader>
          <CardContent className="settings-form-grid">
            <Field label="Deň publikovania">
              <select
                value={draft.publication_weekday}
                onChange={(event) =>
                  setDraft({ ...draft, publication_weekday: Number(event.target.value) })
                }
              >
                {weekdays.map((day, index) => (
                  <option key={day} value={index}>
                    {day.charAt(0).toUpperCase() + day.slice(1)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Čas">
              <Input
                type="time"
                value={draft.publication_time.slice(0, 5)}
                onChange={(event) => setDraft({ ...draft, publication_time: event.target.value })}
              />
            </Field>
            <Field label="Časové pásmo">
              <Input
                value={draft.timezone}
                onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}
              />
            </Field>
            <div className="next-run-card">
              <Clock3 />
              <div>
                <small>Najbližší termín</small>
                <strong>{nextLabel}</strong>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Obsah oznamov</CardTitle>
            <CardDescription>
              Predvolené správanie automaticky zostaveného prehľadu.
            </CardDescription>
          </CardHeader>
          <CardContent className="toggle-stack">
            <ToggleRow
              title="Automatické publikovanie"
              description="Carlo publikuje bez potreby ručného potvrdenia."
              checked={draft.automatic_publication_enabled}
              onChecked={(checked) =>
                setDraft({ ...draft, automatic_publication_enabled: checked })
              }
            />
            <ToggleRow
              title="Popisy z Google kalendára"
              description="Nové udalosti použijú kalendárový popis, pokiaľ ho redakcia neupraví."
              checked={draft.publish_google_descriptions}
              onChecked={(checked) => setDraft({ ...draft, publish_google_descriptions: checked })}
            />
            <ToggleRow
              title="Automaticky vytvorený úvod"
              description="Pri nedostupnosti generátora sa použije bezpečný slovenský text."
              checked={draft.generated_intro_enabled}
              onChecked={(checked) => setDraft({ ...draft, generated_intro_enabled: checked })}
            />
            <div className="toggle-row">
              <div>
                <strong>Upozornenie @everyone</strong>
                <span>Carlo ho povinne vloží práve raz, iba do prvej správy.</span>
              </div>
              <span className="status-badge">Vždy zapnuté</span>
            </div>
            <ToggleRow
              title="Núdzovo použiť posledné dáta kalendára"
              description="Ak finálna synchronizácia zlyhá, Carlo smie publikovať iba ešte bezpečne čerstvú cache. Predvolene je publikovanie zablokované."
              checked={draft.allow_stale_calendar_cache}
              onChecked={(checked) => setDraft({ ...draft, allow_stale_calendar_cache: checked })}
            />
            <Field label="Záverečná správa (voliteľná)">
              <Textarea
                value={draft.closing_message ?? ''}
                onChange={(event) =>
                  setDraft({ ...draft, closing_message: event.target.value || null })
                }
              />
            </Field>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Prevádzkové upozornenia</CardTitle>
            <CardDescription>
              Kategórie správ, ktoré Carlo pošle do kanála moderátorov. Každá má odlišné označenie.
            </CardDescription>
          </CardHeader>
          <CardContent className="toggle-stack">
            <ToggleRow
              title="Google kalendáre"
              description="Zlyhaný sync a nejednoznačné zmeny opakovaných udalostí."
              checked={draft.alert_calendar_sync_enabled}
              onChecked={(checked) => setDraft({ ...draft, alert_calendar_sync_enabled: checked })}
            />
            <ToggleRow
              title="Publikovanie a recovery"
              description="Blokovanie, čiastočný výstup, retry a potrebný zásah Admina."
              checked={draft.alert_publication_enabled}
              onChecked={(checked) => setDraft({ ...draft, alert_publication_enabled: checked })}
            />
            <ToggleRow
              title="Kanálové operácie"
              description="Zlyhané vytvorenie alebo archivácia projektového kanála."
              checked={draft.alert_channel_operations_enabled}
              onChecked={(checked) =>
                setDraft({ ...draft, alert_channel_operations_enabled: checked })
              }
            />
            <ToggleRow
              title="Zmeny rolí"
              description="Zlyhanie pri udeľovaní alebo odoberaní Team Mod či Admin."
              checked={draft.alert_role_operations_enabled}
              onChecked={(checked) =>
                setDraft({ ...draft, alert_role_operations_enabled: checked })
              }
            />
            <ToggleRow
              title="Pripomienka pred publikovaním"
              description="Voliteľná redakčná pripomienka pred najbližším termínom."
              checked={draft.alert_publication_reminder_enabled}
              onChecked={(checked) =>
                setDraft({ ...draft, alert_publication_reminder_enabled: checked })
              }
            />
          </CardContent>
        </Card>
      </div>
      <Card className="settings-side-card">
        <CardHeader>
          <CardTitle>Miesta na Discorde</CardTitle>
          <CardDescription>Kanály a kategórie, ktoré Carlo používa pri práci.</CardDescription>
        </CardHeader>
        <CardContent className="settings-fields">
          <ChannelSelect
            label="Oznamy"
            value={draft.announcement_channel_id}
            channels={directory.channels}
            onChange={(id) => setDraft({ ...draft, announcement_channel_id: id })}
          />
          <ChannelSelect
            label="Moderátori"
            value={draft.moderator_channel_id}
            channels={directory.channels}
            onChange={(id) => setDraft({ ...draft, moderator_channel_id: id })}
          />
          <ChannelSelect
            label="Príkazy"
            value={draft.command_channel_id}
            channels={directory.channels}
            onChange={(id) => setDraft({ ...draft, command_channel_id: id })}
          />
          <Button className="settings-save" disabled={saving} onClick={() => void save()}>
            {saving ? <LoaderCircle className="spin" /> : <Check />} Uložiť nastavenia
          </Button>
          <div className="manual-publish-box">
            <div>
              <strong>Ručné publikovanie</strong>
              <span>Úspech preskočí iba najbližší pravidelný termín.</span>
            </div>
            {publishPreview ? (
              <div className="manual-publish-confirm">
                <p>
                  {publishPreview.announcement_count} položiek v {publishPreview.message_count}{' '}
                  správach · {dateTime(publishPreview.scheduled_for)}
                </p>
                <details className="manual-publish-preview">
                  <summary>Zobraziť presný Discord náhľad</summary>
                  <DiscordPreview draft={publishPreview.draft} />
                </details>
                <div>
                  <Button variant="outline" onClick={() => setPublishPreview(null)}>
                    Zrušiť
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={publishing}
                    onClick={() => void publish()}
                  >
                    Zverejniť teraz
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="outline" disabled={publishing} onClick={() => void preparePublish()}>
                Pripraviť bezpečný náhľad
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function CalendarsPanel({
  items,
  onChanged,
  setNotice,
}: {
  items: CalendarSource[]
  onChanged: (items: CalendarSource[]) => void
  setNotice: (notice: Notice) => void
}) {
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [calendarId, setCalendarId] = useState('')
  async function add() {
    setCreating(true)
    try {
      const result = await createCalendarSource({
        display_name: name,
        external_calendar_id: calendarId,
        priority: (items.length + 1) * 10,
        active: true,
      })
      onChanged([...items, result])
      setName('')
      setCalendarId('')
      setNotice({ kind: 'success', text: 'Google kalendár bol pridaný.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setCreating(false)
    }
  }
  return (
    <div className="settings-grid settings-grid-calendars">
      <Card>
        <CardHeader>
          <CardTitle>Pripojené kalendáre</CardTitle>
          <CardDescription>
            Nižšia priorita rozhoduje skôr pri rovnakom čase udalostí.
          </CardDescription>
        </CardHeader>
        <CardContent className="calendar-list">
          {items.length === 0 && (
            <EmptyState
              icon={CalendarDays}
              title="Zatiaľ nie je pripojený kalendár"
              text="Pridajte Google Calendar ID a Carlo môže pripraviť prvý automatický prehľad."
            />
          )}
          {items.map((calendar) => (
            <CalendarRow
              key={calendar.id}
              value={calendar}
              onChanged={(changed) =>
                onChanged(items.map((item) => (item.id === changed.id ? changed : item)))
              }
              setNotice={setNotice}
            />
          ))}
        </CardContent>
      </Card>
      <Card className="settings-side-card">
        <CardHeader>
          <CardTitle>Pridať Google kalendár</CardTitle>
          <CardDescription>
            Kalendár musí byť zdieľaný so servisným účtom Carla aspoň na čítanie.
          </CardDescription>
        </CardHeader>
        <CardContent className="settings-fields">
          <Field label="Názov v administrácii">
            <Input
              placeholder="Napríklad Program Domčeka"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <Field label="Google Calendar ID">
            <Input
              placeholder="…@group.calendar.google.com"
              value={calendarId}
              onChange={(event) => setCalendarId(event.target.value)}
            />
          </Field>
          <Button
            disabled={creating || !name.trim() || !calendarId.trim()}
            onClick={() => void add()}
          >
            {creating ? <LoaderCircle className="spin" /> : <Plus />} Pridať kalendár
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

function CalendarRow({
  value,
  onChanged,
  setNotice,
}: {
  value: CalendarSource
  onChanged: (value: CalendarSource) => void
  setNotice: (notice: Notice) => void
}) {
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  async function toggle() {
    setBusy(true)
    try {
      onChanged(await updateCalendarSource({ ...value, active: !value.active }))
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  async function sync() {
    setBusy(true)
    try {
      const result = await syncCalendarSource(value.id)
      setNotice({
        kind: 'success',
        text: `Synchronizácia skončila: ${result.received} prijatých udalostí.`,
      })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  async function save() {
    setBusy(true)
    try {
      const changed = await updateCalendarSource(draft)
      onChanged(changed)
      setDraft(changed)
      setEditing(false)
      setNotice({ kind: 'success', text: 'Kalendár bol upravený.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  return (
    <article className={`calendar-row ${editing ? 'calendar-row-editing' : ''}`}>
      <div className="calendar-icon">
        <CalendarDays />
      </div>
      <div className="calendar-copy">
        <div>
          <strong>{value.display_name}</strong>
          <SyncBadge status={value.sync_status} />
        </div>
        <span>{value.external_calendar_id}</span>
        <small>
          {value.last_sync_success_at
            ? `Naposledy úspešne ${dateTime(value.last_sync_success_at)}`
            : 'Ešte nebola úspešne synchronizovaná'}
        </small>
      </div>
      <div className="calendar-actions">
        <Switch
          checked={value.active}
          onCheckedChange={() => void toggle()}
          aria-label={`Aktivovať ${value.display_name}`}
        />
        <Button
          variant="outline"
          size="sm"
          disabled={busy || !value.active}
          onClick={() => void sync()}
        >
          <RefreshCw className={busy ? 'spin' : ''} />
          Synchronizovať
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setEditing(!editing)}>
          {editing ? 'Zavrieť' : 'Upraviť'}
        </Button>
      </div>
      {editing && (
        <div className="calendar-edit-form">
          <Field label="Názov">
            <Input
              value={draft.display_name}
              onChange={(event) => setDraft({ ...draft, display_name: event.target.value })}
            />
          </Field>
          <Field label="Google Calendar ID">
            <Input
              value={draft.external_calendar_id}
              onChange={(event) => setDraft({ ...draft, external_calendar_id: event.target.value })}
            />
          </Field>
          <Field label="Priorita">
            <Input
              type="number"
              min={0}
              max={10000}
              value={draft.priority}
              onChange={(event) => setDraft({ ...draft, priority: Number(event.target.value) })}
            />
          </Field>
          <Button disabled={busy} onClick={() => void save()}>
            <Check /> Uložiť kalendár
          </Button>
        </div>
      )}
    </article>
  )
}

export function ChannelsPanel({
  directory,
  archives,
  isAdmin,
  configuration,
  onConfigurationSaved,
  onArchivesChanged,
  setNotice,
}: {
  directory: DiscordDirectory
  archives: ArchiveRequest[]
  isAdmin: boolean
  configuration?: PublicationSettings | null
  onConfigurationSaved?: (value: PublicationSettings) => Promise<void>
  onArchivesChanged: (value: ArchiveRequest[]) => void
  setNotice: (notice: Notice) => void
}) {
  const [name, setName] = useState('')
  const [emoji, setEmoji] = useState('🏠')
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [memberIds, setMemberIds] = useState<string[]>([])
  const [roleIds, setRoleIds] = useState<string[]>([])
  const [categoryId, setCategoryId] = useState('')
  const [archiveChannel, setArchiveChannel] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [projectsCategoryId, setProjectsCategoryId] = useState(
    configuration?.projects_category_id ?? '',
  )
  const [archiveCategoryId, setArchiveCategoryId] = useState(
    configuration?.archive_category_id ?? '',
  )
  const createInFlight = useRef(false)
  const createIdempotencyKey = useRef(crypto.randomUUID())
  const [pendingDecision, setPendingDecision] = useState<{ id: string; approve: boolean } | null>(
    null,
  )
  const recoverableArchives = archives.filter((item) =>
    ['archiving', 'failed'].includes(item.state),
  )
  const availableCategories = directory.categories.filter(
    (category) => category.can_create_project_channel,
  )
  const defaultCategory = availableCategories.find(
    (category) => category.is_default_project_category,
  )
  const peopleWithAccess = memberIds.length + 1
  const archiveCategoryIds = new Set(
    directory.categories.filter((category) => category.is_archive_category).map((item) => item.id),
  )
  const archivableChannels = directory.channels.filter(
    (channel) => channel.category_id === null || !archiveCategoryIds.has(channel.category_id),
  )
  async function create() {
    if (createInFlight.current) return
    createInFlight.current = true
    setBusy(true)
    try {
      const result = await createDiscordChannel({
        name,
        emoji,
        owner_id: ownerId,
        member_ids: memberIds,
        role_ids: roleIds,
        category_id: categoryId || null,
        idempotency_key: createIdempotencyKey.current,
      })
      setNotice({ kind: 'success', text: `Kanál #${result.name} bol vytvorený.` })
      setName('')
      setOwnerId(null)
      setMemberIds([])
      setRoleIds([])
      createIdempotencyKey.current = crypto.randomUUID()
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      createInFlight.current = false
      setBusy(false)
    }
  }
  async function requestArchive() {
    const channel = directory.channels.find((item) => item.id === archiveChannel)
    if (!channel) return
    setBusy(true)
    try {
      const result = await createArchiveRequest({
        channel_id: channel.id,
        reason,
      })
      onArchivesChanged([...archives.filter((item) => item.id !== result.id), result])
      setReason('')
      setNotice({ kind: 'success', text: 'Žiadosť čaká na rozhodnutie Admina.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  async function decide(id: string, approve: boolean) {
    try {
      await decideArchiveRequest(id, approve)
      onArchivesChanged(archives.filter((item) => item.id !== id))
      setNotice({
        kind: 'success',
        text: approve ? 'Kanál bol archivovaný.' : 'Žiadosť bola zamietnutá.',
      })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    }
  }
  async function recoverArchives() {
    setBusy(true)
    try {
      const recovered = await recoverArchiveRequests()
      const recoveredIds = new Set(recovered.map((item) => item.id))
      onArchivesChanged(archives.filter((item) => !recoveredIds.has(item.id)))
      setNotice({
        kind: 'success',
        text: recovered.length
          ? `Carlo obnovil ${recovered.length} archivačných operácií.`
          : 'Žiadnu archiváciu sa zatiaľ nepodarilo obnoviť.',
      })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  async function saveCategoryConfiguration() {
    if (!configuration || !onConfigurationSaved) return
    setBusy(true)
    try {
      const saved = await updatePublicationSettings({
        ...configuration,
        projects_category_id: projectsCategoryId || null,
        archive_category_id: archiveCategoryId || null,
      })
      await onConfigurationSaved(saved)
      setNotice({ kind: 'success', text: 'Kategórie pre projekty a archív sú uložené.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="channel-workspace">
      <section className="channel-creation-card">
        <div className="channel-section-heading">
          <span className="section-icon">
            <Plus />
          </span>
          <div>
            <h2>Nový projektový kanál</h2>
            <p>Súkromný textový priestor s presne určeným prístupom.</p>
          </div>
        </div>
        {isAdmin && configuration && (
          <div className="channel-placement-settings">
            <div>
              <strong>Pravidlá umiestnenia</strong>
              <span>Predvolená cieľová kategória a archív patria k správe kanálov.</span>
            </div>
            <Field label="Projektová kategória">
              <select
                value={projectsCategoryId}
                onChange={(event) => setProjectsCategoryId(event.target.value)}
              >
                <option value="">Nie je nastavená</option>
                {directory.categories
                  .filter(
                    (category) =>
                      category.voice_channel_count === 0 && category.id !== archiveCategoryId,
                  )
                  .map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Archívna kategória">
              <select
                value={archiveCategoryId}
                onChange={(event) => setArchiveCategoryId(event.target.value)}
              >
                <option value="">Nie je nastavená</option>
                {directory.categories
                  .filter(
                    (category) =>
                      category.voice_channel_count === 0 && category.id !== projectsCategoryId,
                  )
                  .map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
              </select>
            </Field>
            <Button
              variant="outline"
              disabled={busy || !projectsCategoryId || !archiveCategoryId}
              onClick={() => void saveCategoryConfiguration()}
            >
              <Check /> Uložiť kategórie
            </Button>
          </div>
        )}
        <div className="channel-basics-grid">
          <Field label="Kategória">
            <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">
                {defaultCategory ? `Predvolená · ${defaultCategory.name}` : 'Vyberte kategóriu'}
              </option>
              {availableCategories
                .filter((category) => category.id !== defaultCategory?.id)
                .map((category) => (
                  <option value={category.id} key={category.id}>
                    {category.name} · {category.text_channel_count} textových kanálov
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Názov kanála">
            <Input
              placeholder="nazov-projektu"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <Field label="Emoji v názve">
            <Input
              value={emoji}
              maxLength={16}
              onChange={(event) => setEmoji(event.target.value)}
            />
          </Field>
        </div>
        {availableCategories.length === 0 && (
          <div className="category-note">
            <MessageSquareMore />
            <span>
              Nenašla sa žiadna vhodná textová kategória. Archív a kategórie s hlasovými kanálmi
              Carlo zámerne neponúka.
            </span>
          </div>
        )}
        <div className="access-builder">
          <MemberPicker
            label="Zodpovedná osoba"
            description="Ak nikoho nevyberiete, zodpovednou osobou budete vy."
            value={ownerId ? [ownerId] : []}
            multiple={false}
            emptyLabel="Vy – používateľ, ktorý kanál vytvára"
            onChange={(ids) => {
              const nextOwner = ids[0] ?? null
              setOwnerId(nextOwner)
              if (nextOwner) setMemberIds((current) => current.filter((id) => id !== nextOwner))
            }}
          />
          <MemberPicker
            label="Ďalší ľudia s prístupom"
            description="Výsledky sa zobrazujú automaticky počas písania."
            value={memberIds}
            excludedIds={ownerId ? [ownerId] : []}
            onChange={setMemberIds}
          />
          <RolePicker roles={directory.roles} value={roleIds} onChange={setRoleIds} />
        </div>
        <div className="channel-create-footer">
          <div className="permission-preview">
            <ShieldCheck />
            <div>
              <strong>Súkromný kanál</strong>
              <span>
                @everyone ho neuvidí · {peopleWithAccess} {peopleWord(peopleWithAccess)} ·{' '}
                {roleIds.length} {roleWord(roleIds.length)}
              </span>
            </div>
          </div>
          <Button
            disabled={busy || !name.trim() || !emoji.trim() || (!categoryId && !defaultCategory)}
            onClick={() => void create()}
          >
            {busy ? <LoaderCircle className="spin" /> : <Plus />} Vytvoriť kanál
          </Button>
        </div>
      </section>

      <section className="archive-workspace">
        <div className="channel-section-heading archive-heading">
          <span className="section-icon archive">
            <Archive />
          </span>
          <div>
            <h2>Archivácia kanálov</h2>
            <p>Nová žiadosť aj rozhodnutia sú spolu v jednom plnohodnotnom pracovnom priestore.</p>
          </div>
          {isAdmin && recoverableArchives.length > 0 && (
            <Button variant="outline" disabled={busy} onClick={() => void recoverArchives()}>
              <RefreshCw /> Obnoviť rozpracované ({recoverableArchives.length})
            </Button>
          )}
        </div>
        <div className="archive-layout">
          <div className="archive-request-form">
            <h3>Nová žiadosť</h3>
            <ChannelSelect
              label="Kanál"
              value={archiveChannel || null}
              channels={archivableChannels}
              onChange={(id) => setArchiveChannel(id ?? '')}
            />
            <Field label="Dôvod">
              <Textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Prečo sa projekt uzatvára?"
              />
            </Field>
            <Button
              variant="outline"
              disabled={busy || !archiveChannel || reason.trim().length < 3}
              onClick={() => void requestArchive()}
            >
              <Archive /> Odoslať žiadosť
            </Button>
          </div>
          <div className="archive-queue">
            <div className="archive-queue-heading">
              <h3>Otvorené žiadosti</h3>
              <Badge variant="secondary">{archives.length}</Badge>
            </div>
            <div className="archive-list">
              {archives.length === 0 && (
                <EmptyState
                  icon={Archive}
                  title="Nič nečaká na rozhodnutie"
                  text="Nová žiadosť sa zobrazí tu aj v kanáli moderátorov."
                />
              )}
              {archives.map((item) => (
                <article className={`archive-row state-${item.state}`} key={item.id}>
                  <span className="archive-state-mark">
                    <Archive />
                  </span>
                  <div>
                    <strong>#{item.original_channel_name}</strong>
                    <span>{item.reason}</span>
                    <small>
                      {item.state === 'pending'
                        ? `Čaká na rozhodnutie · platí do ${dateTime(item.expires_at)}`
                        : item.state === 'archiving'
                          ? 'Schválené · čaká na bezpečné dokončenie'
                          : 'Predchádzajúci pokus zlyhal · možno ho obnoviť'}
                    </small>
                  </div>
                  {isAdmin && item.state === 'pending' && (
                    <div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPendingDecision({ id: item.id, approve: false })}
                      >
                        Zamietnuť
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setPendingDecision({ id: item.id, approve: true })}
                      >
                        Schváliť
                      </Button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>
      <AlertDialog
        open={pendingDecision !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDecision(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingDecision?.approve ? 'Archivovať tento kanál?' : 'Zamietnuť žiadosť?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDecision?.approve
                ? 'Kanál sa presunie do archívu a všetky individuálne oprávnenia nahradia oprávnenia archívnej kategórie.'
                : 'Žiadosť sa uzavrie bez zmeny kanála.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Zrušiť</AlertDialogCancel>
            <AlertDialogAction
              variant={pendingDecision?.approve ? 'destructive' : 'default'}
              onClick={() => {
                if (pendingDecision) void decide(pendingDecision.id, pendingDecision.approve)
                setPendingDecision(null)
              }}
            >
              Potvrdiť
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export function RolesPanel({
  publication,
  setNotice,
}: {
  publication: PublicationSettings
  setNotice: (notice: Notice) => void
}) {
  const [query, setQuery] = useState('')
  const [members, setMembers] = useState<DiscordMemberOption[]>([])
  const [searching, setSearching] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [pending, setPending] = useState<{
    member: DiscordMemberOption
    role: 'team_mod' | 'admin'
    enabled: boolean
  } | null>(null)
  useEffect(() => {
    const normalized = query.trim()
    if (!normalized) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setSearching(true)
      void searchDiscordMembers(normalized, controller.signal)
        .then(setMembers)
        .catch((error: unknown) => {
          if (!controller.signal.aborted) setNotice({ kind: 'error', text: message(error) })
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearching(false)
        })
    }, 240)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, setNotice])
  async function change(member: DiscordMemberOption, role: 'team_mod' | 'admin', enabled: boolean) {
    setBusy(`${member.id}:${role}`)
    try {
      const changed = await setDiscordRole(member.id, role, enabled)
      setMembers(members.map((item) => (item.id === changed.id ? changed : item)))
      setNotice({
        kind: 'success',
        text: `${role === 'admin' ? 'Admin' : 'Team Mod'} oprávnenie bolo ${enabled ? 'udelené' : 'odobrané'}.`,
      })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setBusy(null)
    }
  }
  return (
    <>
      <Card className="roles-card">
        <CardHeader>
          <CardTitle>Oprávnenia členov</CardTitle>
          <CardDescription>
            Carlo dovolí meniť iba Team Mod a Admin. Posledného Admina nemožno odobrať.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="member-search picker-search-shell">
            <Search aria-hidden="true" />
            <Input
              value={query}
              placeholder="Začnite písať meno alebo prezývku…"
              onChange={(event) => {
                const next = event.target.value
                setQuery(next)
                if (!next.trim()) {
                  setMembers([])
                  setSearching(false)
                }
              }}
            />
            {searching && <LoaderCircle className="spin" aria-label="Vyhľadávam" />}
            {query && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Vymazať vyhľadávanie"
                onClick={() => {
                  setQuery('')
                  setMembers([])
                  setSearching(false)
                }}
              >
                <X />
              </Button>
            )}
          </div>
          <div className="member-results">
            {members.map((member) => (
              <MemberRoleRow
                key={member.id}
                member={member}
                publication={publication}
                busy={busy}
                onChange={(member, role, enabled) => setPending({ member, role, enabled })}
              />
            ))}
            {!query.trim() && members.length === 0 && (
              <EmptyState
                icon={Users}
                title="Začnite písať meno"
                text="Výsledky s avatarom a aktuálnymi oprávneniami sa zobrazia automaticky."
              />
            )}
            {query.trim() && !searching && members.length === 0 && (
              <EmptyState
                icon={Users}
                title="Nikto sa nenašiel"
                text="Skúste inú časť mena alebo Discord prezývky."
              />
            )}
          </div>
          <p className="role-footnote">
            <ShieldCheck /> Carlo pred každou zmenou znova overí vlastné Manage Roles oprávnenie a
            poradie rolí.
          </p>
        </CardContent>
      </Card>
      <AlertDialog
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open) setPending(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Potvrdiť zmenu oprávnenia?</AlertDialogTitle>
            <AlertDialogDescription>
              {pending
                ? `${pending.enabled ? 'Udelíte' : 'Odoberiete'} rolu ${pending.role === 'admin' ? 'Admin' : 'Team Mod'} členovi ${pending.member.display_name}.`
                : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Zrušiť</AlertDialogCancel>
            <AlertDialogAction
              variant={pending && !pending.enabled ? 'destructive' : 'default'}
              onClick={() => {
                if (pending) void change(pending.member, pending.role, pending.enabled)
                setPending(null)
              }}
            >
              Potvrdiť zmenu
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function MemberRoleRow({
  member,
  publication,
  busy,
  onChange,
}: {
  member: DiscordMemberOption
  publication: PublicationSettings
  busy: string | null
  onChange: (member: DiscordMemberOption, role: 'team_mod' | 'admin', enabled: boolean) => void
}) {
  const team =
    publication.team_mod_role_id !== null && member.role_ids.includes(publication.team_mod_role_id)
  const admin =
    publication.admin_role_id !== null && member.role_ids.includes(publication.admin_role_id)
  return (
    <article className="member-row">
      <div className="member-identity">
        {member.avatar_url ? (
          <img src={member.avatar_url} alt="" />
        ) : (
          <span>{member.display_name[0]}</span>
        )}
        <div>
          <strong>{member.display_name}</strong>
          <small>@{member.username}</small>
        </div>
      </div>
      <div className="role-switches">
        <ToggleCompact
          label="Team Mod"
          checked={team}
          disabled={busy === `${member.id}:team_mod`}
          onChecked={(checked) => onChange(member, 'team_mod', checked)}
        />
        <ToggleCompact
          label="Admin"
          checked={admin}
          disabled={busy === `${member.id}:admin`}
          onChecked={(checked) => onChange(member, 'admin', checked)}
        />
      </div>
    </article>
  )
}

export function ReactionsPanel({
  value,
  directory,
  onSaved,
  setNotice,
}: {
  value: ReactionSettings
  directory: DiscordDirectory
  onSaved: (value: ReactionSettings) => void
  setNotice: (notice: Notice) => void
}) {
  const [draft, setDraft] = useState(value)
  const [testChannel, setTestChannel] = useState(directory.channels[0]?.id ?? '')
  const [saving, setSaving] = useState(false)
  async function save() {
    setSaving(true)
    try {
      const result = await updateReactionSettings(draft)
      onSaved(result)
      setDraft(result)
      setNotice({ kind: 'success', text: 'Reakcie sú uložené a bot ich použije bez reštartu.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setSaving(false)
    }
  }
  async function test(kind: 'seen' | 'auto' | 'mention') {
    try {
      await testDiscordReaction(kind, testChannel)
      setNotice({ kind: 'success', text: 'Carlo poslal skúšobnú správu a pridal reakciu.' })
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    }
  }
  return (
    <div className="settings-grid settings-grid-main">
      <div className="settings-stack">
        <ReactionCard
          title="Seen reakcia"
          description="Pridá sa na poslednú správu úspešného prehľadu."
          enabled={draft.seen_enabled}
          unicode={draft.seen_emoji_unicode}
          emojiId={draft.seen_emoji_id}
          emojis={directory.emojis}
          onChange={(change) =>
            setDraft({
              ...draft,
              seen_enabled: change.enabled,
              seen_emoji_unicode: change.unicode,
              seen_emoji_id: change.emojiId,
            })
          }
        />
        <ReactionCard
          title="Reakcia pri označení Carla"
          description="Carlo zareaguje, keď ho niekto označí v správe."
          enabled={draft.mention_reaction_enabled}
          unicode={draft.mention_reaction_emoji_unicode}
          emojiId={draft.mention_reaction_emoji_id}
          emojis={directory.emojis}
          onChange={(change) =>
            setDraft({
              ...draft,
              mention_reaction_enabled: change.enabled,
              mention_reaction_emoji_unicode: change.unicode,
              mention_reaction_emoji_id: change.emojiId,
            })
          }
        />
        <ReactionCard
          title="Automatická reakcia v kanáloch"
          description="Každá nová správa vo vybraných kanáloch dostane reakciu."
          enabled={draft.auto_reaction_enabled}
          unicode={draft.auto_reaction_emoji_unicode}
          emojiId={draft.auto_reaction_emoji_id}
          emojis={directory.emojis}
          onChange={(change) =>
            setDraft({
              ...draft,
              auto_reaction_enabled: change.enabled,
              auto_reaction_emoji_unicode: change.unicode,
              auto_reaction_emoji_id: change.emojiId,
            })
          }
        >
          <ChannelMultiPicker
            channels={directory.channels}
            value={draft.auto_reaction_channel_ids}
            onChange={(ids) => setDraft({ ...draft, auto_reaction_channel_ids: ids })}
          />
        </ReactionCard>
      </div>
      <Card className="settings-side-card">
        <CardHeader>
          <CardTitle>Vyskúšať reakciu</CardTitle>
          <CardDescription>
            Carlo pošle jasne označenú skúšobnú správu do zvoleného kanála.
          </CardDescription>
        </CardHeader>
        <CardContent className="settings-fields">
          <ChannelSelect
            label="Testovací kanál"
            value={testChannel || null}
            channels={directory.channels}
            onChange={(id) => setTestChannel(id ?? '')}
          />
          <Button
            variant="outline"
            disabled={!testChannel || !draft.seen_enabled}
            onClick={() => void test('seen')}
          >
            Test seen
          </Button>
          <Button
            variant="outline"
            disabled={!testChannel || !draft.mention_reaction_enabled}
            onClick={() => void test('mention')}
          >
            Test označenia
          </Button>
          <Button
            variant="outline"
            disabled={!testChannel || !draft.auto_reaction_enabled}
            onClick={() => void test('auto')}
          >
            Test automatickej
          </Button>
          <Button className="settings-save" disabled={saving} onClick={() => void save()}>
            {saving ? <LoaderCircle className="spin" /> : <Check />}Uložiť reakcie
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

function ReactionCard({
  title,
  description,
  enabled,
  unicode,
  emojiId,
  emojis,
  onChange,
  children,
}: {
  title: string
  description: string
  enabled: boolean
  unicode: string | null
  emojiId: string | null
  emojis: DiscordDirectory['emojis']
  onChange: (value: { enabled: boolean; unicode: string | null; emojiId: string | null }) => void
  children?: ReactNode
}) {
  const mode = emojiId ? 'server' : 'unicode'
  return (
    <Card>
      <CardHeader className="reaction-heading">
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <Switch
          checked={enabled}
          onCheckedChange={(checked) => onChange({ enabled: checked, unicode, emojiId })}
        />
      </CardHeader>
      <CardContent className="reaction-fields">
        <Field label="Typ emoji">
          <select
            value={mode}
            onChange={(event) =>
              onChange({
                enabled,
                unicode: event.target.value === 'unicode' ? (unicode ?? '✅') : null,
                emojiId:
                  event.target.value === 'server'
                    ? (emojis.find((emoji) => emoji.available)?.id ?? null)
                    : null,
              })
            }
          >
            <option value="unicode">Bežné emoji</option>
            <option value="server">Emoji servera</option>
          </select>
        </Field>
        {mode === 'unicode' ? (
          <Field label="Emoji">
            <Input
              value={unicode ?? ''}
              maxLength={32}
              onChange={(event) =>
                onChange({ enabled, unicode: event.target.value || null, emojiId: null })
              }
            />
          </Field>
        ) : (
          <Field label="Emoji servera">
            <select
              value={emojiId ?? ''}
              onChange={(event) =>
                onChange({ enabled, unicode: null, emojiId: event.target.value || null })
              }
            >
              <option value="">Vyberte emoji</option>
              {emojiId && !emojis.some((emoji) => emoji.id === emojiId) && (
                <option value={emojiId}>Uložené emoji je na serveri nedostupné</option>
              )}
              {emojis.map((emoji) => (
                <option key={emoji.id} disabled={!emoji.available} value={emoji.id}>
                  :{emoji.name}:{emoji.available ? '' : ' (nedostupné)'}
                </option>
              ))}
            </select>
          </Field>
        )}
        {children}
      </CardContent>
    </Card>
  )
}

function ToggleRow({
  title,
  description,
  checked,
  onChecked,
}: {
  title: string
  description: string
  checked: boolean
  onChecked: (checked: boolean) => void
}) {
  return (
    <div className="toggle-row">
      <div>
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
      <Switch checked={checked} onCheckedChange={onChecked} aria-label={title} />
    </div>
  )
}
function ToggleCompact({
  label,
  checked,
  disabled,
  onChecked,
}: {
  label: string
  checked: boolean
  disabled: boolean
  onChecked: (checked: boolean) => void
}) {
  return (
    <label>
      <span>{label}</span>
      <Switch checked={checked} disabled={disabled} onCheckedChange={onChecked} />
    </label>
  )
}
function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactElement<{ id?: string }>
}) {
  const generatedId = useId()
  const controlId = children.props.id ?? generatedId
  return (
    <div className="settings-field">
      <Label htmlFor={controlId}>{label}</Label>
      {cloneElement(children, { id: controlId })}
      {hint && <small>{hint}</small>}
    </div>
  )
}
function ChannelSelect({
  label,
  value,
  channels,
  onChange,
}: {
  label: string
  value: string | null
  channels: DiscordDirectory['channels']
  onChange: (id: string | null) => void
}) {
  return (
    <Field label={label}>
      <select value={value ?? ''} onChange={(event) => onChange(event.target.value || null)}>
        <option value="">Nie je vybrané</option>
        {channels.map((channel) => (
          <option key={channel.id} value={channel.id}>
            {channel.kind === 'text' ? '#' : ''}
            {channel.name}
          </option>
        ))}
      </select>
    </Field>
  )
}
function SyncBadge({ status }: { status: CalendarSource['sync_status'] }) {
  const labels = {
    never: 'Nesynchronizovaný',
    running: 'Prebieha',
    succeeded: 'Aktuálny',
    failed: 'Chyba',
  }
  return <Badge variant={status === 'failed' ? 'destructive' : 'secondary'}>{labels[status]}</Badge>
}
function EmptyState({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof CalendarDays
  title: string
  text: string
}) {
  return (
    <div className="settings-empty">
      <Icon />
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  )
}
export function NoticeBanner({ notice }: { notice: Exclude<Notice, null> }) {
  return (
    <div className={`settings-notice ${notice.kind}`} role="status">
      {notice.kind === 'success' ? <Check /> : <MessageSquareMore />}
      {notice.text}
    </div>
  )
}
function SettingsSkeleton() {
  return (
    <section className="settings-page">
      <div className="settings-hero">
        <div>
          <p className="eyebrow">Riadiace centrum</p>
          <h1>Nastavenia Carla</h1>
        </div>
      </div>
      <div className="settings-loading">
        <LoaderCircle className="spin" /> Načítavam živé údaje z Discordu…
      </div>
    </section>
  )
}
function PageError({ notice, onRetry }: { notice: Notice; onRetry: () => void }) {
  return (
    <section className="settings-page">
      <div className="settings-error">
        <Settings2 />
        <h1>Nastavenia sa nepodarilo načítať</h1>
        <p>{notice?.text ?? 'Skúste to znova.'}</p>
        <Button onClick={onRetry}>
          Skúsiť znova <ChevronRight />
        </Button>
      </div>
    </section>
  )
}
function message(error: unknown) {
  return error instanceof ApiError ? error.message : 'Operáciu sa nepodarilo bezpečne dokončiť.'
}
function dateTime(value: string) {
  return new Intl.DateTimeFormat('sk-SK', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  )
}
function nextPublicationLabel(settings: PublicationSettings) {
  const now = new Date()
  const target = new Date(now)
  const days = (settings.publication_weekday - ((now.getDay() + 6) % 7) + 7) % 7
  target.setDate(now.getDate() + days)
  const [hours = 20, minutes = 0] = settings.publication_time.split(':').map(Number)
  target.setHours(hours, minutes, 0, 0)
  if (target <= now) target.setDate(target.getDate() + 7)
  return new Intl.DateTimeFormat('sk-SK', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(target)
}

function peopleWord(count: number) {
  return count === 1 ? 'človek' : count < 5 ? 'ľudia' : 'ľudí'
}

function roleWord(count: number) {
  return count === 1 ? 'rola' : count > 1 && count < 5 ? 'roly' : 'rolí'
}
