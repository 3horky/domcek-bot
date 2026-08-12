import { expect, test, type Page, type Route } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

type Role = 'admin' | 'team_mod' | 'publisher' | 'none'

interface MockState {
  role: Role
  eventDescription: string
  includedStop: boolean
  manualEvents: Record<string, unknown>[]
  infoAnnouncements: Record<string, unknown>[]
  calls: Array<{ path: string; method: string; body: unknown }>
  published: boolean
  archives: Record<string, unknown>[]
  memberRoles: string[]
  extraEvents: number
  reactions: Record<string, unknown>
  publicationSettings: Record<string, unknown>
  calendars: Record<string, unknown>[]
  settingsFailureStatus: number | null
  settingsSaveFailureStatus: number | null
  memberSearchFailureStatus: number | null
  roleMutationFailure: 'last_admin' | 'discord_unavailable' | null
}

const normalEvent = {
  kind: 'external_event',
  source_id: 'event-1',
  title: 'Otvorený Domček',
  description: 'Príďte medzi nás.',
  included: true,
  exclusion_reason: null,
  display_time: '12.08. // 18:00–20:00',
  day_name: 'streda',
  day_emoji: null,
  is_all_day: false,
  source_title: 'Otvorený Domček',
  source_description: 'Text priamo z Google kalendára.',
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

const stopEvent = {
  ...normalEvent,
  source_id: 'event-stop',
  title: 'Interná porada',
  source_title: 'Interná porada',
  description: null,
  source_description: 'stop carlo',
  included: false,
  exclusion_reason: 'source_stop_phrase',
  is_recurring: false,
}

function capabilities(role: Role) {
  if (role === 'admin')
    return [
      'view_admin',
      'edit_content',
      'force_inclusion',
      'manual_publish',
      'manage_channels',
      'approve_archive',
      'manage_settings',
      'manage_roles',
      'view_full_audit',
    ]
  if (role === 'team_mod') return ['view_admin', 'edit_content', 'manage_channels']
  if (role === 'publisher') return ['view_admin', 'manual_publish']
  return []
}

async function mockCarlo(page: Page, role: Role = 'admin'): Promise<MockState> {
  const state: MockState = {
    role,
    eventDescription: 'Príďte medzi nás.',
    includedStop: false,
    manualEvents: [],
    infoAnnouncements: [],
    calls: [],
    published: false,
    archives: [],
    memberRoles: [],
    extraEvents: 0,
    reactions: defaultReactionSettings(),
    publicationSettings: defaultPublicationSettings(),
    calendars: [],
    settingsFailureStatus: null,
    settingsSaveFailureStatus: null,
    memberSearchFailureStatus: null,
    roleMutationFailure: null,
  }
  await page
    .context()
    .addCookies([{ name: 'domcek_csrf', value: 'e2e-csrf', url: 'http://127.0.0.1:4174' }])
  await page.route('https://cdn.discordapp.com/emojis/**', (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="28" fill="#2f7552"/></svg>',
    }),
  )
  await page.route('https://cdn.discordapp.com/avatars/**', (route) =>
    route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="32" fill="#e4f1e9"/><circle cx="32" cy="24" r="11" fill="#2f7552"/><path d="M13 56c3-14 12-20 19-20s16 6 19 20" fill="#2f7552"/></svg>',
    }),
  )
  await page.route('**/api/v1/**', async (route) => handleApi(route, state))
  return state
}

async function handleApi(route: Route, state: MockState) {
  const role = state.role
  const request = route.request()
  const path = new URL(request.url()).pathname
  const method = request.method()
  const contentType = request.headers()['content-type'] ?? ''
  const body = contentType.includes('application/json') ? request.postDataJSON() : null
  state.calls.push({ path, method, body })
  const json = (value: unknown, status = 200) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) })

  if (path === '/api/v1/session') {
    if (role === 'none') return json({ code: 'authentication_required' }, 401)
    return json({
      authenticated: true,
      user: { id: '123', username: role, display_name: roleLabel(role), avatar_url: null },
      guild_id: '456',
      roles: [role],
      capabilities: capabilities(role),
      expires_at: '2026-08-11T12:00:00Z',
    })
  }
  if (role === 'none') return json({ code: 'authentication_required' }, 401)
  if (path === '/api/v1/publication/draft') return json(draft(state))
  if (path === '/api/v1/publication/dashboard')
    return json({
      automatic_publication_enabled: true,
      last_calendar_sync_at: '2026-08-10T18:00:00Z',
      pending_archive_count: state.archives.length,
      last_publication: state.published
        ? {
            id: 'run-1',
            scheduled_for: '2026-08-10T18:00:00Z',
            completed_at: '2026-08-10T18:01:00Z',
            state: 'succeeded_manual',
            mode: 'manual',
          }
        : null,
    })
  if (path === '/api/v1/manual-events' && method === 'GET') return json(state.manualEvents)
  if (path === '/api/v1/manual-events' && method === 'POST') {
    const values = body as Record<string, unknown>
    const record = {
      id: 'manual-1',
      guild_id: '456',
      title: values.title,
      description: values.description ?? null,
      is_all_day: values.is_all_day,
      starts_at: values.starts_at ?? null,
      ends_at: values.ends_at ?? null,
      starts_on: values.starts_on ?? null,
      ends_on: values.ends_on ?? null,
      timezone: 'Europe/Bratislava',
      link_url: null,
      active: true,
      deleted_at: null,
      version: 1,
    }
    state.manualEvents = [record]
    return json(record, 201)
  }
  if (path === '/api/v1/info-announcements' && method === 'GET')
    return json(state.infoAnnouncements)
  if (path === '/api/v1/info-announcements' && method === 'POST') {
    const values = body as Record<string, unknown>
    const record = {
      id: 'info-1',
      guild_id: '456',
      title: values.title,
      description: values.description,
      valid_from: values.valid_from,
      valid_until: values.valid_until,
      link_url: null,
      image_url: values.image_url ?? null,
      active: true,
      deleted_at: null,
      version: 1,
    }
    state.infoAnnouncements = [record]
    return json(record, 201)
  }
  if (path === '/api/v1/uploads/info-images')
    return json({ image_url: '/media/info/e2e.webp', width: 320, height: 180 }, 201)
  if (path.includes('/override') || path.includes('/series-override')) {
    const values = body as Record<string, unknown>
    if (path.includes('event-stop'))
      state.includedStop = values.inclusion_decision === 'force_include'
    else if (values.public_description) state.eventDescription = String(values.public_description)
    return json({ version: 1 })
  }
  if (path === '/api/v1/publication/manual/preview') {
    if (!capabilities(role).includes('manual_publish')) return json({ code: 'forbidden' }, 403)
    return json({
      confirmation_token: 'confirmation',
      scheduled_for: '2026-08-10T18:00:00Z',
      slot_key: 'slot-1',
      announcement_count: draft(state).public_items.length,
      message_count: 1,
      draft: draft(state),
    })
  }
  if (path === '/api/v1/publication/manual/confirm') {
    if (!capabilities(role).includes('manual_publish')) return json({ code: 'forbidden' }, 403)
    state.published = true
    return json({ run_id: 'run-1', state: 'succeeded_manual', slot_key: 'slot-1' })
  }
  if (path === '/api/v1/admin/settings') {
    const sourcePage = new URL(request.headers()['referer'] ?? 'http://localhost/').pathname
    if (!capabilities(role).includes('manage_settings'))
      return json(
        {
          detail:
            sourcePage === '/roly'
              ? 'Roly môže spravovať iba Admin.'
              : sourcePage === '/nastavenia'
                ? 'Nastavenia môže spravovať iba Admin.'
                : 'Na správu reakcií nemáte oprávnenie.',
        },
        403,
      )
    if (state.settingsFailureStatus)
      return json(
        {
          detail:
            sourcePage === '/roly'
              ? 'Oprávnenia sa teraz nedajú načítať.'
              : sourcePage === '/nastavenia'
                ? 'Nastavenia sa teraz nedajú načítať.'
                : 'Nastavenia reakcií sa teraz nedajú načítať.',
        },
        state.settingsFailureStatus,
      )
    return json(adminSettings(state))
  }
  if (path === '/api/v1/admin/settings/publication' && method === 'PUT') {
    if (!capabilities(state.role).includes('manage_settings'))
      return json({ detail: 'Nastavenia môže spravovať iba Admin.', code: 'forbidden' }, 403)
    if (state.settingsSaveFailureStatus)
      return json(
        {
          detail:
            state.settingsSaveFailureStatus === 409
              ? 'Nastavenia boli medzitým zmenené.'
              : 'Nastavenia sa nepodarilo uložiť.',
          code: state.settingsSaveFailureStatus === 409 ? 'conflict' : 'settings_unavailable',
        },
        state.settingsSaveFailureStatus,
      )
    const values = { ...(body as Record<string, unknown>) }
    delete values.expected_version
    state.publicationSettings = {
      ...values,
      everyone_mention_enabled: true,
      version: Number(state.publicationSettings.version) + 1,
    }
    return json(state.publicationSettings)
  }
  if (path === '/api/v1/admin/settings/reactions' && method === 'PUT') {
    const values = body as Record<string, unknown>
    state.reactions = { ...values, guild_id: '456', version: Number(values.expected_version) + 1 }
    delete state.reactions.expected_version
    return json(state.reactions)
  }
  if (path === '/api/v1/admin/calendars' && method === 'POST') {
    const values = body as Record<string, unknown>
    const calendar = mockCalendar({
      id: `calendar-${state.calendars.length + 1}`,
      display_name: String(values.display_name),
      external_calendar_id: String(values.external_calendar_id),
      priority: Number(values.priority),
    })
    state.calendars = [...state.calendars, calendar]
    return json(calendar, 201)
  }
  const calendarMatch = path.match(/^\/api\/v1\/admin\/calendars\/([^/]+)$/)
  if (calendarMatch && method === 'PUT') {
    const values = body as Record<string, unknown>
    const current = state.calendars.find((item) => item.id === calendarMatch[1])
    const updated: Record<string, unknown> = {
      ...current,
      ...values,
      version: Number(current?.version ?? 1) + 1,
    }
    delete updated.expected_version
    state.calendars = state.calendars.map((item) => (item.id === calendarMatch[1] ? updated : item))
    return json(updated)
  }
  if (path.match(/^\/api\/v1\/admin\/calendars\/[^/]+\/sync$/) && method === 'POST')
    return json({ received: 12, created: 2, updated: 3 })
  if (path === '/api/v1/admin/discord/reactions/test' && method === 'POST')
    return json({ message_id: 'reaction-test-message' })
  if (path === '/api/v1/admin/discord/directory') return json(directory())
  if (path === '/api/v1/admin/archives' && method === 'GET') return json(state.archives)
  if (path === '/api/v1/admin/archives' && method === 'POST') {
    const record = archiveRecord()
    state.archives = [record]
    return json(record, 201)
  }
  if (path.includes('/api/v1/admin/archives/') && path.endsWith('/decision')) {
    state.archives = []
    return json({ ...archiveRecord(), state: 'executed' })
  }
  if (path === '/api/v1/admin/channels' && method === 'POST')
    return json(
      { channel_id: '777', name: 'e2e-projekt', jump_url: 'https://discord.test/777' },
      201,
    )
  if (path === '/api/v1/admin/discord/members') {
    if (state.memberSearchFailureStatus)
      return json({ detail: 'Ľudí sa teraz nepodarilo vyhľadať.' }, state.memberSearchFailureStatus)
    const query = new URL(request.url()).searchParams.get('query')?.toLocaleLowerCase('sk') ?? ''
    if (query.includes('pomaly')) await new Promise((resolve) => setTimeout(resolve, 650))
    if (query.includes('mart'))
      return json([
        {
          id: '999',
          username: 'martina.z',
          display_name: 'Martina Živčáková-Hrušková',
          avatar_url: 'https://cdn.discordapp.com/avatars/999/test.png',
          role_ids: state.memberRoles,
        },
        {
          id: '998',
          username: 'martina_90',
          display_name: 'Martina Živčáková',
          avatar_url: null,
          role_ids: [],
        },
      ])
    return json([
      {
        id: '999',
        username: 'tester',
        display_name: 'Testovací člen',
        avatar_url: null,
        role_ids: state.memberRoles,
      },
    ])
  }
  if (path === '/api/v1/admin/discord/roles' && method === 'PUT') {
    if (!capabilities(state.role).includes('manage_roles'))
      return json({ detail: 'Roly môže spravovať iba Admin.', code: 'forbidden' }, 403)
    if (state.roleMutationFailure === 'last_admin')
      return json(
        {
          detail: 'Najprv udeľte Admin oprávnenie ďalšiemu členovi.',
          code: 'last_admin',
        },
        409,
      )
    if (state.roleMutationFailure === 'discord_unavailable')
      return json(
        {
          detail: 'Skontrolujte oprávnenia Carla a skúste operáciu znova.',
          code: 'discord_unavailable',
        },
        502,
      )
    const values = body as Record<string, unknown>
    const roleId = values.role === 'admin' ? '900' : '901'
    state.memberRoles = values.enabled
      ? [...new Set([...state.memberRoles, roleId])]
      : state.memberRoles.filter((id) => id !== roleId)
    return json({
      id: String(values.member_id),
      username: values.member_id === '999' ? 'martina.z' : 'martina_90',
      display_name: values.member_id === '999' ? 'Martina Živčáková-Hrušková' : 'Martina Živčáková',
      avatar_url:
        values.member_id === '999' ? 'https://cdn.discordapp.com/avatars/999/test.png' : null,
      role_ids: state.memberRoles,
    })
  }
  if (path === '/api/v1/publication/history' || path === '/api/v1/publication/shadow-history')
    return json([])
  if (path === '/api/v1/audit') return json([])
  if (path === '/api/v1/operations/summary') return json({ processes: [], calendars: [] })
  return json({})
}

function draft(state: MockState) {
  const editorEvents = [
    { ...normalEvent, description: state.eventDescription },
    { ...stopEvent, included: state.includedStop },
  ]
  for (let index = 0; index < state.extraEvents; index += 1) {
    editorEvents.push({
      ...normalEvent,
      source_id: `event-extra-${index}`,
      title: `Programová udalosť ${index + 1}`,
      source_title: `Programová udalosť ${index + 1}`,
      description: `Redakčný popis ${index + 1}`,
      is_recurring: false,
    })
  }
  const publicItems: Record<string, unknown>[] = [editorEvents[0]]
  publicItems.push(...editorEvents.slice(2))
  if (state.includedStop) publicItems.push(editorEvents[1])
  for (const item of state.manualEvents) {
    publicItems.push({
      kind: 'manual_event',
      source_id: item.id,
      title: item.title,
      description: item.description,
      included: true,
      display_time: '15.–21.08. // celý deň',
      is_all_day: true,
    })
  }
  for (const item of state.infoAnnouncements) {
    publicItems.push({
      kind: 'info',
      source_id: item.id,
      title: item.title,
      description: item.description,
      included: true,
      display_time: null,
      is_all_day: null,
    })
  }
  return {
    composer_version: 'e4-v2',
    guild_id: 456,
    slot_key: 'slot-1',
    scheduled_for: '2026-08-10T18:00:00Z',
    scheduled_local: '2026-08-10T20:00:00+02:00',
    timezone: 'Europe/Bratislava',
    window_starts_at: '2026-08-10T18:00:00Z',
    window_ends_at: '2026-08-24T18:00:00Z',
    intro_text: 'Ahojte!',
    outro_text: null,
    editor_events: editorEvents,
    public_items: publicItems,
    warnings: [],
    messages: [
      {
        position: 0,
        part_key: 'part-1',
        content: '@everyone Ahojte!',
        embeds: publicItems.map((item) => ({
          item_kind: item.kind,
          source_id: item.source_id,
          color: item.kind === 'info' ? 0xf9e79f : 0xd68910,
          title: item.title,
          description: item.description,
          author_name: item.kind === 'info' ? null : 'streda',
          author_icon_url: null,
          link_url: null,
          thumbnail_url: null,
        })),
        allowed_mentions: ['everyone'],
        seen_target: true,
      },
    ],
  }
}

function adminSettings(state: MockState) {
  return {
    publication: state.publicationSettings,
    calendars: state.calendars,
    reactions: state.reactions,
  }
}

function defaultPublicationSettings() {
  return {
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
    command_channel_id: '701',
    moderator_channel_id: '701',
    projects_category_id: '800',
    archive_category_id: '801',
    closing_message: null,
    version: 1,
  }
}

function defaultReactionSettings() {
  return {
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
  }
}

function mockCalendar(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    id: 'calendar-1',
    guild_id: '456',
    external_calendar_id: 'program@example.test',
    display_name: 'Program Domčeka',
    priority: 10,
    active: true,
    sync_status: 'succeeded',
    last_sync_attempt_at: '2026-08-12T18:00:00Z',
    last_sync_success_at: '2026-08-12T18:00:00Z',
    last_full_sync_at: '2026-08-12T18:00:00Z',
    last_sync_error: null,
    version: 1,
    ...overrides,
  }
}

function directory() {
  return {
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
        text_channel_count: 4,
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
        text_channel_count: 8,
        voice_channel_count: 0,
        can_create_project_channel: false,
        is_archive_category: true,
        is_default_project_category: false,
      },
      {
        id: '803',
        name: 'workshopy',
        kind: 'category',
        category_id: null,
        text_channel_count: 3,
        voice_channel_count: 0,
        can_create_project_channel: true,
        is_archive_category: false,
        is_default_project_category: false,
      },
      {
        id: '802',
        name: 'voice',
        kind: 'category',
        category_id: null,
        text_channel_count: 0,
        voice_channel_count: 3,
        can_create_project_channel: false,
        is_archive_category: false,
        is_default_project_category: false,
      },
    ],
    roles: [{ id: '901', name: 'Team Mod', position: 2, managed: false }],
    emojis: [
      { id: '990', name: 'seen', animated: false, available: true },
      { id: '991', name: 'old', animated: false, available: false },
    ],
  }
}

function archiveRecord() {
  return {
    id: 'archive-1',
    guild_id: '456',
    discord_channel_id: '700',
    archive_category_id: '801',
    original_channel_name: 'oznamy',
    reason: 'Projekt skončil',
    state: 'pending',
    requested_by_user_id: '123',
    expires_at: '2026-08-12T12:00:00Z',
    decided_by_user_id: null,
    decided_at: null,
    discord_approval_message_id: null,
  }
}

function roleLabel(role: Role) {
  if (role === 'admin') return 'Domček Admin'
  if (role === 'team_mod') return 'Team Mod Tester'
  if (role === 'publisher') return 'SDB / FMA Tester'
  return 'Člen'
}

test('01 Admin sa prihlási a otvorí najbližší balík', async ({ page }) => {
  await mockCarlo(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Prehľad', exact: true })).toBeVisible()
  await page.getByRole('link', { name: /Skontrolovať oznamy/ }).click()
  await expect(page.getByRole('heading', { name: 'Redakčný pult' })).toBeVisible()
})

test('02 Team Mod upraví popis kalendárovej udalosti', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  await page.goto('/oznamy')
  await page.getByRole('button', { name: 'Upraviť Otvorený Domček' }).click()
  await page.getByRole('textbox', { name: /Redakčný popis/ }).fill('Nový redakčný text')
  await page.getByRole('button', { name: 'Uložiť zmenu' }).click()
  await expect(page.getByText('Nový redakčný text').first()).toBeVisible()
  expect(state.eventDescription).toBe('Nový redakčný text')
})

test('03 úprava zostane po opätovnom načítaní dát', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  state.eventDescription = 'Trvalá úprava po syncu'
  await page.goto('/oznamy')
  await page.getByRole('button', { name: /Načítať aktuálne údaje/ }).click()
  await expect(page.getByText('Trvalá úprava po syncu').first()).toBeVisible()
})

test('04 rovnaká udalosť používa úpravu aj pri ďalšom týždennom náhľade', async ({ page }) => {
  const state = await mockCarlo(page)
  state.eventDescription = 'Text zdieľaný do ďalšieho týždňa'
  await page.goto('/oznamy')
  await page.reload()
  await expect(page.getByText('Text zdieľaný do ďalšieho týždňa').first()).toBeVisible()
})

test('05 používateľ vytvorí viacdňovú manuálnu udalosť', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  await page.goto('/oznamy')
  await page.getByRole('button', { name: 'Manuálnu udalosť' }).click()
  await page.getByLabel('Názov').fill('Letný tábor')
  await page.getByText('Celodenná udalosť', { exact: true }).click()
  await page.getByLabel('Prvý deň').fill('2026-08-15')
  await page.getByLabel('Posledný deň').fill('2026-08-21')
  await page.getByRole('button', { name: 'Uložiť udalosť' }).click()
  await expect(page.getByText('Letný tábor').first()).toBeVisible()
  expect(state.manualEvents).toHaveLength(1)
})

test('06 používateľ vytvorí INFO oznam s inkluzívnou expiráciou', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  await page.goto('/oznamy')
  await page.getByRole('button', { name: 'INFO oznam' }).click()
  await page.getByLabel('Názov').fill('Dôležité INFO')
  await page.getByLabel('Popis').fill('Platí vrátane posledného dňa.')
  await page.getByLabel('Platí od').fill('2026-08-10')
  await page.getByLabel('Platí do').fill('2026-08-20')
  await page.getByRole('button', { name: 'Uložiť oznam' }).click()
  await expect(page.getByText('Dôležité INFO').first()).toBeVisible()
  expect(state.infoAnnouncements[0]?.valid_until).toBe('2026-08-20')
})

test('07 Admin ručne publikuje dvojkrokovo a dvojklik nevytvorí druhý účinok', async ({ page }) => {
  const state = await mockCarlo(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Pripraviť ručné zverejnenie' }).click()
  await page.getByRole('button', { name: 'Potvrdiť a zverejniť' }).dblclick()
  await expect(page.getByText(/Publikovanie skončilo stavom succeeded_manual/)).toBeVisible()
  expect(state.published).toBe(true)
  expect(
    state.calls.filter((call) => call.path === '/api/v1/publication/manual/confirm'),
  ).toHaveLength(1)
})

test('08 Admin vytvorí súkromný kanál', async ({ page }) => {
  test.setTimeout(60_000)
  const state = await mockCarlo(page)
  await page.goto('/kanaly')
  await expect(page.getByRole('heading', { name: 'Kanály', exact: true })).toBeVisible({
    timeout: 15_000,
  })
  await expect(page.getByText('Pravidlá umiestnenia')).toHaveCount(0)
  const opener = page.getByRole('button', { name: /Vytvoriť nový kanál/ })
  await opener.click()
  let dialog = page.getByRole('dialog', { name: 'Vytvoriť nový kanál' })
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(opener).toBeFocused()
  await expect(page.getByRole('link', { name: 'Preskočiť na obsah' })).not.toBeFocused()
  await opener.click()
  dialog = page.getByRole('dialog', { name: 'Vytvoriť nový kanál' })
  const locationControl = dialog.locator('details').filter({ hasText: 'Zmeniť umiestnenie' })
  await expect(locationControl.locator('summary svg')).toHaveCount(2)
  await expect(dialog.getByText('Carlo ho zaradí do časti „projekty“.')).toBeVisible()
  await dialog.getByText('Zmeniť umiestnenie').click()
  await dialog.getByLabel('Časť servera').selectOption('803')
  await expect(dialog.getByText('Kanál bude zaradený do časti „workshopy“.')).toBeVisible()

  const nameInput = dialog.getByLabel('Názov')
  await nameInput.fill('Letný Tábor 2026!')
  await expect(nameInput).toHaveValue('letný-tábor-2026-')
  await expect(dialog.getByText('#⛺・letný-tábor-2026')).toBeVisible()
  await dialog.getByRole('button', { name: 'Otvoriť všetky emoji' }).click()
  const emojiSearch = page.getByPlaceholder('Hľadať emoji…')
  await expect(emojiSearch).toBeFocused()
  await emojiSearch.fill('camera')
  await page.locator('button[data-unified="1f4f7"]').click()
  await expect(dialog.getByText(/#📷・letný-tábor-2026/)).toBeVisible()

  const leaderPicker = dialog.locator('.discord-picker').filter({
    hasText: 'Kto bude kanál viesť?',
  })
  const leaderSearch = leaderPicker.getByRole('combobox', { name: 'Kto bude kanál viesť?' })
  await leaderSearch.fill('tester')
  await leaderPicker.getByRole('option', { name: /Testovací člen/ }).click()
  await expect(leaderSearch).toHaveValue('')
  await expect(leaderSearch).toBeFocused()
  await expect(leaderPicker.getByRole('option')).toHaveCount(0)
  await leaderPicker.getByRole('button', { name: /Testovací člen/ }).click()
  await expect(leaderSearch).toBeFocused()

  const memberSearch = dialog.getByRole('combobox', { name: 'Koho chcete pridať?' })
  await memberSearch.fill('tester')
  await dialog.getByRole('option', { name: /Testovací člen/ }).click()
  await expect(memberSearch).toHaveValue('')
  await expect(memberSearch).toBeFocused()
  await expect(dialog.getByRole('option', { name: /Testovací člen/ })).toHaveCount(0)
  const groupControl = dialog.locator('details').filter({ hasText: 'Pridať celú skupinu' })
  await expect(groupControl.locator('summary svg')).toHaveCount(2)
  await dialog.getByText('Pridať celú skupinu').click()
  const rolePicker = dialog.locator('.role-picker')
  await rolePicker.getByRole('option', { name: /Team Mod/ }).click()
  await expect(dialog.getByText('1 vybratá')).toBeVisible()
  await expect(rolePicker.getByRole('button', { name: 'Team Mod' })).toBeVisible()
  await dialog.getByText('Pridať celú skupinu').click()
  await expect(dialog.getByText('1 vybratá')).toBeVisible()
  await expect(rolePicker).not.toBeVisible()
  await dialog.getByText('Pridať celú skupinu').click()
  await rolePicker.getByRole('button', { name: 'Zrušiť výber' }).click()
  await expect(
    rolePicker.getByText('Žiadna skupina – prístup dostanú iba vybraní ľudia.'),
  ).toBeVisible()
  await nameInput.fill('e2e-projekt')
  await dialog.getByRole('button', { name: 'Vytvoriť kanál' }).click()
  await expect(page.getByText(/Kanál #e2e-projekt bol vytvorený/)).toBeVisible()
  expect(state.calls.some((call) => call.path === '/api/v1/admin/channels')).toBe(true)
  const createCall = state.calls.find((call) => call.path === '/api/v1/admin/channels')
  expect((createCall?.body as Record<string, unknown>).member_ids).toEqual(['999'])
  expect((createCall?.body as Record<string, unknown>).role_ids).toEqual([])
  expect((createCall?.body as Record<string, unknown>).category_id).toBe('803')
})

test('09 Team Mod požiada o archiváciu a Admin schváli konkrétnu žiadosť', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  await page.goto('/kanaly')
  await page.getByRole('button', { name: /Archivovať kanál/ }).click()
  const dialog = page.getByRole('dialog', { name: 'Archivovať kanál' })
  await dialog.getByLabel('Ktorý kanál chcete archivovať?').selectOption('700')
  await dialog.getByLabel('Prečo sa kanál archivuje?').fill('Projekt skončil')
  await dialog.getByRole('button', { name: 'Odoslať žiadosť' }).click()
  await expect(page.getByText('Žiadosť čaká na rozhodnutie Admina.')).toBeVisible()
  expect(state.archives).toHaveLength(1)

  state.role = 'admin'
  await page.reload()
  await page.getByRole('button', { name: 'Schváliť' }).click()
  await page.getByRole('button', { name: 'Potvrdiť' }).click()
  await expect(page.getByText('Kanál bol archivovaný.')).toBeVisible()
  expect(state.archives).toHaveLength(0)
})

test('10 Admin klávesnicou vyberie človeka a bezpečne zmení obe roly', async ({
  page,
}, testInfo) => {
  const state = await mockCarlo(page)
  await page.goto('/roly')
  const search = page.getByRole('combobox', { name: 'Koho chcete spravovať?' })
  await search.fill('mart')
  await expect(page.getByRole('option')).toHaveCount(2)
  await search.press('Enter')
  await expect(page.getByRole('heading', { name: 'Martina Živčáková-Hrušková' })).toBeFocused()
  const selectedStateAxe = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(
    selectedStateAxe.violations.map((violation) => violation.id),
    'Vybraný človek musí zostať bez automaticky zistiteľného WCAG A/AA porušenia.',
  ).toEqual([])
  if (process.env.CARLO_VISUAL_AUDIT_DIR) {
    await page.screenshot({
      path: `${process.env.CARLO_VISUAL_AUDIT_DIR}/roly--selected--${testInfo.project.name}.png`,
      fullPage: true,
    })
  }

  await page.getByRole('button', { name: 'Udeliť Team Mod' }).click()
  const grantDialog = page.getByRole('alertdialog')
  const grantTeam = grantDialog.getByRole('button', { name: 'Udeliť Team Mod', exact: true })
  await expect(grantDialog).toContainText('Martina Živčáková-Hrušková')
  await grantTeam.dblclick()
  await expect(page.getByText(/Team Mod oprávnenie bolo udelené človeku Martina/)).toBeVisible()
  expect(state.memberRoles).toEqual(['901'])
  expect(state.calls.filter((call) => call.path === '/api/v1/admin/discord/roles')).toHaveLength(1)

  await page.getByRole('button', { name: 'Udeliť Admin' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Udeliť Admin' }).click()
  await expect(page.getByText(/Admin oprávnenie bolo udelené človeku Martina/)).toBeVisible()
  expect(state.memberRoles).toEqual(['901', '900'])

  await page.getByRole('button', { name: 'Odobrať Team Mod' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Odobrať Team Mod' }).click()
  await expect(page.getByText(/Team Mod oprávnenie bolo odobrané človeku Martina/)).toBeVisible()
  expect(state.memberRoles).toEqual(['900'])

  await page.getByRole('button', { name: 'Odobrať Admin' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('stratí prístup k nastaveniam')
  await page.getByRole('alertdialog').getByRole('button', { name: 'Odobrať Admin' }).click()
  await expect(page.getByText(/Admin oprávnenie bolo odobrané človeku Martina/)).toBeVisible()
  expect(state.memberRoles).toEqual([])
  expect(
    state.calls
      .filter((call) => call.path === '/api/v1/admin/discord/roles')
      .map((call) => (call.body as Record<string, unknown>).enabled),
  ).toEqual([true, true, false, false])
})

test('11 neoprávnený používateľ neobíde Admin API', async ({ page }) => {
  await mockCarlo(page, 'none')
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'Prihlásiť cez Discord' })).toBeVisible()
  const status = await page.evaluate(async () =>
    fetch('/api/v1/admin/settings/publication', { method: 'PUT', body: '{}' }).then(
      (response) => response.status,
    ),
  )
  expect(status).toBe(401)
})

test('12 stop carlo je viditeľné mimo preview a Admin ho vie zaradiť', async ({ page }) => {
  const state = await mockCarlo(page)
  await page.goto('/oznamy')
  await expect(page.getByText('Interná porada')).toHaveCount(0)
  await page.getByRole('button', { name: /Google kalendár/ }).click()
  await page.getByRole('button', { name: 'Upraviť Interná porada' }).click()
  await page
    .locator('fieldset')
    .filter({ hasText: 'Zaradenie do oznamov' })
    .locator('select')
    .selectOption('force_include')
  await page.getByRole('button', { name: 'Uložiť zmenu' }).click()
  await page.getByRole('button', { name: /Najbližší prehľad/ }).click()
  await expect(page.getByText('Interná porada').first()).toBeVisible()
  expect(state.includedStop).toBe(true)
})

test('13 instance a budúca séria používajú odlišné endpointy', async ({ page }) => {
  const state = await mockCarlo(page, 'team_mod')
  await page.goto('/oznamy')
  await page.getByRole('button', { name: 'Upraviť Otvorený Domček' }).click()
  await page.getByText('Tento a všetky budúce', { exact: true }).click()
  await page.getByLabel('Redakčný popis').fill('Odteraz pre sériu')
  await page.getByRole('button', { name: 'Uložiť pre sériu' }).click()
  expect(state.calls.some((call) => call.path.endsWith('/series-override'))).toBe(true)
  expect(state.calls.some((call) => call.path === '/api/v1/events/event-1/override')).toBe(false)
})

test('14 SDB FMA vidí balík a publikuje, ale nemá ostatnú administráciu', async ({ page }) => {
  const state = await mockCarlo(page, 'publisher')
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Ručné zverejnenie' })).toBeVisible()
  await expect(page.getByRole('link', { name: /Nastavenia/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Audit/ })).toHaveCount(0)
  await page.getByRole('button', { name: 'Pripraviť ručné zverejnenie' }).click()
  await page.getByRole('button', { name: 'Potvrdiť a zverejniť' }).click()
  expect(state.published).toBe(true)
})

test('15 rozhranie zvládne veľký balík bez horizontálneho pretečenia', async ({ page }) => {
  const state = await mockCarlo(page)
  state.extraEvents = 60
  await page.goto('/oznamy')
  await expect(page.getByText('Programová udalosť 60').first()).toBeVisible()
  const fitsViewport = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )
  expect(fitsViewport).toBe(true)
})

test('16 klávesnica preskočí na obsah a modal vráti fokus', async ({ page }) => {
  await mockCarlo(page, 'team_mod')
  await page.goto('/oznamy')
  await expect(page.getByRole('heading', { name: 'Redakčný pult' })).toBeVisible()
  await page.keyboard.press('Tab')
  const skipLink = page.getByRole('link', { name: 'Preskočiť na obsah' })
  await expect(skipLink).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()

  const opener = page.getByRole('button', { name: 'Manuálnu udalosť' })
  await opener.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(opener).toBeFocused()
})

test('17 rešpektuje systémové nastavenie obmedzeného pohybu', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await mockCarlo(page)
  await page.goto('/')
  const timing = await page
    .getByRole('link', { name: /Skontrolovať oznamy/ })
    .evaluate((element) => {
      const style = getComputedStyle(element)
      return {
        animationDuration: style.animationDuration,
        transitionDuration: style.transitionDuration,
      }
    })
  expect(Number.parseFloat(timing.animationDuration)).toBeLessThanOrEqual(0.00001)
  expect(Number.parseFloat(timing.transitionDuration)).toBeLessThanOrEqual(0.00001)
})

for (const [name, path] of [
  ['Prehľad', '/'],
  ['Redakčný pult', '/oznamy'],
  ['Kanály', '/kanaly'],
  ['Roly', '/roly'],
  ['Reakcie', '/reakcie'],
  ['Nastavenia', '/nastavenia'],
] as const) {
  test(`18 Axe: ${name} nemá automaticky zistiteľné WCAG A/AA porušenie`, async ({
    page,
  }, testInfo) => {
    await mockCarlo(page)
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    const visualAuditPage = process.env.CARLO_VISUAL_AUDIT_PAGE ?? 'Reakcie'
    if (process.env.CARLO_VISUAL_AUDIT_DIR && name === visualAuditPage) {
      await page.screenshot({
        path: `${process.env.CARLO_VISUAL_AUDIT_DIR}/${path === '/' ? 'prehlad' : path.slice(1)}--baseline--${testInfo.project.name}.png`,
        fullPage: true,
      })
    }
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    const violations = result.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.map((node) => node.target.join(' ')),
    }))
    expect(violations, `${path}: ${JSON.stringify(violations)}`).toEqual([])
  })
}

test('19 Reakcie upravujú, testujú a ukladajú práve viditeľné emoji', async ({ page }) => {
  const state = await mockCarlo(page)
  await page.goto('/reakcie')
  await expect(page.getByRole('heading', { name: 'Čo má Carlo označiť emoji?' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3 })).toHaveCount(3)

  await page.getByRole('switch', { name: 'Zapnúť: Reakcia pri označení Carla' }).click()
  await expect(page.getByText('Máte neuložené zmeny')).toBeVisible()

  await page.getByRole('link', { name: 'Roly' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('Zahodiť neuložené zmeny?')
  await page.getByRole('button', { name: 'Zostať a dokončiť' }).click()
  await expect(page).toHaveURL(/\/reakcie$/)

  await page.getByRole('button', { name: 'Reakcia pri označení Carla: zmeniť emoji' }).click()
  const emojiSearch = page.getByPlaceholder('Hľadať emoji…')
  await emojiSearch.fill('party')
  await page.getByRole('button', { name: 'party popper' }).click()

  const mentionRule = page.locator('.reaction-rule').filter({
    has: page.getByRole('heading', { name: 'Reakcia pri označení Carla' }),
  })
  await mentionRule.getByRole('button', { name: 'Vyskúšať' }).click()
  await expect(
    page.getByRole('dialog', { name: 'Vyskúšať: Reakcia pri označení Carla' }),
  ).toContainText('presne emoji, ktoré práve vidíte')
  await page.getByRole('button', { name: 'Poslať skúšobnú správu' }).dblclick()
  await expect(page.getByText(/Skúšobná správa s aktuálne zobrazeným emoji/)).toBeVisible()

  const testCalls = state.calls.filter(
    (call) => call.path === '/api/v1/admin/discord/reactions/test',
  )
  expect(testCalls).toHaveLength(1)
  expect(testCalls[0]?.body).toMatchObject({
    kind: 'mention',
    channel_id: '700',
  })
  const testedEmoji = testCalls[0]?.body as Record<string, unknown>
  expect(Boolean(testedEmoji.emoji_id) !== Boolean(testedEmoji.emoji_unicode)).toBe(true)

  await page.getByRole('button', { name: 'Uložiť zmeny' }).click()
  await expect(page.getByText('Všetky zmeny sú uložené')).toBeVisible()
  await page.reload()
  await expect(
    page.getByRole('switch', { name: 'Vypnúť: Reakcia pri označení Carla' }),
  ).toBeChecked()

  const automaticRule = page.locator('.reaction-rule').filter({
    has: page.getByRole('heading', { name: 'Reakcia na nové správy' }),
  })
  await automaticRule.getByRole('textbox', { name: 'Kanály' }).fill('moder')
  await automaticRule.getByRole('option', { name: /#moderatori/ }).click()
  await expect(automaticRule.getByText('moderatori', { exact: true })).toBeVisible()
  await automaticRule.getByRole('button', { name: 'Zrušiť výber' }).click()
  await expect(automaticRule.getByText('Žiadny kanál nie je vybraný.')).toBeVisible()
})

test('20 Reakcie ponúknu náhradu za nedostupné serverové emoji', async ({ page }) => {
  const state = await mockCarlo(page)
  state.reactions = {
    ...state.reactions,
    seen_emoji_id: '991',
    seen_emoji_unicode: null,
  }
  await page.goto('/reakcie')
  await expect(page.getByText('Toto emoji už na serveri nie je dostupné.')).toBeVisible()
  await page.getByRole('button', { name: 'Reakcia pod prehľadom: zmeniť emoji' }).click()
  await page.getByPlaceholder('Hľadať emoji…').fill('seen')
  await page.locator('.reaction-emoji-popover .epr-emoji').first().click()
  await expect(page.getByText('Toto emoji už na serveri nie je dostupné.')).toHaveCount(0)
})

test('21 Reakcie pri chybe ponúknu obnovu namiesto nekonečného načítania', async ({ page }) => {
  const state = await mockCarlo(page)
  state.settingsFailureStatus = 503
  await page.goto('/reakcie')
  await expect(page.getByRole('alert')).toContainText('Nastavenia reakcií sa teraz nedajú načítať.')
  await expect(page.getByText('Načítavam reakcie a emoji…')).toHaveCount(0)
  state.settingsFailureStatus = null
  await page.getByRole('button', { name: 'Skúsiť znova' }).click()
  await expect(page.getByRole('heading', { name: 'Čo má Carlo označiť emoji?' })).toBeVisible()
})

test('22 Reakcie pri chýbajúcom oprávnení zobrazia zrozumiteľný zákaz', async ({ page }) => {
  await mockCarlo(page, 'team_mod')
  await page.goto('/reakcie')
  await expect(page.getByRole('alert')).toContainText('Na správu reakcií nemáte oprávnenie.')
  await expect(page.getByText('Načítavam reakcie a emoji…')).toHaveCount(0)
})

test('23 Roly chránia posledného Admina a dávajú konkrétny ďalší krok', async ({ page }) => {
  const state = await mockCarlo(page)
  state.memberRoles = ['900']
  state.roleMutationFailure = 'last_admin'
  await page.goto('/roly')
  await page.getByRole('combobox', { name: 'Koho chcete spravovať?' }).fill('mart')
  await page.getByRole('option', { name: /Martina Živčáková-Hrušková/ }).click()
  await page.getByRole('button', { name: 'Odobrať Admin' }).click()
  const dialog = page.getByRole('alertdialog')
  await dialog.getByRole('button', { name: 'Odobrať Admin' }).click()
  await expect(dialog.getByRole('alert')).toContainText(
    'Najprv udeľte Admin oprávnenie niekomu ďalšiemu.',
  )
  await expect(dialog).toBeVisible()
  expect(state.memberRoles).toEqual(['900'])
  await dialog.getByRole('button', { name: 'Zrušiť' }).click()
  await expect(page.getByRole('button', { name: 'Odobrať Admin' })).toBeFocused()
})

test('24 Roly pri Discord obmedzení neukážu falošný úspech', async ({ page }) => {
  const state = await mockCarlo(page)
  state.roleMutationFailure = 'discord_unavailable'
  await page.goto('/roly')
  await page.getByRole('combobox', { name: 'Koho chcete spravovať?' }).fill('mart')
  await page.getByRole('option', { name: /Martina Živčáková-Hrušková/ }).click()
  await page.getByRole('button', { name: 'Udeliť Team Mod' }).click()
  const dialog = page.getByRole('alertdialog')
  await dialog.getByRole('button', { name: 'Udeliť Team Mod' }).click()
  await expect(dialog.getByRole('alert')).toContainText('Discord výsledok')
  await expect(page.getByText(/oprávnenie bolo udelené/)).toHaveCount(0)
  expect(state.memberRoles).toEqual([])
})

test('25 Roly čerstvo odmietnu zmenu po strate Admin oprávnenia', async ({ page }) => {
  const state = await mockCarlo(page)
  await page.goto('/roly')
  await page.getByRole('combobox', { name: 'Koho chcete spravovať?' }).fill('mart')
  await page.getByRole('option', { name: /Martina Živčáková-Hrušková/ }).click()
  await page.getByRole('button', { name: 'Udeliť Team Mod' }).click()
  state.role = 'team_mod'
  const dialog = page.getByRole('alertdialog')
  await dialog.getByRole('button', { name: 'Udeliť Team Mod' }).click()
  await expect(dialog.getByRole('alert')).toContainText('už nie je platné')
  expect(state.memberRoles).toEqual([])
})

test('26 Roly obnovia lokálne zlyhané vyhľadávanie bez straty dopytu', async ({ page }) => {
  const state = await mockCarlo(page)
  state.memberSearchFailureStatus = 503
  await page.goto('/roly')
  const search = page.getByRole('combobox', { name: 'Koho chcete spravovať?' })
  await search.fill('mart')
  const error = page.getByRole('alert').filter({ hasText: 'Ľudí sa teraz nepodarilo vyhľadať' })
  await expect(error).toBeVisible()
  await expect(search).toHaveValue('mart')
  state.memberSearchFailureStatus = null
  await error.getByRole('button', { name: 'Skúsiť znova' }).click()
  await expect(page.getByRole('option')).toHaveCount(2)
})

test('27 Roly pri chybe načítania ponúknu obnovu a nezostanú v loadingu', async ({ page }) => {
  const state = await mockCarlo(page)
  state.settingsFailureStatus = 503
  await page.goto('/roly')
  await expect(page.getByRole('alert')).toContainText('Oprávnenia sa teraz nedajú načítať.')
  await expect(page.getByText('Načítavam roly…')).toHaveCount(0)
  state.settingsFailureStatus = null
  await page.getByRole('button', { name: 'Skúsiť znova' }).click()
  await expect(page.getByRole('heading', { name: 'Nájdite človeka' })).toBeVisible()
})

test('28 Roly pri priamom vstupe bez Admin oprávnenia vysvetlia zákaz', async ({ page }) => {
  await mockCarlo(page, 'team_mod')
  await page.goto('/roly')
  await expect(page.getByRole('alert')).toContainText('Roly môže spravovať iba Admin.')
  await expect(page.getByText('Načítavam roly…')).toHaveCount(0)
})

test('29 Roly nedovolia starej odpovedi prepísať novší dopyt', async ({ page }) => {
  await mockCarlo(page)
  await page.goto('/roly')
  const search = page.getByRole('combobox', { name: 'Koho chcete spravovať?' })
  await search.fill('pomaly')
  await page.waitForTimeout(300)
  await search.fill('mart')
  await expect(page.getByRole('option')).toHaveCount(2)
  await page.waitForTimeout(500)
  await expect(page.getByRole('option')).toHaveCount(2)
  await expect(page.getByRole('option', { name: /Testovací člen/ })).toHaveCount(0)
})

test('30 Nastavenia chránia draft, rizikovú voľbu a dvojklik uloženia', async ({ page }) => {
  const state = await mockCarlo(page)
  await page.goto('/nastavenia')
  await expect(page.getByRole('heading', { name: 'Nastavenia' })).toBeVisible()
  await expect(page.getByText('Ručné publikovanie')).toHaveCount(0)
  await expect(page.getByText('Europe/Bratislava · automaticky rešpektuje letný čas')).toBeVisible()

  const closing = page.getByLabel('Záverečná správa (voliteľná)')
  await closing.fill('Pokojný záver týždňa.')
  await expect(page.getByText('Máte neuložené zmeny')).toBeVisible()
  await page.reload()
  await expect(closing).toHaveValue('Pokojný záver týždňa.')
  await expect(page.getByText('Máte neuložené zmeny')).toBeVisible()

  await page.getByRole('tab', { name: 'Kalendáre' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('Zahodiť neuložené zmeny?')
  await page.getByRole('button', { name: 'Zostať a dokončiť' }).click()
  await expect(closing).toHaveValue('Pokojný záver týždňa.')

  const staleSwitch = page.getByRole('switch', { name: 'Použiť posledné dostupné dáta' })
  await staleSwitch.click()
  await expect(page.getByRole('alertdialog')).toContainText('Povoliť publikovanie zo starších dát?')
  await page.getByRole('button', { name: 'Nepovoliť' }).click()
  await expect(staleSwitch).not.toBeChecked()
  await staleSwitch.click()
  await page.getByRole('button', { name: 'Povoliť staršie dáta' }).click()
  await expect(staleSwitch).toBeChecked()

  await page.getByRole('button', { name: 'Uložiť zmeny' }).dblclick()
  await expect(page.getByText('Publikačné nastavenia sú uložené.')).toBeVisible()
  expect(
    state.calls.filter((call) => call.path === '/api/v1/admin/settings/publication'),
  ).toHaveLength(1)
  expect(state.publicationSettings).toMatchObject({
    closing_message: 'Pokojný záver týždňa.',
    allow_stale_calendar_cache: true,
    everyone_mention_enabled: true,
  })
})

test('31 Nastavenia pri konflikte zachovajú draft a vedome načítajú novšiu verziu', async ({
  page,
}) => {
  const state = await mockCarlo(page)
  state.settingsSaveFailureStatus = 409
  await page.goto('/nastavenia')
  const closing = page.getByLabel('Záverečná správa (voliteľná)')
  await closing.fill('Moja rozpracovaná hodnota')
  await page.getByRole('button', { name: 'Uložiť zmeny' }).click()
  const conflict = page.getByRole('alert').filter({ hasText: 'medzitým zmenil niekto iný' })
  await expect(conflict).toBeVisible()
  await expect(closing).toHaveValue('Moja rozpracovaná hodnota')

  state.settingsSaveFailureStatus = null
  state.publicationSettings = {
    ...state.publicationSettings,
    closing_message: 'Aktuálna hodnota od iného Admina',
    version: 2,
  }
  await conflict.getByRole('button', { name: 'Načítať aktuálne hodnoty' }).click()
  await expect(page.getByLabel('Záverečná správa (voliteľná)')).toHaveValue(
    'Aktuálna hodnota od iného Admina',
  )
})

test('32 Kalendáre používajú modal, pravdivý výsledok a žiadnu číselnú prioritu', async ({
  page,
}, testInfo) => {
  const state = await mockCarlo(page)
  await page.goto('/nastavenia')
  await page.getByRole('tab', { name: 'Kalendáre' }).click()
  await expect(page.getByText('Carlo môže fungovať aj bez kalendára.')).toBeVisible()
  if (process.env.CARLO_VISUAL_AUDIT_DIR) {
    await page.screenshot({
      path: `${process.env.CARLO_VISUAL_AUDIT_DIR}/nastavenia--kalendare--${testInfo.project.name}.png`,
      fullPage: true,
    })
  }

  const addOpener = page.locator('.calendar-card-heading').getByRole('button', {
    name: 'Pridať kalendár',
  })
  await addOpener.click()
  const dialog = page.getByRole('dialog', { name: 'Pridať Google kalendár' })
  await dialog.getByLabel('Názov v administrácii').fill('Program Domčeka')
  await dialog.getByLabel('Google Calendar ID').fill('program@example.test')
  await dialog.getByRole('button', { name: 'Pridať kalendár' }).dblclick()
  await expect(page.getByText('Google kalendár Program Domčeka bol pridaný.')).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(addOpener).toBeFocused()
  expect(state.calls.filter((call) => call.path === '/api/v1/admin/calendars')).toHaveLength(1)

  const row = page.locator('.calendar-row').filter({ hasText: 'Program Domčeka' })
  await expect(row).toContainText('Aktuálny')
  await row.getByRole('button', { name: 'Synchronizovať' }).click()
  await expect(page.getByText(/Program Domčeka sa obnovil.*12 udalostí/)).toBeVisible()
  await row.getByRole('button', { name: 'Upraviť' }).click()
  const edit = page.getByRole('dialog', { name: /Upraviť kalendár Program Domčeka/ })
  await expect(edit.getByLabel('Priorita')).toHaveCount(0)
  await edit.getByLabel('Názov v administrácii').fill('Program a podujatia')
  await edit.getByRole('button', { name: 'Uložiť kalendár' }).click()
  await expect(page.getByText('Kalendár Program a podujatia bol upravený.')).toBeVisible()
})

test('33 Nastavenia pri chybe načítania a bez oprávnenia nezostanú prázdne', async ({ page }) => {
  const state = await mockCarlo(page)
  state.settingsFailureStatus = 503
  await page.goto('/nastavenia')
  await expect(
    page.getByRole('heading', { name: 'Nastavenia sa nepodarilo načítať' }),
  ).toBeVisible()
  await expect(page.getByText('Nastavenia sa teraz nedajú načítať.')).toBeVisible()
  state.settingsFailureStatus = null
  await page.getByRole('button', { name: 'Skúsiť znova' }).click()
  await expect(page.getByRole('heading', { name: 'Nastavenia', exact: true })).toBeVisible()
})

test('34 Priamy vstup do Nastavení bez Admin oprávnenia vysvetlí obmedzenie', async ({ page }) => {
  await mockCarlo(page, 'team_mod')
  await page.goto('/nastavenia')
  await expect(
    page.getByRole('heading', { name: 'Nastavenia sa nepodarilo načítať' }),
  ).toBeVisible()
  await expect(page.getByText('Nastavenia Carla môže spravovať iba Admin.')).toBeVisible()
})

test('35 Kalendár so zlyhaným obnovením ukáže vek, dopad a ľudskú nápravu', async ({ page }) => {
  const state = await mockCarlo(page)
  state.calendars = [
    mockCalendar({
      sync_status: 'failed',
      last_sync_error: '403 forbidden permission denied',
      last_sync_success_at: '2026-08-10T18:00:00Z',
    }),
  ]
  await page.goto('/nastavenia')
  await page.getByRole('tab', { name: 'Kalendáre' }).click()
  const row = page.locator('.calendar-row').filter({ hasText: 'Program Domčeka' })
  await expect(row).toContainText('Chyba')
  await expect(row).toContainText('Carlo nemá ku kalendáru prístup')
  await expect(row).toContainText('Naposledy úspešne')
})
