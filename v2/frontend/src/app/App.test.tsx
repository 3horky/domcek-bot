import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { App } from './App'

const session = {
  authenticated: true,
  user: {
    id: '123',
    username: 'admin',
    display_name: 'Domček Admin',
    avatar_url: null,
  },
  guild_id: '456',
  roles: ['admin'],
  capabilities: [
    'view_admin',
    'edit_content',
    'manage_settings',
    'manage_channels',
    'manage_roles',
    'reconcile_publication',
  ],
  expires_at: '2026-08-09T22:00:00+00:00',
}

const draftEvent = {
  kind: 'external_event' as const,
  source_id: 'event-1',
  title: 'Otvorený Domček',
  description: 'Príďte medzi nás.',
  included: true,
  exclusion_reason: null,
  display_time: '12.08. // 18:00–20:00',
  day_name: 'streda',
  day_emoji: 'https://example.test/day.png',
  is_all_day: false,
  source_title: 'Otvorený Domček',
  source_description: 'Text priamo z kalendára.',
  is_recurring: true,
  instance_override_version: 0,
  instance_public_title: null,
  instance_description_state: 'inherit',
  instance_public_description: null,
  inclusion_decision: 'auto',
  series_override_version: 0,
  series_public_title: null,
  series_description_state: 'inherit',
  series_public_description: null,
}

const draft = {
  composer_version: 'e4-v2',
  guild_id: 456,
  slot_key: 'slot',
  scheduled_for: '2026-08-10T18:00:00+00:00',
  scheduled_local: '2026-08-10T20:00:00+02:00',
  timezone: 'Europe/Bratislava',
  window_starts_at: '2026-08-10T18:00:00+00:00',
  window_ends_at: '2026-08-24T18:00:00+00:00',
  intro_text: 'Ahojte!',
  outro_text: null,
  editor_events: [draftEvent],
  public_items: [draftEvent],
  warnings: [],
  messages: [
    {
      position: 0,
      part_key: 'part-1',
      content: '@everyone Ahojte!',
      embeds: [
        {
          item_kind: 'external_event' as const,
          source_id: 'event-1',
          color: 0xd68910,
          title: 'Otvorený Domček',
          description: 'Príďte medzi nás.',
          author_name: 'streda',
          author_icon_url: null,
          link_url: null,
          thumbnail_url: null,
        },
        {
          item_kind: 'info' as const,
          source_id: 'info-1',
          color: 0xf9e79f,
          title: 'Praktické INFO',
          description: 'Dôležitá informácia.',
          author_name: null,
          author_icon_url: null,
          link_url: null,
          thumbnail_url: null,
        },
      ],
      allowed_mentions: ['everyone'],
      seen_target: true,
    },
  ],
}

const dashboardSummary = {
  automatic_publication_enabled: true,
  last_calendar_sync_at: '2026-08-09T18:00:00+00:00',
  pending_archive_count: 1,
  last_publication: null,
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.history.replaceState({}, '', '/')
  window.dispatchEvent(new PopStateEvent('popstate'))
})

describe('authenticated application shell', () => {
  test('shows Discord login when there is no valid session', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          code: 'authentication_required',
          detail: 'Vyžaduje sa prihlásenie.',
        }),
        { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
      ),
    )

    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'Oznamy pripravené bez ručnej roboty' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Prihlásiť cez Discord' })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/v1/auth/discord/login'),
    )
  })

  test('makes the nearest publication the dashboard focal point', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json(session))
      .mockResolvedValueOnce(Response.json(draft))

    render(<App />)

    expect(await screen.findByText('Najbližšie zverejnenie')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Obsah najbližšieho prehľadu' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Skontrolovať oznamy/ })).toHaveAttribute(
      'href',
      '/oznamy',
    )
    expect(screen.getByText('Domček Admin')).toBeInTheDocument()
  })

  test('renders the canonical event and Discord message in the editor', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/publication/dashboard') {
        return Promise.resolve(Response.json(dashboardSummary))
      }
      if (path === '/api/v1/manual-events' || path === '/api/v1/info-announcements') {
        return Promise.resolve(Response.json([]))
      }
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)

    fireEvent.click(await screen.findByRole('link', { name: /Redakčný pult/ }))
    expect(await screen.findByRole('heading', { name: 'Redakčný pult' })).toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Discord náhľad' })).toBeInTheDocument()
    expect(await screen.findAllByText('Otvorený Domček')).toHaveLength(2)
    expect(screen.getByText('@everyone')).toBeInTheDocument()
    expect(screen.getAllByText('Carlo')).toHaveLength(2)
    expect(screen.queryByText('Oznamy o dianí v Domčeku')).not.toBeInTheDocument()
    expect(document.querySelector('[data-embed-kind="external_event"]')).toHaveStyle({
      borderLeftColor: '#d68910',
    })
    expect(screen.getByText('Praktické INFO').closest('.discord-embed')).toHaveStyle({
      borderLeftColor: '#f9e79f',
    })
    expect(screen.getByLabelText('Na túto správu Carlo pridá seen reakciu')).toBeInTheDocument()
  })

  test('shows immutable publication history separately from audit', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path.includes('/api/v1/publication/recovery/')) {
        return Promise.resolve(Response.json({ run_id: 'run-1', state: 'succeeded_manual' }))
      }
      if (path.startsWith('/api/v1/publication/shadow-history')) {
        return Promise.resolve(Response.json([]))
      }
      if (path.startsWith('/api/v1/publication/history')) {
        return Promise.resolve(
          Response.json([
            {
              id: 'run-1',
              slot_key: 'slot-1',
              scheduled_for: '2026-08-10T18:00:00+00:00',
              mode: 'manual',
              initiated_by_user_id: '123',
              state: 'partially_published',
              attempt: 1,
              composer_version: 'e4-v2',
              intro_text: 'Ahojte!',
              intro_prompt_version: 'fallback-v1',
              intro_used_fallback: true,
              outro_text: null,
              warning_codes: [],
              started_at: '2026-08-10T17:59:00+00:00',
              completed_at: '2026-08-10T18:00:02+00:00',
              error_code: null,
              error_detail: null,
              items: [
                {
                  id: 'item-1',
                  kind: 'external_event',
                  position: 0,
                  title: 'Otvorený Domček',
                  description: 'Príďte medzi nás.',
                  display_time: '12.08. // 18:00',
                  day_emoji: null,
                  starts_at: null,
                  ends_at: null,
                  starts_on: null,
                  ends_on: null,
                  is_all_day: false,
                  link_url: null,
                  image_url: null,
                },
              ],
              messages: [
                {
                  id: 'message-1',
                  position: 0,
                  discord_channel_id: '700',
                  discord_message_id: null,
                  jump_url: null,
                  state: 'uncertain',
                  content: '@everyone Ahojte!',
                  embeds: [],
                  allowed_mentions: ['everyone'],
                  seen_target: true,
                  attempt_count: 1,
                  error_detail: 'Neistý výsledok',
                  reaction_error: null,
                  sent_at: null,
                },
              ],
            },
          ]),
        )
      }
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /História publikácií/ }))

    expect(await screen.findByRole('heading', { name: 'História publikácií' })).toBeInTheDocument()
    expect(await screen.findByText('Ručné publikovanie', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/položiek/)).toBeInTheDocument()
    expect(screen.getByText('Publikovanie potrebuje rozhodnutie Admina')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Discord ID správy 1'), {
      target: { value: '123456789012345678' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Prepojiť existujúcu správu' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/publication/recovery/run-1/link-existing',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            message_position: 0,
            discord_message_id: '123456789012345678',
          }),
        }),
      ),
    )
  })

  test('opens one unified settings workspace with live Discord choices', async () => {
    document.cookie = 'domcek_csrf=test-csrf'
    const createCalls: Array<Record<string, unknown>> = []
    const adminSettings = {
      publication: {
        guild_id: '456',
        timezone: 'Europe/Bratislava',
        publication_weekday: 0,
        publication_time: '20:00:00',
        automatic_publication_enabled: true,
        publish_google_descriptions: false,
        generated_intro_enabled: true,
        everyone_mention_enabled: true,
        allow_stale_calendar_cache: false,
        alert_calendar_sync_enabled: true,
        alert_publication_enabled: true,
        alert_channel_operations_enabled: true,
        alert_role_operations_enabled: true,
        alert_publication_reminder_enabled: false,
        admin_role_id: '900',
        team_mod_role_id: '901',
        publisher_role_id: '902',
        announcement_channel_id: '700',
        command_channel_id: null,
        moderator_channel_id: '701',
        projects_category_id: '800',
        archive_category_id: '801',
        closing_message: null,
        version: 1,
      },
      calendars: [],
      reactions: {
        guild_id: '456',
        seen_enabled: true,
        seen_emoji_id: null,
        seen_emoji_unicode: '✅',
        auto_reaction_enabled: false,
        auto_reaction_emoji_id: null,
        auto_reaction_emoji_unicode: null,
        mention_reaction_enabled: false,
        mention_reaction_emoji_id: null,
        mention_reaction_emoji_unicode: null,
        auto_reaction_channel_ids: [],
        version: 1,
      },
    }
    const directory = {
      channels: [
        {
          id: '700',
          name: 'oznamy',
          kind: 'text',
          category_id: '800',
          text_channel_count: 0,
          voice_channel_count: 0,
          can_create_project_channel: false,
          is_archive_category: false,
          is_default_project_category: false,
        },
        {
          id: '701',
          name: 'moderatori',
          kind: 'text',
          category_id: null,
          text_channel_count: 0,
          voice_channel_count: 0,
          can_create_project_channel: false,
          is_archive_category: false,
          is_default_project_category: false,
        },
      ],
      categories: [
        {
          id: '800',
          name: 'projekty',
          kind: 'category',
          category_id: null,
          text_channel_count: 2,
          voice_channel_count: 0,
          can_create_project_channel: true,
          is_archive_category: false,
          is_default_project_category: true,
        },
        {
          id: '801',
          name: 'archiv',
          kind: 'category',
          category_id: null,
          text_channel_count: 2,
          voice_channel_count: 0,
          can_create_project_channel: false,
          is_archive_category: true,
          is_default_project_category: false,
        },
      ],
      roles: [],
      emojis: [],
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/admin/settings') return Promise.resolve(Response.json(adminSettings))
      if (path === '/api/v1/admin/discord/directory') {
        return Promise.resolve(Response.json(directory))
      }
      if (path === '/api/v1/admin/archives') return Promise.resolve(Response.json([]))
      if (path === '/api/v1/admin/channels' && init?.method === 'POST') {
        createCalls.push(JSON.parse(String(init.body)) as Record<string, unknown>)
        if (createCalls.length === 1) {
          return Promise.resolve(
            Response.json(
              { detail: 'Dočasná chyba vytvorenia kanála.' },
              { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
            ),
          )
        }
        return Promise.resolve(
          Response.json({ id: '777', name: 'projekt', jump_url: 'https://discord.test/777' }),
        )
      }
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /Nastavenia/ }))

    expect(await screen.findByRole('tab', { name: /Publikovanie/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nastavenia' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Kalendáre/ })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /Kanály/ })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Oznamy')).toHaveValue('700')
    expect(screen.getByText('Pravidlá umiestnenia')).toBeInTheDocument()
    expect(screen.getByLabelText('Nové projektové kanály')).toHaveValue('800')
    expect(screen.getByLabelText('Archivované kanály')).toHaveValue('801')
    fireEvent.click(screen.getByRole('tab', { name: /Kalendáre/ }))
    expect(await screen.findByText('Zatiaľ nie je pripojený kalendár')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: /Kanály/ }))
    expect(await screen.findByRole('heading', { name: 'Kanály' })).toBeInTheDocument()
    expect(screen.queryByText('Pravidlá umiestnenia')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Vytvoriť nový kanál/ }))
    const channelDialog = screen.getByRole('dialog', { name: 'Vytvoriť nový kanál' })
    const channelName = within(channelDialog).getByLabelText('Názov')
    fireEvent.compositionStart(channelName)
    fireEvent.change(channelName, { target: { value: 'Z\u030cltý ' } })
    fireEvent.compositionEnd(channelName, { data: ' ' })
    expect(channelName).toHaveValue('žltý-')
    fireEvent.change(channelName, {
      target: { value: 'Môj Projekt!' },
    })
    expect(channelName).toHaveValue('môj-projekt-')
    expect(within(channelDialog).getByText('#🏠・môj-projekt')).toBeInTheDocument()
    fireEvent.click(within(channelDialog).getByRole('button', { name: /^Vytvoriť kanál/ }))
    expect(await screen.findByText('Dočasná chyba vytvorenia kanála.')).toBeInTheDocument()
    fireEvent.click(within(channelDialog).getByRole('button', { name: /^Vytvoriť kanál/ }))
    expect(await screen.findByText('Kanál #projekt bol vytvorený.')).toBeInTheDocument()
    expect(createCalls).toHaveLength(2)
    expect(createCalls[0]?.name).toBe('môj-projekt')
    expect(createCalls[0]?.idempotency_key).toBe(createCalls[1]?.idempotency_key)
  })

  test('edits a recurring event from this occurrence and refreshes the preview', async () => {
    document.cookie = 'domcek_csrf=test-csrf'
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/manual-events' || path === '/api/v1/info-announcements') {
        return Promise.resolve(Response.json([]))
      }
      if (path === '/api/v1/events/event-1/series-override') {
        return Promise.resolve(
          Response.json({
            public_title: 'Nový titulok',
            description_state: 'custom',
            public_description: 'Text priamo z kalendára.',
            version: 1,
          }),
        )
      }
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByText('Redakčný pult'))
    fireEvent.click(await screen.findByRole('button', { name: 'Upraviť Otvorený Domček' }))

    expect(screen.getByRole('dialog', { name: 'Otvorený Domček' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Redakčný popis/)).toHaveValue('Text priamo z kalendára.')
    fireEvent.click(screen.getByLabelText('Tento a všetky budúce'))
    fireEvent.change(screen.getByLabelText(/Titulok oznamu/), {
      target: { value: 'Nový titulok' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Uložiť pre sériu' }))

    expect(
      await screen.findByText('Zmena je uložená a Discord náhľad je aktuálny.'),
    ).toBeInTheDocument()
    const seriesCall = fetchMock.mock.calls.find(
      ([input]) => input === '/api/v1/events/event-1/series-override',
    )
    expect(seriesCall?.[1]).toMatchObject({
      method: 'PUT',
      body: JSON.stringify({
        expected_version: 0,
        public_title: 'Nový titulok',
        description_state: 'custom',
        public_description: 'Text priamo z kalendára.',
      }),
    })
    await waitFor(() =>
      expect((seriesCall?.[1]?.headers as Headers).get('X-CSRF-Token')).toBe('test-csrf'),
    )
  })

  test('creates an INFO announcement through the responsive content form', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, options) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/info-announcements' && options?.method === 'POST') {
        return Promise.resolve(
          Response.json({ id: 'info-1', version: 1, deleted_at: null }, { status: 201 }),
        )
      }
      if (path === '/api/v1/uploads/info-images' && options?.method === 'POST') {
        return Promise.resolve(
          Response.json(
            {
              image_url: 'http://localhost:8000/media/info/uploaded.webp',
              width: 800,
              height: 500,
              bytes: 12345,
            },
            { status: 201 },
          ),
        )
      }
      if (path === '/api/v1/info-announcements') return Promise.resolve(Response.json([]))
      if (path === '/api/v1/manual-events') return Promise.resolve(Response.json([]))
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /Redakčný pult/ }))
    expect(await screen.findByRole('heading', { name: 'Redakčný pult' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'INFO oznam' }))
    fireEvent.change(screen.getByLabelText('Názov'), { target: { value: 'Dôležité INFO' } })
    fireEvent.change(screen.getByLabelText(/Popis/), { target: { value: 'Praktický text.' } })
    fireEvent.change(screen.getByLabelText(/Nahrať obrázok/), {
      target: { files: [new File(['image'], 'info.png', { type: 'image/png' })] },
    })
    expect(await screen.findByText('Obrázok je pripravený')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Uložiť oznam' }))

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([input, options]) =>
            input === '/api/v1/info-announcements' && options?.method === 'POST',
        ),
      ).toBe(true),
    )
    const createCall = fetchMock.mock.calls.find(
      ([input, options]) => input === '/api/v1/info-announcements' && options?.method === 'POST',
    )
    expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
      title: 'Dôležité INFO',
      description: 'Praktický text.',
      active: true,
      image_url: 'http://localhost:8000/media/info/uploaded.webp',
    })
    const uploadCall = fetchMock.mock.calls.find(
      ([input, options]) => input === '/api/v1/uploads/info-images' && options?.method === 'POST',
    )
    expect(uploadCall?.[1]?.body).toBeInstanceOf(FormData)
    expect((uploadCall?.[1]?.headers as Headers).has('Content-Type')).toBe(false)
  })

  test('creates a one-day manual event without exposing exclusive end-date semantics', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, options) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/manual-events' && options?.method === 'POST') {
        return Promise.resolve(
          Response.json({ id: 'manual-1', version: 1, deleted_at: null }, { status: 201 }),
        )
      }
      if (path === '/api/v1/manual-events') return Promise.resolve(Response.json([]))
      if (path === '/api/v1/info-announcements') return Promise.resolve(Response.json([]))
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /Redakčný pult/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Manuálnu udalosť' }))
    fireEvent.change(screen.getByLabelText('Názov'), { target: { value: 'Mimoriadne stretnutie' } })
    fireEvent.click(screen.getByLabelText(/Celodenná udalosť/))
    fireEvent.change(screen.getByLabelText('Prvý deň'), { target: { value: '2026-08-20' } })
    fireEvent.click(screen.getByRole('button', { name: 'Uložiť udalosť' }))

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([input, options]) => input === '/api/v1/manual-events' && options?.method === 'POST',
        ),
      ).toBe(true),
    )
    const createCall = fetchMock.mock.calls.find(
      ([input, options]) => input === '/api/v1/manual-events' && options?.method === 'POST',
    )
    expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
      title: 'Mimoriadne stretnutie',
      is_all_day: true,
      starts_on: '2026-08-20',
      ends_on: null,
      starts_at: null,
    })
  })

  test('shows the full inclusive range of a multi-day all-day manual event', async () => {
    const manualEvent = {
      id: 'manual-week',
      guild_id: 456,
      title: 'Letný tábor',
      description: 'Program na celý týždeň.',
      is_all_day: true,
      starts_at: null,
      ends_at: null,
      starts_on: '2026-08-17',
      ends_on: '2026-08-24',
      timezone: 'Europe/Bratislava',
      active: true,
      version: 1,
      created_by: '123',
      updated_by: '123',
      created_at: '2026-08-09T18:00:00+00:00',
      updated_at: '2026-08-09T18:00:00+00:00',
      deleted_at: null,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path === '/api/v1/manual-events') return Promise.resolve(Response.json([manualEvent]))
      if (path === '/api/v1/info-announcements') return Promise.resolve(Response.json([]))
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /Redakčný pult/ }))
    fireEvent.click(await screen.findByText('Manuálne'))

    expect(await screen.findByText('Letný tábor')).toBeInTheDocument()
    expect(screen.getByText(/17\. 8\. 2026 – 23\. 8\. 2026/)).toBeInTheDocument()
  })

  test('shows a readable role-filtered audit timeline', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const path = String(input)
      if (path === '/api/v1/session') return Promise.resolve(Response.json(session))
      if (path.startsWith('/api/v1/audit')) {
        return Promise.resolve(
          Response.json([
            {
              id: 'audit-1',
              actor_user_id: '123',
              action: 'manual_event.created',
              object_type: 'manual_event',
              object_id: 'manual-1',
              before: null,
              after: { title: 'Mimoriadne stretnutie', active: true },
              result: 'succeeded',
              correlation_id: 'correlation-1',
              created_at: '2026-08-09T18:00:00+00:00',
            },
          ]),
        )
      }
      return Promise.resolve(Response.json(draft))
    })

    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: /Audit/ }))

    expect(await screen.findByRole('heading', { name: 'Audit' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Záznam bol vytvorený' })).toBeInTheDocument()
    expect(screen.getByText('Vznikol nový záznam.')).toBeInTheDocument()
    expect(screen.getByText('Úspešné')).toBeInTheDocument()
  })
})
