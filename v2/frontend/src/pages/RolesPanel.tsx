import {
  Check,
  LoaderCircle,
  Search,
  ShieldCheck,
  TriangleAlert,
  UserRound,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

import {
  ApiError,
  type DiscordMemberOption,
  type PublicationSettings,
  searchDiscordMembers,
  setDiscordRole,
} from '../api/client'
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
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import type { Notice } from './SettingsPage'

type ManagedRole = 'team_mod' | 'admin'
type SearchState = 'idle' | 'searching' | 'ready' | 'empty' | 'error'

const roleCopy: Record<ManagedRole, { name: string; description: string; removal: string }> = {
  team_mod: {
    name: 'Team Mod',
    description: 'Môže upravovať oznamy a spravovať kanály.',
    removal: 'Človek stratí redakčný prístup a možnosť spravovať kanály cez Carla.',
  },
  admin: {
    name: 'Admin',
    description: 'Má plnú správu Carla vrátane nastavení, rolí a schvaľovania archivácie.',
    removal: 'Človek stratí prístup k nastaveniam a správe rolí.',
  },
}

export function RolesPanel({
  publication,
  setNotice,
}: {
  publication: PublicationSettings
  setNotice: (notice: Notice) => void
}) {
  const searchId = useId()
  const resultsId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const selectedHeadingRef = useRef<HTMLHeadingElement>(null)
  const submittingRef = useRef(false)
  const [query, setQuery] = useState('')
  const [members, setMembers] = useState<DiscordMemberOption[]>([])
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [retryRevision, setRetryRevision] = useState(0)
  const [activeIndex, setActiveIndex] = useState(0)
  const [selectedMember, setSelectedMember] = useState<DiscordMemberOption | null>(null)
  const [pending, setPending] = useState<{
    member: DiscordMemberOption
    role: ManagedRole
    enabled: boolean
  } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    const normalized = query.trim()
    if (!normalized) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void searchDiscordMembers(normalized, controller.signal)
        .then((results) => {
          setMembers(results)
          setSearchState(results.length > 0 ? 'ready' : 'empty')
        })
        .catch(() => {
          if (!controller.signal.aborted) setSearchState('error')
        })
    }, 240)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, retryRevision])

  function selectMember(member: DiscordMemberOption) {
    setSelectedMember(member)
    setQuery('')
    setMembers([])
    setSearchState('idle')
    window.requestAnimationFrame(() => selectedHeadingRef.current?.focus())
  }

  function openConfirmation(member: DiscordMemberOption, role: ManagedRole, enabled: boolean) {
    setActionError(null)
    setPending({ member, role, enabled })
  }

  async function confirmChange() {
    if (!pending || submittingRef.current) return
    submittingRef.current = true
    setSubmitting(true)
    setActionError(null)
    try {
      const changed = await setDiscordRole(pending.member.id, pending.role, pending.enabled)
      setSelectedMember(changed)
      setMembers((current) => current.map((item) => (item.id === changed.id ? changed : item)))
      const action = pending.enabled ? 'udelené' : 'odobrané'
      setNotice({
        kind: 'success',
        text: `${roleCopy[pending.role].name} oprávnenie bolo ${action} človeku ${changed.display_name}.`,
      })
      setPending(null)
    } catch (error) {
      setActionError(roleMutationError(error, pending))
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  return (
    <div className="roles-workspace">
      <section className="roles-search-panel" aria-labelledby="roles-search-title">
        <div className="roles-section-heading">
          <span className="roles-section-icon" aria-hidden="true">
            <Users />
          </span>
          <div>
            <p className="eyebrow">Prvý krok</p>
            <h2 id="roles-search-title">Nájdite človeka</h2>
            <p>Začnite písať meno alebo Discord prezývku.</p>
          </div>
        </div>
        <div className="roles-member-search">
          <Label htmlFor={searchId}>Koho chcete spravovať?</Label>
          <div className="picker-search-shell">
            <Search aria-hidden="true" />
            <Input
              ref={inputRef}
              id={searchId}
              role="combobox"
              aria-autocomplete="list"
              aria-controls={resultsId}
              aria-expanded={searchState === 'ready'}
              aria-activedescendant={
                searchState === 'ready' ? `${resultsId}-${activeIndex}` : undefined
              }
              value={query}
              placeholder="Napríklad Martina alebo martina_90"
              onChange={(event) => {
                const next = event.target.value
                setQuery(next)
                setMembers([])
                setActiveIndex(0)
                setSearchState(next.trim() ? 'searching' : 'idle')
              }}
              onKeyDown={(event) => {
                if (searchState !== 'ready' || members.length === 0) return
                if (event.key === 'ArrowDown') {
                  event.preventDefault()
                  setActiveIndex((current) => (current + 1) % members.length)
                }
                if (event.key === 'ArrowUp') {
                  event.preventDefault()
                  setActiveIndex((current) => (current - 1 + members.length) % members.length)
                }
                if (event.key === 'Enter') {
                  event.preventDefault()
                  const member = members[activeIndex]
                  if (member) selectMember(member)
                }
                if (event.key === 'Escape') {
                  setQuery('')
                  setMembers([])
                  setSearchState('idle')
                }
              }}
            />
            {searchState === 'searching' && (
              <LoaderCircle className="spin" aria-label="Vyhľadávam ľudí" />
            )}
            {query && searchState !== 'searching' && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Vymazať vyhľadávanie"
                onClick={() => {
                  setQuery('')
                  setMembers([])
                  setSearchState('idle')
                  inputRef.current?.focus()
                }}
              >
                <X />
              </Button>
            )}
          </div>
          <SearchResults
            id={resultsId}
            state={searchState}
            members={members}
            activeIndex={activeIndex}
            onActive={setActiveIndex}
            onSelect={selectMember}
            onRetry={() => {
              setMembers([])
              setSearchState('searching')
              setRetryRevision((current) => current + 1)
            }}
          />
        </div>
      </section>

      {selectedMember ? (
        <MemberPermissions
          member={selectedMember}
          publication={publication}
          headingRef={selectedHeadingRef}
          submitting={submitting}
          pending={pending}
          onChange={openConfirmation}
          onChooseAnother={() => {
            setSelectedMember(null)
            window.requestAnimationFrame(() => inputRef.current?.focus())
          }}
        />
      ) : (
        <section className="roles-selection-empty" aria-labelledby="roles-empty-title">
          <span aria-hidden="true">
            <UserRound />
          </span>
          <div>
            <h2 id="roles-empty-title">Oprávnenia sa ukážu po výbere</h2>
            <p>Najprv vyhľadajte konkrétneho človeka. Bez potvrdenia sa nič nezmení.</p>
          </div>
        </section>
      )}

      <AlertDialog
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open && !submitting) {
            setPending(null)
            setActionError(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pending ? confirmationTitle(pending) : 'Zmeniť oprávnenie'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pending ? confirmationDescription(pending) : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {actionError && (
            <div className="role-action-error" role="alert">
              <TriangleAlert aria-hidden="true" />
              <span>{actionError}</span>
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitting}>Zrušiť</AlertDialogCancel>
            <AlertDialogAction
              variant={pending && !pending.enabled ? 'destructive' : 'default'}
              disabled={submitting}
              onClick={() => void confirmChange()}
            >
              {submitting && <LoaderCircle className="spin" aria-hidden="true" />}
              {pending ? actionLabel(pending.role, pending.enabled) : 'Zmeniť oprávnenie'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function SearchResults({
  id,
  state,
  members,
  activeIndex,
  onActive,
  onSelect,
  onRetry,
}: {
  id: string
  state: SearchState
  members: DiscordMemberOption[]
  activeIndex: number
  onActive: (index: number) => void
  onSelect: (member: DiscordMemberOption) => void
  onRetry: () => void
}) {
  if (state === 'idle')
    return <p className="roles-search-hint">Výsledky sa zobrazia automaticky.</p>
  if (state === 'searching')
    return (
      <p className="roles-search-status" role="status">
        Vyhľadávam ľudí…
      </p>
    )
  if (state === 'empty')
    return (
      <p className="roles-search-status" role="status">
        Nikto sa nenašiel. Skúste inú časť mena alebo prezývky.
      </p>
    )
  if (state === 'error')
    return (
      <div className="roles-search-error" role="alert">
        <div>
          <TriangleAlert aria-hidden="true" />
          <span>Ľudí sa teraz nepodarilo vyhľadať. Vaše zadanie zostalo zachované.</span>
        </div>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Skúsiť znova
        </Button>
      </div>
    )
  return (
    <div id={id} className="roles-search-results" role="listbox" aria-label="Nájdení ľudia">
      {members.map((member, index) => (
        <button
          type="button"
          role="option"
          aria-selected={activeIndex === index}
          id={`${id}-${index}`}
          key={member.id}
          className={activeIndex === index ? 'active' : ''}
          onMouseEnter={() => onActive(index)}
          onClick={() => onSelect(member)}
        >
          <MemberAvatar member={member} />
          <span>
            <strong>{member.display_name}</strong>
            <small>@{member.username}</small>
          </span>
          <span className="roles-select-person">Vybrať</span>
        </button>
      ))}
    </div>
  )
}

function MemberPermissions({
  member,
  publication,
  headingRef,
  submitting,
  pending,
  onChange,
  onChooseAnother,
}: {
  member: DiscordMemberOption
  publication: PublicationSettings
  headingRef: React.RefObject<HTMLHeadingElement | null>
  submitting: boolean
  pending: { member: DiscordMemberOption; role: ManagedRole; enabled: boolean } | null
  onChange: (member: DiscordMemberOption, role: ManagedRole, enabled: boolean) => void
  onChooseAnother: () => void
}) {
  return (
    <section className="member-permissions" aria-labelledby="selected-member-title">
      <header className="selected-member-header">
        <div className="selected-member-identity">
          <MemberAvatar member={member} />
          <div>
            <p className="eyebrow">Vybraný človek</p>
            <h2 id="selected-member-title" ref={headingRef} tabIndex={-1}>
              {member.display_name}
            </h2>
            <p>@{member.username}</p>
          </div>
        </div>
        <Button variant="outline" onClick={onChooseAnother}>
          Vybrať iného človeka
        </Button>
      </header>
      <div className="permission-list">
        {(['team_mod', 'admin'] as const).map((role) => {
          const roleId = role === 'admin' ? publication.admin_role_id : publication.team_mod_role_id
          const enabled = roleId !== null && member.role_ids.includes(roleId)
          const isBusy = submitting && pending?.member.id === member.id && pending.role === role
          return (
            <article className="permission-row" key={role}>
              <span className={enabled ? 'permission-mark enabled' : 'permission-mark'}>
                {enabled ? <Check aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}
              </span>
              <div className="permission-copy">
                <div>
                  <h3>{roleCopy[role].name}</h3>
                  <Badge variant={enabled ? 'default' : 'secondary'}>
                    {enabled ? 'Má oprávnenie' : 'Nemá oprávnenie'}
                  </Badge>
                </div>
                <p>{roleCopy[role].description}</p>
              </div>
              <Button
                variant={enabled ? 'outline' : 'default'}
                disabled={submitting}
                onClick={() => onChange(member, role, !enabled)}
              >
                {isBusy && <LoaderCircle className="spin" aria-hidden="true" />}
                {actionLabel(role, !enabled)}
              </Button>
            </article>
          )
        })}
      </div>
      <p className="roles-safety-note">
        <ShieldCheck aria-hidden="true" />
        Carlo pred potvrdením znova overí vaše oprávnenie aj to, či môže zvolenú rolu bezpečne
        zmeniť.
      </p>
    </section>
  )
}

function MemberAvatar({ member }: { member: DiscordMemberOption }) {
  if (member.avatar_url)
    return <img className="role-member-avatar" src={member.avatar_url} alt="" />
  return (
    <span className="role-member-avatar role-member-avatar-fallback" aria-hidden="true">
      {member.display_name.slice(0, 1).toLocaleUpperCase('sk')}
    </span>
  )
}

function actionLabel(role: ManagedRole, enabled: boolean) {
  return `${enabled ? 'Udeliť' : 'Odobrať'} ${roleCopy[role].name}`
}

function confirmationTitle(pending: {
  member: DiscordMemberOption
  role: ManagedRole
  enabled: boolean
}) {
  return `${actionLabel(pending.role, pending.enabled)} človeku ${pending.member.display_name}?`
}

function confirmationDescription(pending: {
  member: DiscordMemberOption
  role: ManagedRole
  enabled: boolean
}) {
  if (pending.enabled)
    return `${pending.member.display_name} získa toto oprávnenie na Discord serveri aj v Carlovi.`
  const lastAdminNote =
    pending.role === 'admin'
      ? ' Ak je posledným Adminom, Carlo zmenu odmietne a nič sa nezmení.'
      : ''
  return `${roleCopy[pending.role].removal}${lastAdminNote}`
}

function roleMutationError(
  error: unknown,
  pending: { member: DiscordMemberOption; role: ManagedRole; enabled: boolean },
) {
  const role = roleCopy[pending.role].name
  if (error instanceof ApiError && error.code === 'last_admin')
    return `Admin oprávnenie človeku ${pending.member.display_name} nemožno odobrať. Je posledným Adminom. Najprv udeľte Admin oprávnenie niekomu ďalšiemu.`
  if (error instanceof ApiError && error.status === 403)
    return `Vaše oprávnenie na správu rolí už nie je platné. ${role} sa nepodarilo bezpečne zmeniť. Obnovte stránku alebo sa znovu prihláste.`
  if (error instanceof ApiError && error.code === 'discord_unavailable')
    return `Discord výsledok zmeny ${role} sa nepodarilo potvrdiť. Vyhľadajte človeka znova; ak sa stav nezmenil, skontrolujte postavenie Carlovej roly na Discorde a skúste to opäť.`
  return `${role} oprávnenie človeku ${pending.member.display_name} sa nepodarilo zmeniť. Načítajte jeho stav znova a skúste to opäť.`
}
