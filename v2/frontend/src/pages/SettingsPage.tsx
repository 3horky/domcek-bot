import {
  Archive,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  Clock3,
  FolderArchive,
  FolderTree,
  LoaderCircle,
  MessageSquareMore,
  Plus,
  RefreshCw,
  Settings2,
  ShieldCheck,
  SmilePlus,
  Sparkles,
  UsersRound,
} from 'lucide-react'
import EmojiPicker, { EmojiStyle } from 'emoji-picker-react'
import {
  cloneElement,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactElement,
} from 'react'

import {
  ApiError,
  type AdminSettings,
  type ArchiveRequest,
  type CalendarSource,
  type DiscordDirectory,
  type PublicationSettings,
  createArchiveRequest,
  createCalendarSource,
  createDiscordChannel,
  decideArchiveRequest,
  getAdminSettings,
  getDiscordDirectory,
  recoverArchiveRequests,
  syncCalendarSource,
  updateCalendarSource,
  updatePublicationSettings,
} from '../api/client'
import { useAuth } from '../auth/context'
import { MemberPicker, RolePicker } from '../components/DiscordPickers'
import { UnsavedChangesGuard } from '../components/UnsavedChangesGuard'
import { carloEmojiCategories } from '../lib/emoji'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover'
import { Switch } from '../components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Textarea } from '../components/ui/textarea'

const weekdays = ['pondelok', 'utorok', 'streda', 'štvrtok', 'piatok', 'sobota', 'nedeľa']
const defaultChannelEmojis = ['🏠', '💬', '✨', '🌿']

export type Notice = { kind: 'success' | 'error'; text: string } | null

export function SettingsPage() {
  const auth = useAuth()
  const canAdmin =
    auth.status === 'authenticated' && auth.session.capabilities.includes('manage_settings')
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [directory, setDirectory] = useState<DiscordDirectory | null>(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<Notice>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [settingsRevision, setSettingsRevision] = useState(0)
  const [activeSection, setActiveSection] = useState('publikovanie')
  const [pendingSection, setPendingSection] = useState<string | null>(null)
  const [publicationDirty, setPublicationDirty] = useState(false)
  const handlePublicationDirty = useCallback((dirty: boolean) => setPublicationDirty(dirty), [])
  const publicationDraftKey =
    auth.status === 'authenticated'
      ? `carlo:draft:publication-settings:${auth.session.guild_id}:${auth.session.user.id}:${settings?.publication.version ?? 'loading'}`
      : 'carlo:draft:publication-settings:anonymous'

  const reload = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    setLoadError(null)
    try {
      const [directoryValue, settingsValue] = await Promise.all([
        getDiscordDirectory(),
        canAdmin ? getAdminSettings() : Promise.resolve(null),
      ])
      setDirectory(directoryValue)
      setSettings(settingsValue)
      setSettingsRevision((current) => current + 1)
    } catch (error) {
      setLoadError(message(error))
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
        if (!cancelled) setLoadError(message(error))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [canAdmin])

  if (loading) return <SettingsSkeleton />
  if (!canAdmin)
    return (
      <PageError
        notice={{ kind: 'error', text: 'Nastavenia Carla môže spravovať iba Admin.' }}
        onRetry={() => void reload()}
        retryLabel="Obnoviť oprávnenia"
      />
    )
  if (!directory || !settings)
    return (
      <PageError
        notice={{ kind: 'error', text: loadError ?? 'Carlo neposlal úplné nastavenia.' }}
        onRetry={() => void reload()}
      />
    )

  return (
    <section className="settings-page">
      <header className="settings-hero">
        <div>
          <p className="eyebrow">Trvalé pravidlá</p>
          <h1>Nastavenia</h1>
          <p>Publikovanie, miesta na Discorde a zdroje z Google Kalendára.</p>
        </div>
      </header>
      {notice && <NoticeBanner notice={notice} />}
      <Tabs
        value={activeSection}
        onValueChange={(next) => {
          if (publicationDirty && activeSection === 'publikovanie' && next !== activeSection)
            setPendingSection(next)
          else setActiveSection(next)
        }}
        className="settings-workspace"
      >
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
              key={`${settings.publication.version}:${settingsRevision}`}
              value={settings.publication}
              directory={directory}
              onSaved={(value) => {
                setSettings({ ...settings, publication: value })
                setNotice({ kind: 'success', text: 'Publikačné nastavenia sú uložené.' })
              }}
              onReload={() => void reload()}
              onDirtyChange={handlePublicationDirty}
              draftStorageKey={publicationDraftKey}
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
      <AlertDialog
        open={pendingSection !== null}
        onOpenChange={(open) => {
          if (!open) setPendingSection(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Zahodiť neuložené zmeny?</AlertDialogTitle>
            <AlertDialogDescription>
              V nastaveniach publikovania máte zmeny, ktoré ešte nie sú uložené. Pri prechode na
              kalendáre sa zahodia.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Zostať a dokončiť</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                window.sessionStorage.removeItem(publicationDraftKey)
                setSettingsRevision((current) => current + 1)
                setPublicationDirty(false)
                setActiveSection(pendingSection ?? 'publikovanie')
                setPendingSection(null)
              }}
            >
              Zahodiť zmeny
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}

function PublicationPanel({
  value,
  directory,
  onSaved,
  onReload,
  onDirtyChange,
  draftStorageKey,
}: {
  value: PublicationSettings
  directory: DiscordDirectory
  onSaved: (value: PublicationSettings) => void
  onReload: () => void
  onDirtyChange: (dirty: boolean) => void
  draftStorageKey: string
}) {
  const [draft, setDraft] = useState(() => restoredPublicationDraft(draftStorageKey, value))
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<{ text: string; conflict: boolean } | null>(null)
  const [confirmStaleCache, setConfirmStaleCache] = useState(false)
  const saveInFlight = useRef(false)
  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(value), [draft, value])
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])
  useEffect(() => {
    if (dirty) window.sessionStorage.setItem(draftStorageKey, JSON.stringify(draft))
    else window.sessionStorage.removeItem(draftStorageKey)
  }, [dirty, draft, draftStorageKey])
  const nextLabel = useMemo(() => nextPublicationLabel(draft), [draft])
  async function save() {
    if (saveInFlight.current || !dirty) return
    saveInFlight.current = true
    setSaving(true)
    setSaveError(null)
    try {
      const saved = await updatePublicationSettings(draft)
      window.sessionStorage.removeItem(draftStorageKey)
      onSaved(saved)
    } catch (error) {
      setSaveError({
        text:
          error instanceof ApiError && error.status === 409
            ? 'Nastavenia medzitým zmenil niekto iný. Vaše hodnoty zostali zachované; načítajte aktuálnu verziu a zmenu urobte znova.'
            : `Nastavenia sa nepodarilo uložiť. Vaše zmeny zostali zachované. ${message(error)}`,
        conflict: error instanceof ApiError && error.status === 409,
      })
    } finally {
      saveInFlight.current = false
      setSaving(false)
    }
  }
  return (
    <div className="settings-publication-workspace">
      <UnsavedChangesGuard active={dirty} />
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
                <div className="readonly-setting">
                  <strong>Slovensko</strong>
                  <span>Europe/Bratislava · automaticky rešpektuje letný čas</span>
                </div>
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
                onChecked={(checked) =>
                  setDraft({ ...draft, publish_google_descriptions: checked })
                }
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
                title="Použiť posledné dostupné dáta"
                description="Ak sa kalendár pred termínom neobnoví, Carlo smie použiť iba dáta, ktoré sú ešte bezpečne čerstvé. Predvolene publikovanie zastaví."
                checked={draft.allow_stale_calendar_cache}
                onChecked={(checked) => {
                  if (checked) setConfirmStaleCache(true)
                  else setDraft({ ...draft, allow_stale_calendar_cache: false })
                }}
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
                Kategórie správ, ktoré Carlo pošle do kanála moderátorov. Každá má odlišné
                označenie.
              </CardDescription>
            </CardHeader>
            <CardContent className="toggle-stack">
              <ToggleRow
                title="Google kalendáre"
                description="Zlyhané obnovenie a nejednoznačné zmeny opakovaných udalostí."
                checked={draft.alert_calendar_sync_enabled}
                onChecked={(checked) =>
                  setDraft({ ...draft, alert_calendar_sync_enabled: checked })
                }
              />
              <ToggleRow
                title="Publikovanie"
                description="Zastavenie, neúplný výstup, opakovaný pokus a potrebný zásah Admina."
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
            <div className="settings-placement-block">
              <div>
                <strong>Pravidlá umiestnenia</strong>
                <span>Kam Carlo pridáva nové projektové kanály a kam presúva tie ukončené.</span>
              </div>
              <ChannelSelect
                label="Nové projektové kanály"
                value={draft.projects_category_id}
                channels={directory.categories.filter(
                  (category) =>
                    category.voice_channel_count === 0 && category.id !== draft.archive_category_id,
                )}
                onChange={(id) => setDraft({ ...draft, projects_category_id: id })}
              />
              <ChannelSelect
                label="Archivované kanály"
                value={draft.archive_category_id}
                channels={directory.categories.filter(
                  (category) =>
                    category.voice_channel_count === 0 &&
                    category.id !== draft.projects_category_id,
                )}
                onChange={(id) => setDraft({ ...draft, archive_category_id: id })}
              />
            </div>
          </CardContent>
        </Card>
      </div>
      {dirty && (
        <div className="settings-save-bar" role="region" aria-label="Neuložené nastavenia">
          <div>
            <strong>Máte neuložené zmeny</strong>
            <span>Na serveri sa nič nezmení, kým ich neuložíte.</span>
          </div>
          <div>
            <Button
              variant="ghost"
              disabled={saving}
              onClick={() => {
                setDraft(value)
                setSaveError(null)
                window.sessionStorage.removeItem(draftStorageKey)
              }}
            >
              Zahodiť zmeny
            </Button>
            <Button disabled={saving} onClick={() => void save()}>
              {saving ? <LoaderCircle className="spin" /> : <Check />} Uložiť zmeny
            </Button>
          </div>
        </div>
      )}
      {saveError && (
        <div className="settings-save-error" role="alert">
          <MessageSquareMore aria-hidden="true" />
          <span>{saveError.text}</span>
          {saveError.conflict && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                window.sessionStorage.removeItem(draftStorageKey)
                onReload()
              }}
            >
              Načítať aktuálne hodnoty
            </Button>
          )}
        </div>
      )}
      <AlertDialog open={confirmStaleCache} onOpenChange={setConfirmStaleCache}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Povoliť publikovanie zo starších dát?</AlertDialogTitle>
            <AlertDialogDescription>
              Ak sa Google kalendáre tesne pred termínom neobnovia, Carlo môže použiť posledné ešte
              bezpečne čerstvé dáta. Oznam tak nemusí obsahovať najnovšiu zmenu z kalendára.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Nepovoliť</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                setDraft({ ...draft, allow_stale_calendar_cache: true })
                setConfirmStaleCache(false)
              }}
            >
              Povoliť staršie dáta
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
  const [addOpen, setAddOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [calendarId, setCalendarId] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const addInFlight = useRef(false)
  const addButtonRef = useRef<HTMLButtonElement>(null)
  async function add() {
    if (addInFlight.current) return
    addInFlight.current = true
    setCreating(true)
    setAddError(null)
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
      setAddOpen(false)
      setNotice({ kind: 'success', text: `Google kalendár ${result.display_name} bol pridaný.` })
    } catch (error) {
      setAddError(`Kalendár sa nepodarilo pridať. Nič sa nezmenilo. ${message(error)}`)
    } finally {
      addInFlight.current = false
      setCreating(false)
    }
  }
  return (
    <div className="calendar-workspace">
      <Card className="calendar-overview-card">
        <CardHeader>
          <div className="calendar-card-heading">
            <div>
              <CardTitle>Pripojené kalendáre</CardTitle>
              <CardDescription>
                Carlo môže fungovať aj bez kalendára. Aktívne zdroje pravidelne načítava iba na
                čítanie.
              </CardDescription>
            </div>
            <Dialog open={addOpen} onOpenChange={setAddOpen}>
              <DialogTrigger render={<Button ref={addButtonRef} />}>
                <Plus /> Pridať kalendár
              </DialogTrigger>
              <DialogContent className="calendar-dialog" finalFocus={() => addButtonRef.current}>
                <DialogHeader>
                  <DialogTitle>Pridať Google kalendár</DialogTitle>
                  <DialogDescription>
                    Kalendár musí byť zdieľaný so servisným účtom Carla aspoň na čítanie.
                  </DialogDescription>
                </DialogHeader>
                <div className="calendar-dialog-fields">
                  <Field label="Názov v administrácii">
                    <Input
                      autoFocus
                      placeholder="Napríklad Program Domčeka"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                    />
                  </Field>
                  <Field
                    label="Google Calendar ID"
                    hint="Nájdete ho v Google Kalendári v časti Nastavenia a integrácia kalendára."
                  >
                    <Input
                      placeholder="…@group.calendar.google.com"
                      value={calendarId}
                      onChange={(event) => setCalendarId(event.target.value)}
                    />
                  </Field>
                  {addError && (
                    <div className="calendar-local-error" role="alert">
                      <MessageSquareMore aria-hidden="true" /> {addError}
                    </div>
                  )}
                </div>
                <DialogFooter>
                  <Button variant="outline" disabled={creating} onClick={() => setAddOpen(false)}>
                    Zrušiť
                  </Button>
                  <Button
                    disabled={creating || !name.trim() || !calendarId.trim()}
                    onClick={() => void add()}
                  >
                    {creating ? <LoaderCircle className="spin" /> : <Plus />} Pridať kalendár
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
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
  const [localError, setLocalError] = useState<string | null>(null)
  const operationInFlight = useRef(false)
  function startOperation() {
    if (operationInFlight.current) return false
    operationInFlight.current = true
    setBusy(true)
    setLocalError(null)
    return true
  }
  function finishOperation() {
    operationInFlight.current = false
    setBusy(false)
  }
  async function toggle() {
    if (!startOperation()) return
    try {
      const changed = await updateCalendarSource({ ...value, active: !value.active })
      onChanged(changed)
      setDraft(changed)
      setNotice({
        kind: 'success',
        text: `${changed.display_name} je teraz ${changed.active ? 'zapnutý' : 'vypnutý'}.`,
      })
    } catch (error) {
      setLocalError(
        `${value.display_name} sa nepodarilo ${value.active ? 'vypnúť' : 'zapnúť'}. Stav sa nezmenil. ${message(error)}`,
      )
    } finally {
      finishOperation()
    }
  }
  async function sync() {
    if (!startOperation()) return
    try {
      const result = await syncCalendarSource(value.id)
      setNotice({
        kind: 'success',
        text: `${value.display_name} sa obnovil. Carlo prijal ${result.received} udalostí, vytvoril ${result.created} a aktualizoval ${result.updated}.`,
      })
    } catch (error) {
      setLocalError(
        `${value.display_name} sa nepodarilo obnoviť. Carlo ponechal doterajšie dáta. ${message(error)}`,
      )
    } finally {
      finishOperation()
    }
  }
  async function save() {
    if (!startOperation()) return
    try {
      const changed = await updateCalendarSource(draft)
      onChanged(changed)
      setDraft(changed)
      setEditing(false)
      setNotice({ kind: 'success', text: `Kalendár ${changed.display_name} bol upravený.` })
    } catch (error) {
      setLocalError(
        `${value.display_name} sa nepodarilo upraviť. Zadané hodnoty zostali zachované. ${message(error)}`,
      )
    } finally {
      finishOperation()
    }
  }
  return (
    <article className="calendar-row">
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
        {value.last_sync_error && value.sync_status === 'failed' && (
          <small className="calendar-sync-error">
            Posledné obnovenie zlyhalo: {calendarErrorText(value.last_sync_error)}
          </small>
        )}
      </div>
      <div className="calendar-actions">
        <Switch
          checked={value.active}
          disabled={busy}
          onCheckedChange={() => void toggle()}
          aria-label={`${value.active ? 'Vypnúť' : 'Zapnúť'} kalendár ${value.display_name}`}
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
        <Dialog open={editing} onOpenChange={setEditing}>
          <DialogTrigger render={<Button variant="ghost" size="sm" />}>Upraviť</DialogTrigger>
          <DialogContent className="calendar-dialog">
            <DialogHeader>
              <DialogTitle>Upraviť kalendár {value.display_name}</DialogTitle>
              <DialogDescription>
                Zmena názvu nemení Google kalendár. Po zmene ID Carlo pri ďalšom obnovení načíta
                nový zdroj.
              </DialogDescription>
            </DialogHeader>
            <div className="calendar-dialog-fields">
              <Field label="Názov v administrácii">
                <Input
                  value={draft.display_name}
                  onChange={(event) => setDraft({ ...draft, display_name: event.target.value })}
                />
              </Field>
              <Field label="Google Calendar ID">
                <Input
                  value={draft.external_calendar_id}
                  onChange={(event) =>
                    setDraft({ ...draft, external_calendar_id: event.target.value })
                  }
                />
              </Field>
              {localError && (
                <div className="calendar-local-error" role="alert">
                  <MessageSquareMore aria-hidden="true" /> {localError}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" disabled={busy} onClick={() => setEditing(false)}>
                Zrušiť
              </Button>
              <Button
                disabled={busy || !draft.display_name.trim() || !draft.external_calendar_id.trim()}
                onClick={() => void save()}
              >
                {busy ? <LoaderCircle className="spin" /> : <Check />} Uložiť kalendár
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {localError && !editing && (
        <p className="calendar-row-error" role="alert">
          {localError}
        </p>
      )}
    </article>
  )
}

export function ChannelsPanel({
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
  const [createOpen, setCreateOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [name, setName] = useState('')
  const [emoji, setEmoji] = useState('🏠')
  const [emojiIsAutomatic, setEmojiIsAutomatic] = useState(true)
  const [leaderIds, setLeaderIds] = useState<string[]>([])
  const [memberIds, setMemberIds] = useState<string[]>([])
  const [roleIds, setRoleIds] = useState<string[]>([])
  const [categoryId, setCategoryId] = useState('')
  const [archiveChannel, setArchiveChannel] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const createButtonRef = useRef<HTMLButtonElement>(null)
  const archiveButtonRef = useRef<HTMLButtonElement>(null)
  const nameComposition = useRef(false)
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
  const selectedCategory = availableCategories.find((category) => category.id === categoryId)
  const suggestedEmojis = useMemo(() => suggestChannelEmojis(name), [name])
  const effectiveEmoji = emojiIsAutomatic ? (suggestedEmojis[0] ?? '🏠') : emoji
  const finalChannelName = normalizeChannelName(name, true)
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
        name: finalChannelName,
        emoji: effectiveEmoji,
        owner_id: leaderIds[0] ?? null,
        member_ids: [...new Set([...leaderIds.slice(1), ...memberIds])],
        role_ids: roleIds,
        category_id: categoryId || null,
        idempotency_key: createIdempotencyKey.current,
      })
      setNotice({ kind: 'success', text: `Kanál #${result.name} bol vytvorený.` })
      setName('')
      setLeaderIds([])
      setMemberIds([])
      setRoleIds([])
      setCategoryId('')
      setEmoji('🏠')
      setEmojiIsAutomatic(true)
      setCreateOpen(false)
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
      setArchiveChannel('')
      setArchiveOpen(false)
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
    <div className="channel-home">
      <section className="channel-action-grid" aria-label="Čo chcete urobiť?">
        <button
          ref={createButtonRef}
          type="button"
          className="channel-action-card primary"
          onClick={() => setCreateOpen(true)}
        >
          <span className="channel-action-icon">
            <Sparkles />
          </span>
          <span>
            <strong>Vytvoriť nový kanál</strong>
            <small>Pripravte súkromný priestor pre nový projekt alebo tím.</small>
          </span>
          <ArrowRight />
        </button>
        <button
          ref={archiveButtonRef}
          type="button"
          className="channel-action-card"
          onClick={() => setArchiveOpen(true)}
        >
          <span className="channel-action-icon archive">
            <FolderArchive />
          </span>
          <span>
            <strong>Archivovať kanál</strong>
            <small>Ukončite hotový projekt a pošlite žiadosť na schválenie.</small>
          </span>
          <ArrowRight />
        </button>
      </section>

      <section className="channel-request-board">
        <div className="channel-request-heading">
          <div>
            <p className="eyebrow">Prehľad</p>
            <h2>Žiadosti o archiváciu</h2>
            <p>Tu vidíte iba žiadosti, ktoré ešte potrebujú dokončiť.</p>
          </div>
          <div className="channel-request-count">
            <strong>{archives.length}</strong>
            <span>{archiveRequestLabel(archives.length)}</span>
          </div>
        </div>
        {isAdmin && recoverableArchives.length > 0 && (
          <div className="archive-recovery-note">
            <div>
              <RefreshCw />
              <span>Niektoré schválené archivácie sa nepodarilo dokončiť.</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() => void recoverArchives()}
            >
              Skúsiť dokončiť
            </Button>
          </div>
        )}
        <div className="archive-list friendly-archive-list">
          {archives.length === 0 && (
            <EmptyState
              icon={Check}
              title="Všetko je vybavené"
              text="Momentálne tu nie je žiadna žiadosť, ktorá čaká na rozhodnutie."
            />
          )}
          {archives.map((item) => (
            <article className={`archive-row state-${item.state}`} key={item.id}>
              <span className="archive-state-mark">
                <Archive />
              </span>
              <div>
                <div className="archive-row-title">
                  <strong>#{item.original_channel_name}</strong>
                  <Badge variant="secondary">
                    {item.state === 'pending'
                      ? 'Čaká na schválenie'
                      : item.state === 'archiving'
                        ? 'Dokončuje sa'
                        : 'Vyžaduje pozornosť'}
                  </Badge>
                </div>
                <span>{item.reason}</span>
                {item.state === 'pending' && (
                  <small>Žiadosť platí do {dateTime(item.expires_at)}</small>
                )}
              </div>
              {isAdmin && item.state === 'pending' && (
                <div className="archive-row-actions">
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
      </section>

      <Dialog open={createOpen} onOpenChange={(open) => !busy && setCreateOpen(open)}>
        <DialogContent
          className="channel-dialog"
          showCloseButton={!busy}
          finalFocus={() => createButtonRef.current}
        >
          <DialogHeader className="channel-dialog-header">
            <span className="channel-dialog-icon">
              <Plus />
            </span>
            <div>
              <DialogTitle>Vytvoriť nový kanál</DialogTitle>
              <DialogDescription>
                Stačí názov. Ľudí a skupiny môžete pridať podľa potreby.
              </DialogDescription>
            </div>
          </DialogHeader>
          <div className="channel-dialog-body">
            <section className="channel-dialog-section">
              <div className="channel-dialog-section-title">
                <span>1</span>
                <div>
                  <strong>Ako sa má kanál volať?</strong>
                  <small>Vyberte symbol a napíšte zrozumiteľný názov.</small>
                </div>
              </div>
              <div className="channel-name-builder">
                <div className="emoji-choice-grid" aria-label="Symbol kanála">
                  {suggestedEmojis.map((option) => (
                    <button
                      type="button"
                      key={option}
                      className={effectiveEmoji === option ? 'selected' : ''}
                      aria-label={`Použiť ${option}`}
                      aria-pressed={!emojiIsAutomatic && emoji === option}
                      onClick={() => {
                        setEmoji(option)
                        setEmojiIsAutomatic(false)
                      }}
                    >
                      {option}
                    </button>
                  ))}
                  <ChannelEmojiPicker
                    selected={!emojiIsAutomatic && !suggestedEmojis.includes(emoji)}
                    onChange={(value) => {
                      setEmoji(value)
                      setEmojiIsAutomatic(false)
                    }}
                  />
                </div>
                <Field label="Názov">
                  <Input
                    placeholder="napríklad-letný-tábor"
                    value={name}
                    onChange={(event) => {
                      const nextValue = event.target.value
                      setName(
                        nameComposition.current || (event.nativeEvent as InputEvent).isComposing
                          ? nextValue
                          : normalizeChannelName(nextValue),
                      )
                    }}
                    onCompositionStart={() => {
                      nameComposition.current = true
                    }}
                    onCompositionEnd={(event) => {
                      nameComposition.current = false
                      setName(normalizeChannelName(event.currentTarget.value))
                    }}
                    onBlur={() => setName((current) => normalizeChannelName(current, true))}
                    maxLength={100}
                    autoFocus
                  />
                </Field>
              </div>
              <div className="channel-name-preview" aria-live="polite">
                <span>Názov na Discorde</span>
                <strong>
                  #{effectiveEmoji}・{finalChannelName || 'názov-kanála'}
                </strong>
                {emojiIsAutomatic && <small>Symbol vyberá Carlo podľa názvu</small>}
              </div>
              <div
                className={`channel-location-note ${defaultCategory || selectedCategory ? '' : 'warning'}`}
              >
                <MessageSquareMore />
                <span>
                  {selectedCategory
                    ? `Kanál bude zaradený do časti „${selectedCategory.name}“.`
                    : defaultCategory
                      ? `Carlo ho zaradí do časti „${defaultCategory.name}“.`
                      : 'Najprv vyberte miesto pre nové projektové kanály v Nastaveniach.'}
                </span>
                {!defaultCategory && !selectedCategory && (
                  <a href="/nastavenia">Otvoriť Nastavenia</a>
                )}
              </div>
              {availableCategories.length > 1 && (
                <details className="channel-optional-control">
                  <summary>
                    <FolderTree />
                    <span>Zmeniť umiestnenie</span>
                    <ChevronDown className="disclosure-caret" />
                  </summary>
                  <Field label="Časť servera">
                    <select
                      value={categoryId}
                      onChange={(event) => setCategoryId(event.target.value)}
                    >
                      <option value="">
                        {defaultCategory
                          ? `Predvolené · ${defaultCategory.name}`
                          : 'Vyberte miesto'}
                      </option>
                      {availableCategories
                        .filter((category) => category.id !== defaultCategory?.id)
                        .map((category) => (
                          <option value={category.id} key={category.id}>
                            {category.name}
                          </option>
                        ))}
                    </select>
                  </Field>
                </details>
              )}
            </section>

            <section className="channel-dialog-section">
              <div className="channel-dialog-section-title">
                <span>2</span>
                <div>
                  <strong>Kto má mať prístup?</strong>
                  <small>Kanál bude súkromný. Vyberte iba ľudí, ktorí ho potrebujú.</small>
                </div>
              </div>
              <div className="channel-access-stack">
                <MemberPicker
                  label="Kto bude kanál viesť?"
                  description="Môžete vybrať aj viacerých. Ak nevyberiete nikoho, budete to vy."
                  value={leaderIds}
                  excludedIds={memberIds}
                  emptyLabel="Kanál budete viesť vy"
                  onChange={(ids) => {
                    setLeaderIds(ids)
                    setMemberIds((current) => current.filter((id) => !ids.includes(id)))
                  }}
                />
                <MemberPicker
                  label="Koho chcete pridať?"
                  description="Píšte meno a vyberte ľudí zo zoznamu."
                  value={memberIds}
                  excludedIds={leaderIds}
                  onChange={setMemberIds}
                />
                <details className="channel-optional-control access-groups">
                  <summary>
                    <UsersRound />
                    <span>Pridať celú skupinu</span>
                    {roleIds.length > 0 && (
                      <span className="selected-groups-count">
                        {selectedGroupsLabel(roleIds.length)}
                      </span>
                    )}
                    <ChevronDown className="disclosure-caret" />
                  </summary>
                  <RolePicker
                    roles={directory.roles}
                    value={roleIds}
                    onChange={setRoleIds}
                    showHeading={false}
                  />
                </details>
              </div>
            </section>
          </div>
          <DialogFooter className="channel-dialog-footer">
            <Button variant="outline" disabled={busy} onClick={() => setCreateOpen(false)}>
              Zrušiť
            </Button>
            <Button
              disabled={
                busy ||
                !finalChannelName ||
                !effectiveEmoji.trim() ||
                (!categoryId && !defaultCategory)
              }
              onClick={() => void create()}
            >
              {busy ? <LoaderCircle className="spin" /> : <Plus />} Vytvoriť kanál
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={archiveOpen} onOpenChange={(open) => !busy && setArchiveOpen(open)}>
        <DialogContent
          className="channel-dialog archive-dialog"
          showCloseButton={!busy}
          finalFocus={() => archiveButtonRef.current}
        >
          <DialogHeader className="channel-dialog-header">
            <span className="channel-dialog-icon archive">
              <FolderArchive />
            </span>
            <div>
              <DialogTitle>Archivovať kanál</DialogTitle>
              <DialogDescription>
                Hotový projekt sa po schválení presunie do archívu.
              </DialogDescription>
            </div>
          </DialogHeader>
          <div className="channel-dialog-body compact">
            <ChannelSelect
              label="Ktorý kanál chcete archivovať?"
              value={archiveChannel || null}
              channels={archivableChannels}
              onChange={(id) => setArchiveChannel(id ?? '')}
            />
            <Field label="Prečo sa kanál archivuje?">
              <Textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Napríklad: projekt je dokončený"
              />
            </Field>
            <div className="archive-explanation">
              <ShieldCheck />
              <span>Žiadosť najprv skontroluje Admin. Dovtedy sa v kanáli nič nezmení.</span>
            </div>
          </div>
          <DialogFooter className="channel-dialog-footer">
            <Button variant="outline" disabled={busy} onClick={() => setArchiveOpen(false)}>
              Zrušiť
            </Button>
            <Button
              disabled={busy || !archiveChannel || reason.trim().length < 3}
              onClick={() => void requestArchive()}
            >
              {busy ? <LoaderCircle className="spin" /> : <Archive />} Odoslať žiadosť
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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

function ChannelEmojiPicker({
  selected,
  onChange,
}: {
  selected: boolean
  onChange: (value: string) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <button
            type="button"
            className={selected ? 'selected more-emoji' : 'more-emoji'}
            aria-label="Otvoriť všetky emoji"
            aria-pressed={selected}
          />
        }
      >
        <SmilePlus />
      </PopoverTrigger>
      <PopoverContent className="channel-emoji-popover" aria-label="Všetky emoji">
        <EmojiPicker
          autoFocusSearch
          lazyLoadEmojis
          emojiStyle={EmojiStyle.NATIVE}
          categories={carloEmojiCategories}
          searchPlaceholder="Hľadať emoji…"
          searchClearButtonLabel="Vymazať hľadanie"
          previewConfig={{ showPreview: false }}
          width="100%"
          height={390}
          onEmojiClick={(selection) => {
            onChange(selection.emoji)
            setOpen(false)
          }}
        />
      </PopoverContent>
    </Popover>
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
function calendarErrorText(value: string) {
  const normalized = value.toLocaleLowerCase('sk')
  if (normalized.includes('permission') || normalized.includes('forbidden'))
    return 'Carlo nemá ku kalendáru prístup. Skontrolujte jeho zdieľanie.'
  if (normalized.includes('not found') || normalized.includes('404'))
    return 'Kalendár sa nenašiel. Skontrolujte jeho Google Calendar ID.'
  return 'Google Kalendár neodpovedal správne. Skúste obnovenie znova.'
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
          <p className="eyebrow">Trvalé pravidlá</p>
          <h1>Nastavenia</h1>
        </div>
      </div>
      <div className="settings-loading">
        <LoaderCircle className="spin" /> Načítavam živé údaje z Discordu…
      </div>
    </section>
  )
}
function PageError({
  notice,
  onRetry,
  retryLabel = 'Skúsiť znova',
}: {
  notice: Notice
  onRetry: () => void
  retryLabel?: string
}) {
  return (
    <section className="settings-page">
      <div className="settings-error">
        <Settings2 />
        <h1>Nastavenia sa nepodarilo načítať</h1>
        <p>{notice?.text ?? 'Skúste to znova.'}</p>
        <Button onClick={onRetry}>
          {retryLabel} <ChevronRight />
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
function restoredPublicationDraft(key: string, fallback: PublicationSettings) {
  try {
    const stored = window.sessionStorage.getItem(key)
    if (!stored) return fallback
    const parsed = JSON.parse(stored) as Partial<PublicationSettings>
    if (
      parsed.guild_id !== fallback.guild_id ||
      parsed.version !== fallback.version ||
      typeof parsed.publication_weekday !== 'number' ||
      typeof parsed.publication_time !== 'string'
    ) {
      window.sessionStorage.removeItem(key)
      return fallback
    }
    return { ...fallback, ...parsed }
  } catch {
    window.sessionStorage.removeItem(key)
    return fallback
  }
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

function archiveRequestLabel(count: number) {
  if (count === 1) return 'otvorená žiadosť'
  if (count > 1 && count < 5) return 'otvorené žiadosti'
  return 'otvorených žiadostí'
}

function normalizeChannelName(value: string, final = false) {
  const normalized = value
    .normalize('NFC')
    .toLocaleLowerCase('sk-SK')
    .replace(/[^\p{L}\p{N}-]+/gu, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+/g, '')
    .slice(0, 100)
  return final ? normalized.replace(/-+$/g, '') : normalized
}

function suggestChannelEmojis(name: string) {
  const searchableName = name.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('sk-SK')
  const suggestions: Array<[string[], string[]]> = [
    [
      ['hudba', 'koncert', 'kapela', 'spev', 'zbor'],
      ['🎵', '🎤', '🎸', '🎧'],
    ],
    [
      ['divadlo', 'predstavenie', 'drama', 'tanec'],
      ['🎭', '💃', '🎬', '✨'],
    ],
    [
      ['kniha', 'citanie', 'skola', 'kurz', 'vzdelavanie'],
      ['📚', '✏️', '🧠', '💡'],
    ],
    [
      ['zahrada', 'priroda', 'eko', 'rastlin', 'strom'],
      ['🌱', '🌳', '🌍', '♻️'],
    ],
    [
      ['umenie', 'tvoriv', 'malovanie', 'kreslenie'],
      ['🎨', '🖌️', '✂️', '✨'],
    ],
    [
      ['dielna', 'oprava', 'stavba', 'technika'],
      ['🛠️', '🔧', '⚙️', '🧰'],
    ],
    [
      ['tabor', 'vylet', 'stanovanie'],
      ['⛺', '🌲', '🔥', '🧭'],
    ],
    [
      ['film', 'kino', 'video'],
      ['🎬', '🍿', '📽️', '🎞️'],
    ],
    [
      ['futbal', 'sport', 'turnaj', 'cvicenie'],
      ['⚽', '🏐', '🏀', '🏆'],
    ],
    [
      ['varenie', 'kuchyna', 'jedlo', 'vecera'],
      ['🍲', '🍽️', '☕', '🥕'],
    ],
    [
      ['fot', 'kamera'],
      ['📷', '📸', '🎞️', '🖼️'],
    ],
    [
      ['oslava', 'party', 'festival'],
      ['🎉', '🥳', '🎈', '✨'],
    ],
    [
      ['hra', 'herny', 'gaming'],
      ['🎲', '🎮', '🧩', '♟️'],
    ],
    [
      ['bike', 'bicykel', 'cyklo'],
      ['🚲', '🛞', '🗺️', '🏁'],
    ],
  ]
  return (
    suggestions.find(([keywords]) =>
      keywords.some((keyword) => searchableName.includes(keyword)),
    )?.[1] ?? defaultChannelEmojis
  )
}

function selectedGroupsLabel(count: number) {
  if (count === 1) return '1 vybratá'
  if (count < 5) return `${count} vybraté`
  return `${count} vybratých`
}
