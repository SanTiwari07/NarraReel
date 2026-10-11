import type { components } from './schema'

type S = components['schemas']

export type Project = S['ProjectConfig']
export type VoiceSelection = S['VoiceSelection']
export type AnalyzeResponse = S['AnalyzeResponse']
export type PlanResponse = S['PlanResponse']
export type DurationPlan = S['DurationPlan']
export type DurationOption = S['DurationOption']
export type Health = S['HealthResponse']
export interface ProgressEvent {
  stage: string
  fraction: number
  message: string
}

export interface EngineInfo {
  id: string
  display_name: string
  capabilities: {
    offline: boolean
    native_word_timing: boolean
    native_speed: boolean
    energy_control: 'none' | 'basic' | 'expressive'
    cloning: boolean
    languages: string[]
    needs_gpu: 'no' | 'recommended' | 'yes'
  }
  status: {
    available: boolean
    reason: string | null
    needs_download: boolean
    download_size_mb: number | null
  }
}

/** Where the voice-cloning model is, or will be, downloaded. */
export interface ModelStorage {
  path: string
  default_path: string
  chosen: boolean
  from_env: boolean
  free_gb: number | null
  models_gb: number
  needed_gb: number
}

export type Quality = DurationOption['quality']
export type VoiceProfile = S['VoiceProfile']
export type QualityReport = S['QualityReport']
export type CloneResult = S['CloneResult']

export interface Voice {
  engine: string
  id: string
  name: string
  language: string
  gender: 'female' | 'male' | 'neutral' | 'unknown'
  accent: string | null
  offline: boolean
  custom: boolean
  ref: string
}

export interface FontInfo {
  id: string
  family: string
  style: string
  weight: number
  license: string
  tags: string[]
  scripts: string[]
  user: boolean
  name: string
}

export interface FormatInfo {
  id: string
  name: string
  width: number | null
  height: number | null
  fps: number
  positions: Record<string, number>
  max_text_width: number
  safe_zone: { top?: number; bottom?: number; right?: number }
  default_style: string
  note: string
}

export interface StylePreset {
  id: string
  name: string
  font: { id: string; size: number; uppercase: boolean; letter_spacing: number }
  colors: { text: string; highlight: string; outline: string; shadow: string; box: string | null }
  outline_width: number
  shadow_offset: number
  blur: number
  border_style: 'outline' | 'box'
  layout: {
    words_per_chunk: number
    max_lines: number
    position: 'top' | 'middle' | 'lower_middle' | 'bottom'
    offset_y: number
    align_x: 'left' | 'center' | 'right'
    offset_x: number
  }
  highlight: { mode: 'word' | 'karaoke' | 'none'; scale: number; box: boolean; box_color: string; box_padding: number }
  animation: { in: 'none' | 'pop' | 'fade' | 'bounce'; duration_ms: number }
  emphasis: { enabled: boolean; auto: boolean; color: string; scale: number }
}

export interface JobStatus {
  id: string
  kind: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  error: string | null
  fraction: number
  message: string
  stage: string | null
  result: {
    files: Record<string, string>
    duration: number
    target_seconds: number | null
    target_met: boolean | null
    note: string | null
    warnings: string[]
  } | null
}
