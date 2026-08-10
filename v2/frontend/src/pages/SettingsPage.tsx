import {
  Archive,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  Hash,
  LoaderCircle,
  MessageSquareMore,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  SmilePlus,
  Users,
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
  getArchiveRequests,
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

type Notice = { kind: 'success' | 'error'; text: string } | null

export function SettingsPage() {
  const auth = useAuth()
  const canAdmin =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_settings')
  const canChannels =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_channels')
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [archives, setArchives] = useState<ArchiveRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<Notice>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const [directoryValue, archiveValue, settingsValue] = await Promise.all([
        getDiscordDirectory(),
        canChannels ? getArchiveRequests() : Promise.resolve([]),
        canAdmin ? getAdminSettings() : Promise.resolve(null),
      ])
      setDirectory(directoryValue)
      setArchives(archiveValue)
      setSettings(settingsValue)
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    } finally {
      setLoading(false)
    }
  }, [canAdmin, canChannels])

  useEffect(() => {
    let cancelled = false
    void Promise.all([
      getDiscordDirectory(),
      canChannels ? getArchiveRequests() : Promise.resolve([]),
      canAdmin ? getAdminSettings() : Promise.resolve(null),
    ])
      .then(([directoryValue, archiveValue, settingsValue]) => {
        if (cancelled) return
        setDirectory(directoryValue)
        setArchives(archiveValue)
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
  }, [canAdmin, canChannels])

  if (loading) return <SettingsSkeleton />
  if (!directory) return <PageError notice={notice} onRetry={() => void reload()} />

  const firstTab = canAdmin ? 'publikovanie' : 'kanaly'
  return (
    <section className="settings-page">
      <header className="settings-hero">
        <div>
          <p className="eyebrow">Riadiace centrum</p>
          <h1>Nastavenia Carla</h1>
          <p>Kalendáre, publikovanie aj správa Discordu na jednom mieste.</p>
        </div>
        <Button variant="outline" onClick={() => void reload()}>
          <RefreshCw /> Obnoviť údaje
        </Button>
      </header>
      {notice && <NoticeBanner notice={notice} />}
      <Tabs defaultValue={firstTab} className="settings-workspace">
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
          {canChannels && (
            <TabsTrigger value="kanaly">
              <Hash />
              Kanály
            </TabsTrigger>
          )}
          {canAdmin && (
            <TabsTrigger value="roly">
              <Users />
              Roly
            </TabsTrigger>
          )}
          {canAdmin && (
            <TabsTrigger value="reakcie">
              <SmilePlus />
              Reakcie
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
        {canChannels && (
          <TabsContent value="kanaly">
            <ChannelsPanel
              directory={directory}
              archives={archives}
              isAdmin={canAdmin}
              onArchivesChanged={setArchives}
              setNotice={setNotice}
            />
          </TabsContent>
        )}
        {canAdmin && settings && (
          <TabsContent value="roly">
            <RolesPanel publication={settings.publication} setNotice={setNotice} />
          </TabsContent>
        )}
        {canAdmin && settings && (
          <TabsContent value="reakcie">
            <ReactionsPanel
              value={settings.reactions}
              directory={directory}
              onSaved={(value) => setSettings({ ...settings, reactions: value })}
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
          <ChannelSelect
            label="Projektová kategória"
            value={draft.projects_category_id}
            channels={directory.categories}
            onChange={(id) => setDraft({ ...draft, projects_category_id: id })}
          />
          <ChannelSelect
            label="Archívna kategória"
            value={draft.archive_category_id}
            channels={directory.categories}
            onChange={(id) => setDraft({ ...draft, archive_category_id: id })}
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

function ChannelsPanel({
  directory,
  archives,
  isAdmin,
  onArchivesChanged,
  setNotice,
}: {
  directory: DiscordDirectory
  archives: ArchiveRequest[]
  isAdmin: boolean
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
  const createInFlight = useRef(false)
  const createIdempotencyKey = useRef(crypto.randomUUID())
  const [memberQuery, setMemberQuery] = useState('')
  const [members, setMembers] = useState<DiscordMemberOption[]>([])
  const [pendingDecision, setPendingDecision] = useState<{ id: string; approve: boolean } | null>(
    null,
  )
  const recoverableArchives = archives.filter((item) =>
    ['archiving', 'failed'].includes(item.state),
  )
  async function search() {
    try {
      setMembers(await searchDiscordMembers(memberQuery))
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    }
  }
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
  return (
    <div className="settings-grid settings-grid-main">
      <div className="settings-stack">
        <Card>
          <CardHeader>
            <CardTitle>Nový projektový kanál</CardTitle>
            <CardDescription>
              Carlo vytvorí súkromný kanál vo vybranej povolenej kategórii.
            </CardDescription>
          </CardHeader>
          <CardContent className="settings-fields">
            <Field label="Kategória">
              <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                <option value="">Nastavená pracovná kategória</option>
                {directory.categories.map((category) => (
                  <option value={category.id} key={category.id}>
                    {category.name}
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
            <div className="inline-search">
              <Input
                placeholder="Vyhľadať človeka"
                value={memberQuery}
                onChange={(event) => setMemberQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    void search()
                  }
                }}
              />
              <Button variant="outline" onClick={() => void search()}>
                <Search />
                Hľadať
              </Button>
            </div>
            {members.length > 0 && (
              <div className="channel-people-picker">
                <Field label="Zodpovedná osoba">
                  <select
                    value={ownerId ?? ''}
                    onChange={(event) => setOwnerId(event.target.value || null)}
                  >
                    <option value="">Ja – používateľ, ktorý kanál vytvára</option>
                    {members.map((member) => (
                      <option key={member.id} value={member.id}>
                        {member.display_name}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="choice-cloud" aria-label="Ďalší ľudia s prístupom">
                  {members.map((member) => (
                    <button
                      type="button"
                      key={member.id}
                      className={memberIds.includes(member.id) ? 'selected' : ''}
                      onClick={() => setMemberIds(toggle(memberIds, member.id))}
                    >
                      {member.display_name}
                      {memberIds.includes(member.id) && <Check />}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <Field label="Roly s prístupom" hint="Viac rolí vyberiete s Ctrl/Cmd.">
              <select
                multiple
                value={roleIds}
                onChange={(event) =>
                  setRoleIds(
                    Array.from(event.currentTarget.selectedOptions, (option) => option.value),
                  )
                }
              >
                {directory.roles
                  .filter((role) => !role.managed && role.name !== '@everyone')
                  .map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name}
                    </option>
                  ))}
              </select>
            </Field>
            <div className="permission-preview">
              <ShieldCheck />
              <div>
                <strong>Náhľad prístupu</strong>
                <span>
                  @everyone kanál neuvidí · zodpovedná osoba a {memberIds.length} ďalších ľudí ·{' '}
                  {roleIds.length} rolí
                </span>
              </div>
            </div>
            <Button disabled={busy || !name.trim() || !emoji.trim()} onClick={() => void create()}>
              <Plus />
              Vytvoriť kanál
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Archivácie</CardTitle>
            <CardDescription>
              Rozhodnutie je jednorazové a pri schválení sa oprávnenia zosúladia s archívom.
            </CardDescription>
            {isAdmin && recoverableArchives.length > 0 && (
              <Button variant="outline" disabled={busy} onClick={() => void recoverArchives()}>
                <RefreshCw /> Obnoviť rozpracované ({recoverableArchives.length})
              </Button>
            )}
          </CardHeader>
          <CardContent className="archive-list">
            {archives.length === 0 && (
              <EmptyState
                icon={Archive}
                title="Nič nečaká na rozhodnutie"
                text="Otvorené žiadosti sa zobrazia tu aj v kanáli moderátorov."
              />
            )}
            {archives.map((item) => (
              <article className="archive-row" key={item.id}>
                <div>
                  <strong>#{item.original_channel_name}</strong>
                  <span>{item.reason}</span>
                  <small>
                    {item.state === 'pending'
                      ? `Platí do ${dateTime(item.expires_at)}`
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
          </CardContent>
        </Card>
      </div>
      <Card className="settings-side-card">
        <CardHeader>
          <CardTitle>Požiadať o archiváciu</CardTitle>
          <CardDescription>Team Mod pripraví dôvod, Admin následne rozhodne.</CardDescription>
        </CardHeader>
        <CardContent className="settings-fields">
          <ChannelSelect
            label="Kanál"
            value={archiveChannel || null}
            channels={directory.channels}
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
            <Archive />
            Odoslať žiadosť
          </Button>
        </CardContent>
      </Card>
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

function RolesPanel({
  publication,
  setNotice,
}: {
  publication: PublicationSettings
  setNotice: (notice: Notice) => void
}) {
  const [query, setQuery] = useState('')
  const [members, setMembers] = useState<DiscordMemberOption[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [pending, setPending] = useState<{
    member: DiscordMemberOption
    role: 'team_mod' | 'admin'
    enabled: boolean
  } | null>(null)
  async function search() {
    try {
      setMembers(await searchDiscordMembers(query))
    } catch (error) {
      setNotice({ kind: 'error', text: message(error) })
    }
  }
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
          <div className="member-search">
            <Input
              value={query}
              placeholder="Meno člena servera"
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  void search()
                }
              }}
            />
            <Button onClick={() => void search()} disabled={!query.trim()}>
              <Search />
              Vyhľadať
            </Button>
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
            {members.length === 0 && (
              <EmptyState
                icon={Users}
                title="Vyhľadajte člena"
                text="Zobrazíme jeho aktuálne Carlo roly priamo z Discordu."
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

function ReactionsPanel({
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
          <Field label="Kanály">
            <select
              multiple
              value={draft.auto_reaction_channel_ids}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  auto_reaction_channel_ids: Array.from(
                    event.currentTarget.selectedOptions,
                    (option) => option.value,
                  ),
                })
              }
            >
              {directory.channels.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  #{channel.name}
                </option>
              ))}
            </select>
          </Field>
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
function NoticeBanner({ notice }: { notice: Exclude<Notice, null> }) {
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
function toggle(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
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
