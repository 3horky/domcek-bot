import { expect, test } from '@playwright/test'

const sessionToken = 'carlo-browser-e2e-session'
const csrfToken = 'carlo-browser-e2e-csrf'

test('redakčná úprava prejde cez skutočné API a zostane v PostgreSQL', async ({
  page,
}, testInfo) => {
  await page.context().addCookies([
    { name: 'domcek_session', value: sessionToken, url: 'http://127.0.0.1:4175' },
    { name: 'domcek_csrf', value: csrfToken, url: 'http://127.0.0.1:4175' },
  ])

  const description = `Uložené cez ${testInfo.project.name}`
  await page.goto('/oznamy')
  await expect(page.getByRole('heading', { name: 'Redakčný pult' })).toBeVisible()
  await page.getByRole('button', { name: 'Upraviť Full-stack skúška' }).click()
  await page.getByRole('textbox', { name: /Redakčný popis/ }).fill(description)
  await page.getByRole('button', { name: 'Uložiť zmenu' }).click()
  await expect(page.getByText(description).first()).toBeVisible()

  await page.reload()
  await expect(page.getByText(description).first()).toBeVisible()

  const response = await page.request.get('/api/v1/publication/draft')
  expect(response.status()).toBe(200)
  const draft = (await response.json()) as {
    editor_events: Array<{ title: string; description: string | null }>
  }
  expect(draft.editor_events.find((item) => item.title === 'Full-stack skúška')?.description).toBe(
    description,
  )
})
