import { FlaskConical, LoaderCircle, RotateCcw, Save, Send, TriangleAlert } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

import {
  ApiError,
  type DiscordDirectory,
  type ReactionSettings,
  testDiscordReaction,
  updateReactionSettings,
} from '../api/client'
import { ChannelMultiPicker } from '../components/DiscordPickers'
import {
  ReactionEmojiPicker,
  ReactionEmojiVisual,
  type SelectedReactionEmoji,
} from '../components/ReactionEmojiPicker'
import { UnsavedChangesGuard } from '../components/UnsavedChangesGuard'
import { Button } from '../components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'
import { Switch } from '../components/ui/switch'
import type { Notice } from './SettingsPage'

type ReactionKind = 'seen' | 'mention' | 'auto'

const ruleCopy: Record<ReactionKind, { title: string; description: string; moment: string }> = {
  seen: {
    title: 'Reakcia pod prehľadom',
    description: 'Pridá sa pod poslednú správu každého úspešne zverejneného prehľadu.',
    moment: 'po úspešnom zverejnení prehľadu',
  },
  mention: {
    title: 'Reakcia pri označení Carla',
    description: 'Carlo zareaguje, keď ho niekto označí v správe.',
    moment: 'keď niekto označí Carla',
  },
  auto: {
    title: 'Reakcia na nové správy',
    description: 'Každá nová správa vo vybraných kanáloch dostane zvolené emoji.',
    moment: 'pri novej správe vo vybranom kanáli',
  },
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
  const [saving, setSaving] = useState(false)
  const [testKind, setTestKind] = useState<ReactionKind | null>(null)
  const [testing, setTesting] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)
  const [testChannel, setTestChannel] = useState(directory.channels[0]?.id ?? '')
  const dirty = useMemo(() => comparable(draft) !== comparable(value), [draft, value])

  async function save() {
    const validation = validate(draft, directory)
    if (validation) {
      setNotice({ kind: 'error', text: validation })
      return
    }
    setSaving(true)
    setNotice(null)
    try {
      const result = await updateReactionSettings(draft)
      onSaved(result)
      setDraft(result)
      setNotice({ kind: 'success', text: 'Reakcie sú uložené a Carlo ich už používa.' })
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error, 'Reakcie sa nepodarilo uložiť.') })
    } finally {
      setSaving(false)
    }
  }

  async function sendTest() {
    if (!testKind || !testChannel || testing) return
    const emoji = emojiFor(draft, testKind)
    if (!emoji.emojiId && !emoji.unicode) {
      setTestError('Najprv vyberte dostupné emoji.')
      return
    }
    setTesting(true)
    setTestError(null)
    try {
      await testDiscordReaction(testKind, testChannel, {
        emoji_id: emoji.emojiId,
        emoji_unicode: emoji.unicode,
      })
      const channel = directory.channels.find((item) => item.id === testChannel)
      setTestKind(null)
      setNotice({
        kind: 'success',
        text: `Skúšobná správa s aktuálne zobrazeným emoji bola odoslaná do #${channel?.name ?? 'kanála'}.`,
      })
    } catch (error) {
      setTestError(errorMessage(error, 'Skúšobnú reakciu sa nepodarilo odoslať.'))
    } finally {
      setTesting(false)
    }
  }

  function updateEmoji(kind: ReactionKind, emoji: SelectedReactionEmoji) {
    if (kind === 'seen')
      setDraft({ ...draft, seen_emoji_id: emoji.emojiId, seen_emoji_unicode: emoji.unicode })
    if (kind === 'mention')
      setDraft({
        ...draft,
        mention_reaction_emoji_id: emoji.emojiId,
        mention_reaction_emoji_unicode: emoji.unicode,
      })
    if (kind === 'auto')
      setDraft({
        ...draft,
        auto_reaction_emoji_id: emoji.emojiId,
        auto_reaction_emoji_unicode: emoji.unicode,
      })
  }

  function setEnabled(kind: ReactionKind, enabled: boolean) {
    if (kind === 'seen') setDraft({ ...draft, seen_enabled: enabled })
    if (kind === 'mention') setDraft({ ...draft, mention_reaction_enabled: enabled })
    if (kind === 'auto') setDraft({ ...draft, auto_reaction_enabled: enabled })
  }

  const selectedTest = testKind ? ruleState(draft, testKind) : null
  const selectedChannel = directory.channels.find((channel) => channel.id === testChannel)

  return (
    <div className="reaction-workspace">
      <UnsavedChangesGuard active={dirty && !saving} />
      <div className="reaction-intro">
        <div>
          <p className="eyebrow">Tri jednoduché pravidlá</p>
          <h2>Čo má Carlo označiť emoji?</h2>
          <p>Každé pravidlo môžete samostatne zapnúť, upraviť a bezpečne vyskúšať.</p>
        </div>
        <span className={`reaction-save-status ${dirty ? 'is-dirty' : ''}`} role="status">
          {dirty ? 'Máte neuložené zmeny' : 'Všetky zmeny sú uložené'}
        </span>
      </div>

      <div className="reaction-rule-list">
        {(['seen', 'mention', 'auto'] as const).map((kind) => {
          const state = ruleState(draft, kind)
          const saved = ruleState(value, kind)
          return (
            <ReactionRule
              key={kind}
              kind={kind}
              enabled={state.enabled}
              emoji={state.emoji}
              emojis={directory.emojis}
              dirty={JSON.stringify(state) !== JSON.stringify(saved)}
              onEnabled={(enabled) => setEnabled(kind, enabled)}
              onEmoji={(emoji) => updateEmoji(kind, emoji)}
              onTest={() => {
                setTestError(null)
                setTestKind(kind)
              }}
            >
              {kind === 'auto' && (
                <ChannelMultiPicker
                  channels={directory.channels}
                  value={draft.auto_reaction_channel_ids}
                  onChange={(ids) => setDraft({ ...draft, auto_reaction_channel_ids: ids })}
                />
              )}
            </ReactionRule>
          )
        })}
      </div>

      {dirty && (
        <div className="reaction-save-bar is-dirty">
          <div>
            <TriangleAlert aria-hidden="true" />
            <span>
              <strong>Zmeny ešte nie sú uložené</strong>
              <small>Uložte ich, aby ich Carlo začal používať.</small>
            </span>
          </div>
          <div>
            <Button variant="ghost" disabled={saving} onClick={() => setDraft(value)}>
              <RotateCcw aria-hidden="true" /> Zahodiť zmeny
            </Button>
            <Button disabled={saving} onClick={() => void save()}>
              {saving ? (
                <LoaderCircle className="spin" aria-hidden="true" />
              ) : (
                <Save aria-hidden="true" />
              )}
              {saving ? 'Ukladám…' : 'Uložiť zmeny'}
            </Button>
          </div>
        </div>
      )}

      <Dialog
        open={testKind !== null}
        onOpenChange={(open) => {
          if (!open && !testing) setTestKind(null)
        }}
      >
        <DialogContent className="reaction-test-dialog">
          <DialogHeader>
            <div className="reaction-test-heading">
              {selectedTest && (
                <ReactionEmojiVisual
                  value={selectedTest.emoji}
                  emojis={directory.emojis}
                  className="large"
                />
              )}
              <div>
                <DialogTitle>
                  {testKind ? `Vyskúšať: ${ruleCopy[testKind].title}` : 'Vyskúšať reakciu'}
                </DialogTitle>
                <DialogDescription>
                  Test používa presne emoji, ktoré práve vidíte – aj keď zmeny ešte nie sú uložené.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <div className="reaction-test-body">
            <label htmlFor="reaction-test-channel">Kam poslať skúšobnú správu?</label>
            <select
              id="reaction-test-channel"
              value={testChannel}
              disabled={testing}
              onChange={(event) => setTestChannel(event.target.value)}
            >
              {directory.channels.map((channel) => (
                <option value={channel.id} key={channel.id}>
                  #{channel.name}
                </option>
              ))}
            </select>
            <div className="reaction-test-summary">
              <FlaskConical aria-hidden="true" />
              <p>
                Carlo pošle <strong>jednu označenú skúšobnú správu</strong> do{' '}
                <strong>#{selectedChannel?.name ?? 'vybraného kanála'}</strong> a pridá na ňu
                zvolené emoji. Nebude nikoho označovať.
              </p>
            </div>
            {testError && (
              <p className="form-alert" role="alert">
                {testError}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" disabled={testing} onClick={() => setTestKind(null)}>
              Zrušiť
            </Button>
            <Button disabled={!testChannel || testing} onClick={() => void sendTest()}>
              {testing ? (
                <LoaderCircle className="spin" aria-hidden="true" />
              ) : (
                <Send aria-hidden="true" />
              )}
              {testing ? 'Posielam…' : 'Poslať skúšobnú správu'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ReactionRule({
  kind,
  enabled,
  emoji,
  emojis,
  dirty,
  onEnabled,
  onEmoji,
  onTest,
  children,
}: {
  kind: ReactionKind
  enabled: boolean
  emoji: SelectedReactionEmoji
  emojis: DiscordDirectory['emojis']
  dirty: boolean
  onEnabled: (enabled: boolean) => void
  onEmoji: (emoji: SelectedReactionEmoji) => void
  onTest: () => void
  children?: ReactNode
}) {
  const unavailable = Boolean(
    emoji.emojiId && !emojis.some((item) => item.id === emoji.emojiId && item.available),
  )
  return (
    <article className={`reaction-rule ${enabled ? 'is-enabled' : 'is-disabled'}`}>
      <header className="reaction-rule-header">
        <div className="reaction-rule-icon" aria-hidden="true">
          <ReactionEmojiVisual value={emoji} emojis={emojis} />
        </div>
        <div className="reaction-rule-copy">
          <div>
            <h3>{ruleCopy[kind].title}</h3>
            <span className={`reaction-rule-state ${enabled ? 'enabled' : ''}`}>
              {enabled ? 'Zapnuté' : 'Vypnuté'}
            </span>
            {dirty && <span className="reaction-rule-dirty">Zmenené</span>}
          </div>
          <p>{ruleCopy[kind].description}</p>
        </div>
        <Switch
          checked={enabled}
          aria-label={`${enabled ? 'Vypnúť' : 'Zapnúť'}: ${ruleCopy[kind].title}`}
          onCheckedChange={onEnabled}
        />
      </header>
      <div className="reaction-rule-body">
        <ReactionEmojiPicker
          label={ruleCopy[kind].title}
          value={emoji}
          emojis={emojis}
          onChange={onEmoji}
        />
        {children}
      </div>
      <footer className="reaction-rule-footer">
        <span>
          {enabled
            ? `Carlo ju použije ${ruleCopy[kind].moment}.`
            : 'Pravidlo je vypnuté; uložené nastavenie zostane pripravené.'}
        </span>
        <Button
          variant="outline"
          disabled={!enabled || unavailable || (!emoji.emojiId && !emoji.unicode)}
          title={!enabled ? 'Najprv pravidlo zapnite.' : undefined}
          onClick={onTest}
        >
          <FlaskConical aria-hidden="true" /> Vyskúšať
        </Button>
      </footer>
    </article>
  )
}

function ruleState(value: ReactionSettings, kind: ReactionKind) {
  if (kind === 'seen')
    return {
      enabled: value.seen_enabled,
      emoji: { emojiId: value.seen_emoji_id, unicode: value.seen_emoji_unicode },
    }
  if (kind === 'mention')
    return {
      enabled: value.mention_reaction_enabled,
      emoji: {
        emojiId: value.mention_reaction_emoji_id,
        unicode: value.mention_reaction_emoji_unicode,
      },
    }
  return {
    enabled: value.auto_reaction_enabled,
    emoji: { emojiId: value.auto_reaction_emoji_id, unicode: value.auto_reaction_emoji_unicode },
    channels: value.auto_reaction_channel_ids,
  }
}

function emojiFor(value: ReactionSettings, kind: ReactionKind): SelectedReactionEmoji {
  return ruleState(value, kind).emoji
}

function comparable(value: ReactionSettings) {
  return JSON.stringify({
    seen_enabled: value.seen_enabled,
    seen_emoji_id: value.seen_emoji_id,
    seen_emoji_unicode: value.seen_emoji_unicode,
    mention_reaction_enabled: value.mention_reaction_enabled,
    mention_reaction_emoji_id: value.mention_reaction_emoji_id,
    mention_reaction_emoji_unicode: value.mention_reaction_emoji_unicode,
    auto_reaction_enabled: value.auto_reaction_enabled,
    auto_reaction_emoji_id: value.auto_reaction_emoji_id,
    auto_reaction_emoji_unicode: value.auto_reaction_emoji_unicode,
    auto_reaction_channel_ids: [...value.auto_reaction_channel_ids].sort(),
  })
}

function validate(value: ReactionSettings, directory: DiscordDirectory) {
  for (const kind of ['seen', 'mention', 'auto'] as const) {
    const state = ruleState(value, kind)
    if (state.enabled && !state.emoji.emojiId && !state.emoji.unicode)
      return `Pre pravidlo „${ruleCopy[kind].title}“ vyberte emoji.`
    if (
      state.enabled &&
      state.emoji.emojiId &&
      !directory.emojis.some((emoji) => emoji.id === state.emoji.emojiId && emoji.available)
    )
      return `Pre pravidlo „${ruleCopy[kind].title}“ vyberte dostupné emoji.`
  }
  if (value.auto_reaction_enabled && value.auto_reaction_channel_ids.length === 0)
    return 'Pre reakciu na nové správy vyberte aspoň jeden kanál.'
  return null
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}
