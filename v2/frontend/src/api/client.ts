export interface LivenessResponse {
  status: 'alive'
  version: string
  environment: string
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready'
  dependencies: Record<string, { status: 'healthy' | 'unhealthy' }>
}

export interface OperationsSummary {
  observed_at: string
  next_publication: { slot_key: string; scheduled_for: string }
  processes: Array<{
    process_name: string
    instance_id: string
    state: string
    healthy: boolean
    started_at: string
    last_seen_at: string
    details: Record<string, unknown>
  }>
  active_instance_counts: Record<string, number>
  calendars: Array<{
    id: string
    display_name: string
    active: boolean
    sync_status: string
    last_sync_attempt_at: string | null
    last_sync_success_at: string | null
    last_sync_error: string | null
  }>
  publication_metrics: {
    sample_size: number
    successful: number
    failed: number
    in_progress: number
    skipped: number
  }
  recent_tasks: Array<{
    id: string
    task_type: string
    state: string
    scheduled_for: string
    started_at: string | null
    completed_at: string | null
    error_code: string | null
  }>
}

export interface SessionResponse {
  authenticated: true
  user: {
    id: string
    username: string
    display_name: string
    avatar_url: string | null
  }
  guild_id: string
  roles: string[]
  capabilities: string[]
  expires_at: string
}

export interface DraftItem {
  kind: 'info' | 'external_event' | 'manual_event'
  source_id: string
  title: string
  description: string | null
  included: boolean
  exclusion_reason: 'force_exclude' | 'stop_carlo' | null
  display_time: string | null
  day_name: string | null
  day_emoji: string | null
  is_all_day: boolean | null
  starts_at?: string | null
  ends_at?: string | null
  starts_on?: string | null
  ends_on?: string | null
  source_title: string | null
  source_description: string | null
  is_recurring: boolean
  instance_override_version: number
  instance_public_title: string | null
  instance_description_state: DescriptionState
  instance_public_description: string | null
  inclusion_decision: InclusionDecision
  series_override_version: number
  series_public_title: string | null
  series_description_state: DescriptionState
  series_public_description: string | null
}

export type DescriptionState = 'inherit' | 'custom' | 'intentionally_empty'
export type InclusionDecision = 'auto' | 'force_include' | 'force_exclude'

export interface EventOverrideUpdate {
  expected_version: number
  public_title: string | null
  description_state: DescriptionState
  public_description: string | null
  inclusion_decision?: InclusionDecision
}

export interface EventOverrideResponse {
  public_title: string | null
  description_state: DescriptionState
  public_description: string | null
  version: number
}

export interface ManualEventRecord {
  id: string
  title: string
  description: string | null
  is_all_day: boolean
  starts_at: string | null
  ends_at: string | null
  starts_on: string | null
  ends_on: string | null
  timezone: string
  link_url: string | null
  active: boolean
  deleted_at: string | null
  version: number
}

export type ManualEventWrite = Omit<ManualEventRecord, 'id' | 'deleted_at' | 'version'> & {
  expected_version?: number
}

export interface InfoAnnouncementRecord {
  id: string
  title: string
  description: string
  link_url: string | null
  image_url: string | null
  valid_from: string
  valid_until: string
  active: boolean
  deleted_at: string | null
  version: number
}

export interface InfoImageUpload {
  image_url: string
  width: number
  height: number
  bytes: number
}

export type InfoAnnouncementWrite = Omit<
  InfoAnnouncementRecord,
  'id' | 'deleted_at' | 'version'
> & { expected_version?: number }

export interface AuditRecord {
  id: string
  actor_user_id: string | null
  action: string
  object_type: string
  object_id: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  result: 'succeeded' | 'failed'
  correlation_id: string
  created_at: string | null
}

export interface DiscordEmbedPlan {
  item_kind?: DraftItem['kind']
  source_id: string
  color?: number
  title: string
  description: string | null
  author_name: string | null
  author_icon_url: string | null
  link_url: string | null
  thumbnail_url: string | null
}

export interface DiscordMessagePlan {
  position: number
  part_key: string
  content: string | null
  embeds: DiscordEmbedPlan[]
  allowed_mentions: string[]
  seen_target: boolean
  reaction_emoji: string | null
}

export interface PublicationDraft {
  composer_version: string
  guild_id: number
  slot_key: string
  scheduled_for: string
  scheduled_local: string
  timezone: string
  window_starts_at: string
  window_ends_at: string
  intro_text: string
  outro_text: string | null
  editor_events: DraftItem[]
  public_items: DraftItem[]
  warnings: Array<{ code: string; item_kind: string; source_id: string }>
  messages: DiscordMessagePlan[]
}

export interface PublicationSettings {
  guild_id: string
  timezone: string
  publication_weekday: number
  publication_time: string
  automatic_publication_enabled: boolean
  publish_google_descriptions: boolean
  generated_intro_enabled: boolean
  everyone_mention_enabled: boolean
  allow_stale_calendar_cache: boolean
  publication_grace_seconds: number
  publication_guard_recipient_ids: string[]
  alert_calendar_sync_enabled: boolean
  alert_publication_enabled: boolean
  alert_channel_operations_enabled: boolean
  alert_role_operations_enabled: boolean
  alert_publication_reminder_enabled: boolean
  admin_role_id: string | null
  team_mod_role_id: string | null
  publisher_role_id: string | null
  announcement_channel_id: string | null
  command_channel_id: string | null
  moderator_channel_id: string | null
  projects_category_id: string | null
  archive_category_id: string | null
  closing_message: string | null
  version: number
}

export interface CalendarSource {
  id: string
  guild_id: string
  external_calendar_id: string
  display_name: string
  priority: number
  active: boolean
  sync_status: 'never' | 'running' | 'succeeded' | 'failed'
  last_sync_attempt_at: string | null
  last_sync_success_at: string | null
  last_full_sync_at: string | null
  last_sync_error: string | null
  version: number
}

export interface ReactionSettings {
  guild_id: string
  seen_enabled: boolean
  seen_emoji_id: string | null
  seen_emoji_unicode: string | null
  auto_reaction_enabled: boolean
  auto_reaction_emoji_id: string | null
  auto_reaction_emoji_unicode: string | null
  mention_reaction_enabled: boolean
  mention_reaction_emoji_id: string | null
  mention_reaction_emoji_unicode: string | null
  auto_reaction_channel_ids: string[]
  version: number
}

export interface AdminSettings {
  publication: PublicationSettings
  calendars: CalendarSource[]
  reactions: ReactionSettings
}

export interface DiscordChannelOption {
  id: string
  name: string
  kind: 'text' | 'category'
  category_id: string | null
  text_channel_count: number
  voice_channel_count: number
  can_create_project_channel: boolean
  is_archive_category: boolean
  is_default_project_category: boolean
}

export interface DiscordRoleOption {
  id: string
  name: string
  position: number
  managed: boolean
}

export interface DiscordEmojiOption {
  id: string
  name: string
  animated: boolean
  available: boolean
}

export interface DiscordDirectory {
  channels: DiscordChannelOption[]
  categories: DiscordChannelOption[]
  roles: DiscordRoleOption[]
  emojis: DiscordEmojiOption[]
}

export interface DiscordMemberOption {
  id: string
  username: string
  display_name: string
  avatar_url: string | null
  role_ids: string[]
  undo_id?: string | null
}

export interface ArchiveRequest {
  id: string
  discord_channel_id: string
  original_channel_name: string
  requested_by_user_id: string
  reason: string
  state: string
  expires_at: string
  undo_id?: string | null
}

export interface ManualPublicationPreview {
  slot_key: string
  scheduled_for: string
  announcement_count: number
  message_count: number
  announcement_channel_id: string
  confirmation_token: string
  expires_at: string
  draft: PublicationDraft
}

export interface PublicationGuardResult {
  run_id: string
  state: string
  message_ids: string[]
  warning_codes: string[]
  release_at: string | null
}

export interface PublicationHistoryItem {
  id: string
  kind: 'external_event' | 'manual_event' | 'info'
  position: number
  title: string | null
  description: string | null
  display_time: string | null
  day_emoji: string | null
  starts_at: string | null
  ends_at: string | null
  starts_on: string | null
  ends_on: string | null
  is_all_day: boolean | null
  link_url: string | null
  image_url: string | null
}

export interface PublicationHistoryMessage {
  id: string
  position: number
  discord_channel_id: string
  discord_message_id: string | null
  jump_url: string | null
  state: string
  content: string | null
  embeds: DiscordEmbedPlan[]
  allowed_mentions: string[]
  seen_target: boolean
  reaction_emoji: string | null
  attempt_count: number
  error_detail: string | null
  reaction_error: string | null
  sent_at: string | null
}

export interface PublicationHistoryEntry {
  id: string
  slot_key: string
  scheduled_for: string
  mode: 'automatic' | 'manual'
  initiated_by_user_id: string | null
  state: string
  attempt: number
  composer_version: string
  intro_text: string
  intro_prompt_version: string
  intro_used_fallback: boolean
  outro_text: string | null
  warning_codes: string[]
  started_at: string | null
  completed_at: string | null
  error_code: string | null
  error_detail: string | null
  items: PublicationHistoryItem[]
  messages: PublicationHistoryMessage[]
}

export interface ShadowPublicationCapture {
  id: string
  slot_key: string
  scheduled_for: string
  first_observed_at: string
  last_observed_at: string
  observation_count: number
  draft_sha256: string
  item_count: number
  message_count: number
  calendar_sync_valid: boolean
  calendar_sync_evidence: {
    sync_attempt_succeeded: boolean
    active_source_count: number
    sources: Array<{
      id: string
      status: string
      last_sync_success_at: string | null
    }>
  }
  warning_codes: string[]
  draft: PublicationDraft
}

export interface DashboardSummary {
  automatic_publication_enabled: boolean
  last_calendar_sync_at: string | null
  pending_archive_count: number
  discord_places_configured: boolean
  active_calendars: Array<{
    id: string
    display_name: string
    sync_status: string
    freshness: 'fresh' | 'stale_warning' | 'unsafe'
    last_sync_success_at: string | null
    last_sync_error: string | null
  }>
  last_publication: {
    id: string
    scheduled_for: string
    completed_at: string | null
    state: string
    mode: 'automatic' | 'manual'
  } | null
}

interface ProblemDetail {
  title?: string
  detail?: string
  code?: string
  correlation_id?: string
  current?: unknown
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly correlationId: string | null,
    readonly code: string | null = null,
    readonly current: unknown = null,
  ) {
    super(message)
  }
}

function csrfToken(): string | null {
  const prefix = 'domcek_csrf='
  const value = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
  return value ? decodeURIComponent(value.slice(prefix.length)) : null
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = csrfToken()
    if (token) headers.set('X-CSRF-Token', token)
  }
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'include',
  })
  if (!response.ok) {
    let problem: ProblemDetail = {}
    try {
      problem = (await response.json()) as ProblemDetail
    } catch {
      // A safe fallback is shown when an intermediary did not return JSON.
    }
    if (response.status === 401 && path !== '/api/v1/session' && path !== '/api/v1/auth/logout') {
      window.dispatchEvent(new CustomEvent('carlo:session-expired'))
    }
    throw new ApiError(
      problem.detail ?? problem.title ?? `Požiadavka zlyhala (${response.status}).`,
      response.status,
      problem.correlation_id ?? response.headers.get('X-Correlation-ID'),
      problem.code ?? null,
      problem.current ?? null,
    )
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function getSession(signal?: AbortSignal) {
  return requestJson<SessionResponse>('/api/v1/session', { signal })
}

export function logout() {
  return requestJson<void>('/api/v1/auth/logout', { method: 'POST' })
}

export function getPublicationDraft(signal?: AbortSignal) {
  return requestJson<PublicationDraft>('/api/v1/publication/draft', { signal })
}

export function updateEventOverride(eventId: string, body: EventOverrideUpdate) {
  return requestJson<EventOverrideResponse>(`/api/v1/events/${eventId}/override`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function updateSeriesOverride(eventId: string, body: EventOverrideUpdate) {
  return requestJson<EventOverrideResponse>(`/api/v1/events/${eventId}/series-override`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function getManualEvents(signal?: AbortSignal) {
  return requestJson<ManualEventRecord[]>('/api/v1/manual-events', { signal })
}

export function saveManualEvent(body: ManualEventWrite, eventId?: string) {
  return requestJson<ManualEventRecord>(
    eventId ? `/api/v1/manual-events/${eventId}` : '/api/v1/manual-events',
    { method: eventId ? 'PUT' : 'POST', body: JSON.stringify(body) },
  )
}

export function deleteManualEvent(eventId: string, expectedVersion: number) {
  return requestJson<ManualEventRecord>(
    `/api/v1/manual-events/${eventId}?expected_version=${expectedVersion}`,
    { method: 'DELETE' },
  )
}

export function getInfoAnnouncements(signal?: AbortSignal) {
  return requestJson<InfoAnnouncementRecord[]>('/api/v1/info-announcements', { signal })
}

export function uploadInfoImage(image: File) {
  const body = new FormData()
  body.set('image', image)
  return requestJson<InfoImageUpload>('/api/v1/uploads/info-images', {
    method: 'POST',
    body,
  })
}

export function saveInfoAnnouncement(body: InfoAnnouncementWrite, announcementId?: string) {
  return requestJson<InfoAnnouncementRecord>(
    announcementId ? `/api/v1/info-announcements/${announcementId}` : '/api/v1/info-announcements',
    { method: announcementId ? 'PUT' : 'POST', body: JSON.stringify(body) },
  )
}

export function deleteInfoAnnouncement(announcementId: string, expectedVersion: number) {
  return requestJson<InfoAnnouncementRecord>(
    `/api/v1/info-announcements/${announcementId}?expected_version=${expectedVersion}`,
    { method: 'DELETE' },
  )
}

export function getAudit(signal?: AbortSignal) {
  return requestJson<AuditRecord[]>('/api/v1/audit?limit=100', { signal })
}

export function getLiveness(signal?: AbortSignal) {
  return requestJson<LivenessResponse>('/health/live', { signal })
}

export function getReadiness(signal?: AbortSignal) {
  return requestJson<ReadinessResponse>('/health/ready', { signal })
}

export function getOperationsSummary(signal?: AbortSignal) {
  return requestJson<OperationsSummary>('/api/v1/operations/summary', { signal })
}

export function getPublicationHistory(signal?: AbortSignal) {
  return requestJson<PublicationHistoryEntry[]>('/api/v1/publication/history?limit=50', { signal })
}

export function linkExistingPublicationMessage(
  runId: string,
  messagePosition: number,
  discordMessageId: string,
) {
  return requestJson<{ run_id: string; state: string }>(
    `/api/v1/publication/recovery/${runId}/link-existing`,
    {
      method: 'POST',
      body: JSON.stringify({
        message_position: messagePosition,
        discord_message_id: discordMessageId,
      }),
    },
  )
}

export function confirmPublicationMessageNotSent(runId: string, messagePosition: number) {
  return requestJson<{ run_id: string; state: string }>(
    `/api/v1/publication/recovery/${runId}/confirm-not-sent`,
    {
      method: 'POST',
      body: JSON.stringify({ message_position: messagePosition }),
    },
  )
}

export function getShadowPublicationHistory(signal?: AbortSignal) {
  return requestJson<ShadowPublicationCapture[]>('/api/v1/publication/shadow-history?limit=20', {
    signal,
  })
}

export function getDashboardSummary(signal?: AbortSignal) {
  return requestJson<DashboardSummary>('/api/v1/publication/dashboard', { signal })
}

export function getAdminSettings(signal?: AbortSignal) {
  return requestJson<AdminSettings>('/api/v1/admin/settings', { signal })
}

export function updatePublicationSettings(body: PublicationSettings) {
  return requestJson<PublicationSettings>('/api/v1/admin/settings/publication', {
    method: 'PUT',
    body: JSON.stringify({
      ...body,
      expected_version: body.version,
      everyone_mention_enabled: true,
    }),
  })
}

export function createCalendarSource(
  body: Omit<
    CalendarSource,
    | 'id'
    | 'guild_id'
    | 'sync_status'
    | 'last_sync_attempt_at'
    | 'last_sync_success_at'
    | 'last_full_sync_at'
    | 'last_sync_error'
    | 'version'
  >,
) {
  return requestJson<CalendarSource>('/api/v1/admin/calendars', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateCalendarSource(body: CalendarSource) {
  return requestJson<CalendarSource>(`/api/v1/admin/calendars/${body.id}`, {
    method: 'PUT',
    body: JSON.stringify({
      expected_version: body.version,
      external_calendar_id: body.external_calendar_id,
      display_name: body.display_name,
      priority: body.priority,
      active: body.active,
    }),
  })
}

export function syncCalendarSource(sourceId: string, forceFull = false) {
  return requestJson<{ received: number; created: number; updated: number }>(
    `/api/v1/admin/calendars/${sourceId}/sync?force_full=${forceFull}`,
    { method: 'POST' },
  )
}

export function updateReactionSettings(body: ReactionSettings) {
  return requestJson<ReactionSettings>('/api/v1/admin/settings/reactions', {
    method: 'PUT',
    body: JSON.stringify({ ...body, expected_version: body.version }),
  })
}

export function getDiscordDirectory(signal?: AbortSignal) {
  return requestJson<DiscordDirectory>('/api/v1/admin/discord/directory', { signal })
}

export function searchDiscordMembers(query: string, signal?: AbortSignal) {
  return requestJson<DiscordMemberOption[]>(
    `/api/v1/admin/discord/members?query=${encodeURIComponent(query)}`,
    { signal },
  )
}

export function setDiscordRole(memberId: string, role: 'team_mod' | 'admin', enabled: boolean) {
  return requestJson<DiscordMemberOption>('/api/v1/admin/discord/roles', {
    method: 'PUT',
    body: JSON.stringify({ member_id: memberId, role, enabled }),
  })
}

export function testDiscordReaction(
  kind: 'seen' | 'auto' | 'mention',
  channelId: string,
  emoji: { emoji_id: string | null; emoji_unicode: string | null },
) {
  return requestJson<{ message_id: string }>('/api/v1/admin/discord/reactions/test', {
    method: 'POST',
    body: JSON.stringify({ kind, channel_id: channelId, ...emoji }),
  })
}

export function createDiscordChannel(body: {
  name: string
  emoji: string
  owner_id: string | null
  member_ids: string[]
  role_ids: string[]
  category_id: string | null
  idempotency_key: string
}) {
  return requestJson<{
    channel_id: string
    name: string
    jump_url: string
    undo_id: string | null
  }>('/api/v1/admin/channels', { method: 'POST', body: JSON.stringify(body) })
}

export function undoDiscordOperation(operationId: string) {
  return requestJson<{
    id: string
    operation_type: 'role_change' | 'channel_create' | 'channel_archive'
    state: 'undone'
    object_id: string
  }>(`/api/v1/admin/undo/${operationId}`, { method: 'POST' })
}

export interface UndoOperation {
  id: string
  operation_type: 'role_change' | 'channel_create' | 'channel_archive'
  object_id: string
  state: 'available' | 'undoing'
  before_snapshot: Record<string, unknown>
  after_snapshot: Record<string, unknown>
  created_at: string | null
  last_block_reason: string | null
}

export function getUndoOperations(scope: 'roles' | 'channels', signal?: AbortSignal) {
  return requestJson<UndoOperation[]>(`/api/v1/admin/undo?scope=${scope}`, { signal })
}

export function getArchiveRequests(signal?: AbortSignal) {
  return requestJson<ArchiveRequest[]>('/api/v1/admin/archives', { signal })
}

export function createArchiveRequest(body: { channel_id: string; reason: string }) {
  return requestJson<ArchiveRequest>('/api/v1/admin/archives', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function recoverArchiveRequests() {
  return requestJson<ArchiveRequest[]>('/api/v1/admin/archives/recover', { method: 'POST' })
}

export function decideArchiveRequest(requestId: string, approve: boolean) {
  return requestJson<ArchiveRequest>(`/api/v1/admin/archives/${requestId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ approve }),
  })
}

export function prepareManualPublication() {
  return requestJson<ManualPublicationPreview>('/api/v1/publication/manual/preview', {
    method: 'POST',
  })
}

export function confirmManualPublication(confirmationToken: string) {
  return requestJson<PublicationGuardResult>('/api/v1/publication/manual/confirm', {
    method: 'POST',
    body: JSON.stringify({ confirmation_token: confirmationToken }),
  })
}

export function releaseManualPublication(runId: string) {
  return requestJson<PublicationGuardResult>('/api/v1/publication/manual/release', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId }),
  })
}

export function cancelManualPublication(runId: string) {
  return requestJson<PublicationGuardResult>('/api/v1/publication/manual/cancel', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId }),
  })
}
