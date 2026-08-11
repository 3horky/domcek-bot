import { Check, Hash, LoaderCircle, Search, UserRound, X } from 'lucide-react'
import { useEffect, useId, useMemo, useRef, useState } from 'react'

import {
  ApiError,
  type DiscordChannelOption,
  type DiscordMemberOption,
  type DiscordRoleOption,
  searchDiscordMembers,
} from '../api/client'
import { Button } from './ui/button'
import { Input } from './ui/input'

type SearchState = 'idle' | 'loading' | 'ready' | 'error'

export function MemberPicker({
  label,
  description,
  value,
  onChange,
  multiple = true,
  emptyLabel = 'Nikto nie je vybraný',
  excludedIds = [],
}: {
  label: string
  description: string
  value: string[]
  onChange: (ids: string[]) => void
  multiple?: boolean
  emptyLabel?: string
  excludedIds?: string[]
}) {
  const listId = useId()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DiscordMemberOption[]>([])
  const [knownMembers, setKnownMembers] = useState<Record<string, DiscordMemberOption>>({})
  const [state, setState] = useState<SearchState>('idle')
  const requestSequence = useRef(0)

  useEffect(() => {
    const normalized = query.trim()
    if (!normalized) return
    const sequence = ++requestSequence.current
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setState('loading')
      void searchDiscordMembers(normalized, controller.signal)
        .then((members) => {
          if (sequence !== requestSequence.current) return
          setResults(members)
          setKnownMembers((current) => {
            const next = { ...current }
            for (const member of members) next[member.id] = member
            return next
          })
          setState('ready')
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || sequence !== requestSequence.current) return
          setResults([])
          setState('error')
          if (!(error instanceof ApiError)) throw error
        })
    }, 240)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query])

  function toggleMember(member: DiscordMemberOption) {
    if (value.includes(member.id)) {
      onChange(value.filter((id) => id !== member.id))
    } else {
      onChange(multiple ? [...value, member.id] : [member.id])
    }
  }

  return (
    <div className="discord-picker">
      <div className="discord-picker-heading">
        <div>
          <label htmlFor={`${listId}-search`}>{label}</label>
          <span>{description}</span>
        </div>
        {value.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => onChange([])}>
            <X /> Zrušiť výber
          </Button>
        )}
      </div>
      {value.length > 0 ? (
        <div className="picker-selections" aria-label={`Vybrané: ${label}`}>
          {value.map((id) => (
            <button
              type="button"
              key={id}
              onClick={() => onChange(value.filter((item) => item !== id))}
            >
              <MemberAvatar member={knownMembers[id]} />
              <span>{knownMembers[id]?.display_name ?? `Discord člen ${id}`}</span>
              <X aria-hidden="true" />
            </button>
          ))}
        </div>
      ) : (
        <p className="picker-empty-selection">{emptyLabel}</p>
      )}
      <div className="picker-search-shell">
        <Search aria-hidden="true" />
        <Input
          id={`${listId}-search`}
          role="combobox"
          aria-controls={listId}
          aria-expanded={query.trim().length > 0}
          aria-autocomplete="list"
          value={query}
          placeholder="Začnite písať meno alebo prezývku…"
          onChange={(event) => {
            const next = event.target.value
            setQuery(next)
            if (!next.trim()) {
              setResults([])
              setState('idle')
            }
          }}
        />
        {state === 'loading' && <LoaderCircle className="spin" aria-label="Vyhľadávam" />}
      </div>
      {query.trim() && (
        <div className="picker-results" id={listId} role="listbox" aria-multiselectable={multiple}>
          {state === 'error' && <p>Členov sa nepodarilo načítať. Skúste písať znova.</p>}
          {state === 'ready' && results.length === 0 && <p>Nenašli sa žiadni členovia.</p>}
          {results.filter((member) => !excludedIds.includes(member.id)).map((member) => {
            const selected = value.includes(member.id)
            return (
              <button
                type="button"
                role="option"
                aria-selected={selected}
                className={selected ? 'selected' : ''}
                key={member.id}
                onClick={() => toggleMember(member)}
              >
                <MemberAvatar member={member} />
                <span>
                  <strong>{member.display_name}</strong>
                  <small>@{member.username}</small>
                </span>
                <span className="picker-result-state">
                  {selected ? <Check /> : multiple ? 'Pridať' : 'Vybrať'}
                </span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function RolePicker({
  roles,
  value,
  onChange,
}: {
  roles: DiscordRoleOption[]
  value: string[]
  onChange: (ids: string[]) => void
}) {
  const [query, setQuery] = useState('')
  const available = useMemo(
    () =>
      roles.filter(
        (role) =>
          !role.managed &&
          role.name !== '@everyone' &&
          role.name.toLocaleLowerCase('sk').includes(query.trim().toLocaleLowerCase('sk')),
      ),
    [query, roles],
  )
  const selected = roles.filter((role) => value.includes(role.id))
  return (
    <div className="discord-picker role-picker">
      <div className="discord-picker-heading">
        <div>
          <label htmlFor="role-picker-search">Roly s prístupom</label>
          <span>Voliteľné. Kanál môže zostať bez vybratej roly.</span>
        </div>
        {value.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => onChange([])}>
            <X /> Zrušiť výber
          </Button>
        )}
      </div>
      {selected.length > 0 ? (
        <div className="picker-selections" aria-label="Vybrané roly">
          {selected.map((role) => (
            <button
              type="button"
              key={role.id}
              onClick={() => onChange(value.filter((id) => id !== role.id))}
            >
              <span className="role-dot" aria-hidden="true" />
              <span>{role.name}</span>
              <X aria-hidden="true" />
            </button>
          ))}
        </div>
      ) : (
        <p className="picker-empty-selection">Žiadna rola – prístup dostanú iba vybraní ľudia.</p>
      )}
      <div className="picker-search-shell">
        <Search aria-hidden="true" />
        <Input
          id="role-picker-search"
          value={query}
          placeholder="Filtrovať roly…"
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="picker-results role-results" role="listbox" aria-multiselectable="true">
        {available.map((role) => {
          const isSelected = value.includes(role.id)
          return (
            <button
              type="button"
              role="option"
              aria-selected={isSelected}
              className={isSelected ? 'selected' : ''}
              key={role.id}
              onClick={() =>
                onChange(isSelected ? value.filter((id) => id !== role.id) : [...value, role.id])
              }
            >
              <span className="role-avatar">{role.name.slice(0, 1).toLocaleUpperCase('sk')}</span>
              <span>
                <strong>{role.name}</strong>
                <small>Discord rola</small>
              </span>
              <span className="picker-result-state">{isSelected ? <Check /> : 'Pridať'}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function ChannelMultiPicker({
  channels,
  value,
  onChange,
}: {
  channels: DiscordChannelOption[]
  value: string[]
  onChange: (ids: string[]) => void
}) {
  const [query, setQuery] = useState('')
  const selected = channels.filter((channel) => value.includes(channel.id))
  const available = channels.filter((channel) =>
    channel.name.toLocaleLowerCase('sk').includes(query.trim().toLocaleLowerCase('sk')),
  )
  return (
    <div className="discord-picker channel-picker">
      <div className="discord-picker-heading">
        <div>
          <label htmlFor="channel-picker-search">Kanály</label>
          <span>Vyberte, kde má Carlo reagovať automaticky.</span>
        </div>
        {value.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => onChange([])}>
            <X /> Zrušiť výber
          </Button>
        )}
      </div>
      {selected.length > 0 ? (
        <div className="picker-selections">
          {selected.map((channel) => (
            <button
              type="button"
              key={channel.id}
              onClick={() => onChange(value.filter((id) => id !== channel.id))}
            >
              <Hash />
              <span>{channel.name}</span>
              <X />
            </button>
          ))}
        </div>
      ) : (
        <p className="picker-empty-selection">Žiadny kanál nie je vybraný.</p>
      )}
      <div className="picker-search-shell">
        <Search />
        <Input
          id="channel-picker-search"
          value={query}
          placeholder="Filtrovať kanály…"
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="picker-results compact-results" role="listbox" aria-multiselectable="true">
        {available.map((channel) => {
          const isSelected = value.includes(channel.id)
          return (
            <button
              type="button"
              role="option"
              aria-selected={isSelected}
              className={isSelected ? 'selected' : ''}
              key={channel.id}
              onClick={() =>
                onChange(
                  isSelected ? value.filter((id) => id !== channel.id) : [...value, channel.id],
                )
              }
            >
              <span className="channel-avatar">
                <Hash />
              </span>
              <span>
                <strong>#{channel.name}</strong>
                <small>Textový kanál</small>
              </span>
              <span className="picker-result-state">{isSelected ? <Check /> : 'Pridať'}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function MemberAvatar({ member }: { member?: DiscordMemberOption }) {
  if (member?.avatar_url) return <img className="picker-avatar" src={member.avatar_url} alt="" />
  return (
    <span className="picker-avatar picker-avatar-fallback">
      <UserRound aria-hidden="true" />
    </span>
  )
}
