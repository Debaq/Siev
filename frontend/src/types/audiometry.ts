// Tipos para el módulo de audiometría

export type Ear = 'od' | 'oi'
export type ConductionType = 'aerea' | 'osea' | 'ldl'

export interface ThresholdPoint {
  frequency: number   // Hz (125, 250, 500, 1000, 2000, 3000, 4000, 6000, 8000)
  intensity: number   // dB HL (-10 a 120, pasos de 5)
  ear: Ear
  conduction: ConductionType
  masked: boolean
  noResponse?: boolean // Sin respuesta a máxima intensidad
}

export interface TonalLiminarData {
  thresholds: ThresholdPoint[]
}

export interface SpeechPoint {
  intensity: number   // dB HL
  percentage: number  // 0-100 discriminación
  ear: Ear
}

export interface ThresholdMeasurement {
  intensity?: number  // dB HL
  mkg?: number        // Masking level dB
}

export interface UMDEntry {
  intensity?: number   // dB HL
  percentage?: number  // 0-100 discriminación
  mkg?: number         // Masking level dB
}

export interface VocalData {
  sdt_od?: ThresholdMeasurement  // Umbral mínimo de detección OD
  sdt_oi?: ThresholdMeasurement  // Umbral mínimo de detección OI
  srt_od?: ThresholdMeasurement  // 50% detección OD
  srt_oi?: ThresholdMeasurement  // 50% detección OI
  umd_od: UMDEntry[]             // Máxima discriminación OD
  umd_oi: UMDEntry[]             // Máxima discriminación OI
  speechPoints?: SpeechPoint[]   // deprecated, retrocompat
}

export function createEmptyVocalData(): VocalData {
  return {
    umd_od: [{}],
    umd_oi: [{}],
  }
}

export interface SISIResult {
  ear: Ear
  frequency: number
  intensity: number
  positiveResponses: number // de 20
}

export interface FowlerStep {
  referenceIntensity: number  // dB en oído referencia
  testIntensity: number       // dB en oído test
}

export interface FowlerResult {
  referenceEar: Ear
  testEar: Ear
  frequency: number
  steps: FowlerStep[]
}

export interface ToneDecayResult {
  ear: Ear
  frequency: number
  initialIntensity: number
  finalIntensity: number
  decayDb: number
  durationSeconds: number
}

export interface LuscherResult {
  ear: Ear
  frequency: number
  intensity: number
  dlDb: number // Umbral diferencial en dB
}

export interface RegerResult {
  ear: Ear
  frequency: number
  intensity: number
  dlDb: number // Limen diferencial en dB
}

export type BekesyJergerType = 'I' | 'II' | 'III' | 'IV' | 'V'

export interface BekesyResult {
  ear: Ear
  jergerType: BekesyJergerType
}

export interface SupraliminarData {
  sisi: SISIResult[]
  fowler: FowlerResult[]
  toneDecay: ToneDecayResult[]
  luscher: LuscherResult[]
  reger: RegerResult[]
  bekesy: BekesyResult[]
}

export interface HighFreqThreshold {
  frequency: number   // Hz (8000, 9000, 10000, 11200, 12500, 14000, 16000)
  intensity: number
  ear: Ear
  noResponse?: boolean
}

export interface HighFreqData {
  thresholds: HighFreqThreshold[]
}

// Clasificación automática
export type HearingLossType = 'conductiva' | 'neurosensorial' | 'mixta' | 'normal'
export type HearingLossGrade = 'normal' | 'leve' | 'moderada' | 'moderada_severa' | 'severa' | 'profunda'

export interface HearingClassificationResult {
  ear: Ear
  pta: number                   // Pure Tone Average (500, 1000, 2000, 4000)
  type: HearingLossType
  grade: HearingLossGrade
  gapDb: number                 // Gap aéreo-óseo promedio
}

// Acumetría (Rinne y Weber)
export type RinneValue = '+' | '-' | 'ne' | 'f-'
export type WeberOdValue = '-' | '<'
export type WeberOiValue = '-' | '>'

export interface AcumetryData {
  rinne_od_500?: RinneValue
  rinne_od_1000?: RinneValue
  rinne_oi_500?: RinneValue
  rinne_oi_1000?: RinneValue
  weber_od_500?: WeberOdValue
  weber_od_1000?: WeberOdValue
  weber_oi_500?: WeberOiValue
  weber_oi_1000?: WeberOiValue
}

// Sesión completa
export interface AudiometrySessionData {
  tonal: TonalLiminarData
  vocal: VocalData
  supraliminar: SupraliminarData
  highFreq: HighFreqData
  acumetry: AcumetryData
  classifications: HearingClassificationResult[]
  notes: string
}

// Sub-vista activa dentro de audiometría
export type AudiometrySubView = 'tonal' | 'vocal' | 'supraliminar' | 'alta_frecuencia'

// Frecuencias estándar
export const STANDARD_FREQUENCIES = [125, 250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
export const HIGH_FREQUENCIES = [8000, 9000, 10000, 11200, 12500, 14000, 16000]

// Grados de pérdida según PTA (BIAP)
export function classifyGrade(pta: number): HearingLossGrade {
  if (pta <= 20) return 'normal'
  if (pta <= 40) return 'leve'
  if (pta <= 55) return 'moderada'
  if (pta <= 70) return 'moderada_severa'
  if (pta <= 90) return 'severa'
  return 'profunda'
}

export function gradeLabel(grade: HearingLossGrade): string {
  const labels: Record<HearingLossGrade, string> = {
    normal: 'Normal',
    leve: 'Leve',
    moderada: 'Moderada',
    moderada_severa: 'Moderada-Severa',
    severa: 'Severa',
    profunda: 'Profunda',
  }
  return labels[grade]
}

export function typeLabel(type: HearingLossType): string {
  const labels: Record<HearingLossType, string> = {
    normal: 'Normal',
    conductiva: 'Conductiva',
    neurosensorial: 'Neurosensorial',
    mixta: 'Mixta',
  }
  return labels[type]
}
