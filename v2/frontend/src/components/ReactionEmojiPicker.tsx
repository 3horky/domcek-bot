import { ChevronDown, SmilePlus, TriangleAlert } from 'lucide-react'
import EmojiPicker, { EmojiStyle, type EmojiClickData } from 'emoji-picker-react'
import { useMemo, useState } from 'react'

import type { DiscordDirectory } from '../api/client'
import { carloEmojiCategories, discordEmojiUrl } from '../lib/emoji'
import { Button } from './ui/button'
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover'

export interface SelectedReactionEmoji {
  emojiId: string | null
  unicode: string | null
}

export function ReactionEmojiPicker({
  label,
  value,
  emojis,
  onChange,
}: {
  label: string
  value: SelectedReactionEmoji
  emojis: DiscordDirectory['emojis']
  onChange: (value: SelectedReactionEmoji) => void
}) {
  const [open, setOpen] = useState(false)
  const selectedServerEmoji = emojis.find((emoji) => emoji.id === value.emojiId)
  const unavailable = Boolean(value.emojiId && !selectedServerEmoji?.available)
  const customEmojis = useMemo(
    () =>
      emojis
        .filter((emoji) => emoji.available)
        .map((emoji) => ({
          id: `discord-${emoji.id}`,
          names: [emoji.name, `:${emoji.name}:`, 'server'],
          imgUrl: discordEmojiUrl(emoji.id, emoji.animated),
        })),
    [emojis],
  )

  function choose(selected: EmojiClickData) {
    if (selected.isCustom) {
      const matched = emojis.find(
        (emoji) =>
          selected.unified === `discord-${emoji.id}` ||
          selected.imageUrl.includes(`/emojis/${emoji.id}.`),
      )
      if (matched) onChange({ emojiId: matched.id, unicode: null })
    } else {
      onChange({ emojiId: null, unicode: selected.emoji })
    }
    setOpen(false)
  }

  return (
    <div className="reaction-emoji-control">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              variant="outline"
              className="reaction-emoji-trigger"
              aria-label={`${label}: zmeniť emoji`}
            />
          }
        >
          <ReactionEmojiVisual value={value} emojis={emojis} />
          <span>
            <strong>{emojiName(value, emojis)}</strong>
            <small>Zmeniť emoji</small>
          </span>
          <ChevronDown aria-hidden="true" />
        </PopoverTrigger>
        <PopoverContent className="reaction-emoji-popover" align="start">
          <div className="reaction-emoji-popover-heading">
            <SmilePlus aria-hidden="true" />
            <div>
              <strong>Vyberte emoji</strong>
              <span>Vyhľadávanie zahŕňa bežné aj dostupné emoji servera.</span>
            </div>
          </div>
          <EmojiPicker
            autoFocusSearch
            width="100%"
            height={390}
            emojiStyle={EmojiStyle.NATIVE}
            searchPlaceholder="Hľadať emoji…"
            searchClearButtonLabel="Vyčistiť vyhľadávanie"
            categories={carloEmojiCategories}
            customEmojis={customEmojis}
            previewConfig={{ showPreview: false }}
            onEmojiClick={choose}
          />
        </PopoverContent>
      </Popover>
      {unavailable && (
        <p className="reaction-emoji-warning" role="alert">
          <TriangleAlert aria-hidden="true" /> Toto emoji už na serveri nie je dostupné. Vyberte
          nové.
        </p>
      )}
    </div>
  )
}

export function ReactionEmojiVisual({
  value,
  emojis,
  className = '',
}: {
  value: SelectedReactionEmoji
  emojis: DiscordDirectory['emojis']
  className?: string
}) {
  const serverEmoji = emojis.find((emoji) => emoji.id === value.emojiId)
  if (serverEmoji?.available) {
    return (
      <img
        className={`reaction-emoji-visual ${className}`}
        src={discordEmojiUrl(serverEmoji.id, serverEmoji.animated)}
        alt={`:${serverEmoji.name}:`}
      />
    )
  }
  return (
    <span
      className={`reaction-emoji-visual ${className}`}
      aria-label={value.unicode ?? 'Bez emoji'}
    >
      {value.unicode ?? <SmilePlus aria-hidden="true" />}
    </span>
  )
}

function emojiName(value: SelectedReactionEmoji, emojis: DiscordDirectory['emojis']) {
  const serverEmoji = emojis.find((emoji) => emoji.id === value.emojiId)
  if (serverEmoji) return `:${serverEmoji.name}:`
  if (value.emojiId) return 'Nedostupné emoji'
  return value.unicode ? 'Vybrané emoji' : 'Vyberte emoji'
}
