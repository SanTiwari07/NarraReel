import { api } from '../api/client'
import type { Project } from '../api/types'
import { toProject, useDraft } from '../state/project'

/** Reads a saved project file and checks it with the server before anything changes. */
export async function readProjectFile(file: File): Promise<Project> {
  let raw: unknown
  try {
    raw = JSON.parse(await file.text())
  } catch {
    throw new Error('That file is not a NarraReel project.')
  }
  return api.validateProject(raw)
}

/** Downloads everything chosen so far as a file that can be opened later. */
export function downloadProject() {
  const project = toProject(useDraft.getState())
  const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'project.narrareel.json'
  a.click()
  window.setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
