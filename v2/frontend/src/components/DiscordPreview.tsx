import { Hash } from 'lucide-react'

import type { PublicationDraft } from '../api/client'

const MONTH_COLORS: Record<number, { info: string; event: string }> = {
  1: { info: '#d6eaf8', event: '#21618c' },
  2: { info: '#ccd1d1', event: '#2e4053' },
  3: { info: '#ead1dc', event: '#8e44ad' },
  4: { info: '#fcf3cf', event: '#f4d03f' },
  5: { info: '#d5f5e3', event: '#27ae60' },
  6: { info: '#fdebd0', event: '#e67e22' },
  7: { info: '#fadbd8', event: '#c0392b' },
  8: { info: '#f9e79f', event: '#d68910' },
  9: { info: '#fcf3cf', event: '#b7950b' },
  10: { info: '#f6ddcc', event: '#ca6f1e' },
  11: { info: '#d5dbdb', event: '#566573' },
  12: { info: '#fbeee6', event: '#b03a2e' },
}

export function DiscordPreview({ draft }: { draft: PublicationDraft }) {
  return (
    <div className="discord-window" aria-label="Náhľad správ v Discord kanáli oznamy">
      <header className="discord-window-header">
        <Hash aria-hidden="true" />
        <strong>oznamy</strong>
      </header>
      <div className="discord-feed">
        {draft.messages.map((message) => (
          <article className="discord-message" key={message.part_key}>
            <div className="discord-avatar" aria-hidden="true">
              C
            </div>
            <div className="discord-message-body">
              <header className="discord-message-header">
                <strong>Carlo</strong>
                <span className="discord-app-badge">APP</span>
                <time>v deň zverejnenia</time>
              </header>
              {message.content && (
                <p className="discord-message-content">{withMention(message.content)}</p>
              )}
              {message.embeds.map((embed) => {
                const itemKind =
                  embed.item_kind ??
                  draft.public_items.find((item) => item.source_id === embed.source_id)?.kind ??
                  'external_event'
                return (
                  <div
                    className="discord-embed"
                    data-embed-kind={itemKind}
                    key={`${message.part_key}-${embed.source_id}`}
                    style={{
                      borderLeftColor: discordColor(
                        embed.color ?? fallbackEmbedColor(itemKind, draft.scheduled_local),
                      ),
                    }}
                  >
                    <div className="discord-embed-copy">
                      {embed.author_name && (
                        <div className="discord-embed-author">
                          {embed.author_icon_url && <img src={embed.author_icon_url} alt="" />}
                          <span>{embed.author_name}</span>
                        </div>
                      )}
                      {embed.link_url ? (
                        <a href={embed.link_url} target="_blank" rel="noreferrer">
                          {embed.title}
                        </a>
                      ) : (
                        <strong className="discord-embed-title">{embed.title}</strong>
                      )}
                      {embed.description && <p>{embed.description}</p>}
                    </div>
                    {embed.thumbnail_url && (
                      <img className="discord-embed-thumbnail" src={embed.thumbnail_url} alt="" />
                    )}
                  </div>
                )
              })}
              {message.seen_target && message.reaction_emoji && (
                <div
                  className="discord-reactions"
                  aria-label="Na túto správu Carlo pridá seen reakciu"
                >
                  <ReactionEmoji value={message.reaction_emoji} />
                  <strong>1</strong>
                </div>
              )}
            </div>
          </article>
        ))}
      </div>
      <div className="discord-composer" aria-hidden="true">
        Správa pre #oznamy
      </div>
    </div>
  )
}

function ReactionEmoji({ value }: { value: string }) {
  const custom = value.match(/^([^:]*):(\d+)$/)
  if (!custom) return <span aria-hidden="true">{value}</span>
  return (
    <img
      className="discord-reaction-emoji"
      src={`https://cdn.discordapp.com/emojis/${custom[2]}.webp?size=32`}
      alt=""
    />
  )
}

function fallbackEmbedColor(
  kind: 'external_event' | 'manual_event' | 'info',
  scheduledLocal: string,
) {
  const month = Number(scheduledLocal.slice(5, 7))
  const palette = MONTH_COLORS[month] ?? { info: '#dddddd', event: '#999999' }
  return Number.parseInt((kind === 'info' ? palette.info : palette.event).slice(1), 16)
}

function discordColor(value: number) {
  return `#${value.toString(16).padStart(6, '0')}`
}

function withMention(content: string) {
  const parts = content.split(/(@everyone)/g)
  return parts.map((part, index) =>
    part === '@everyone' ? (
      <span className="discord-mention" key={`${part}-${index}`}>
        {part}
      </span>
    ) : (
      part
    ),
  )
}
