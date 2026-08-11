import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = resolve(frontendRoot, '..', '..')
const failures = []

function read(path) {
  return readFileSync(resolve(repositoryRoot, path), 'utf8')
}

function checkChecklistPriorities() {
  const standard = read('UI_UX_STANDARDY.md')
  const chapter19 = standard.match(/## 19\.[\s\S]*?(?=## 20\.)/)?.[0] ?? ''
  const chapter20 = standard.match(/## 20\.[\s\S]*?(?=## 21\.)/)?.[0] ?? ''
  const checklistItems = chapter19.split('\n').filter((line) => line.startsWith('- [ ]'))
  const definitionItems = chapter20.split('\n').filter((line) => /^\d+\. /.test(line))

  if (checklistItems.length === 0 || definitionItems.length === 0) {
    failures.push('Kapitoly 19 alebo 20 nemajú očakávané kontrolné body.')
    return
  }

  for (const line of [...checklistItems, ...definitionItems]) {
    const labels = ['[BLOKUJE]', '[BACKLOG]'].filter((label) => line.includes(label))
    if (labels.length !== 1) failures.push(`Kontrolný bod nemá práve jednu prioritu: ${line}`)
  }
}

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    return entry.isDirectory() ? walk(path) : [path]
  })
}

function checkNativeMultipleSelect() {
  const sourceRoot = resolve(frontendRoot, 'src')
  for (const path of walk(sourceRoot).filter((item) => /\.tsx?$/.test(item))) {
    const source = readFileSync(path, 'utf8')
    if (/<select\b[^>]*\bmultiple(?:\s|=|>)/s.test(source)) {
      failures.push(`Natívny viacnásobný select je zakázaný: ${relative(frontendRoot, path)}`)
    }
  }
}

function checkLegacyColorBaseline() {
  const baselines = [
    ['v2/frontend/src/styles/global.css', 241],
    ['v2/frontend/src/components/DiscordPreview.tsx', 26],
  ]
  for (const [path, maximum] of baselines) {
    const count = read(path).match(/#[0-9a-fA-F]{3,8}\b/g)?.length ?? 0
    if (count > maximum) {
      failures.push(`${path} zvýšil legacy hex baseline z ${maximum} na ${count}.`)
    }
  }
}

checkChecklistPriorities()
checkNativeMultipleSelect()
checkLegacyColorBaseline()

if (failures.length > 0) {
  console.error(failures.map((failure) => `- ${failure}`).join('\n'))
  process.exitCode = 1
} else {
  console.log('UI/UX statické invarianty sú splnené.')
}
