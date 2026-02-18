import { useState, useCallback, useMemo } from 'react'
import { invoke } from '@tauri-apps/api/core'
import type {
  Ear,
  ConductionType,
  ThresholdPoint,
  SISIResult,
  FowlerResult,
  ToneDecayResult,
  LuscherResult,
  RegerResult,
  BekesyResult,
  HighFreqThreshold,
  AudiometrySessionData,
  AudiometrySubView,
  HearingClassificationResult,
  HearingLossType,
  VocalData,
  UMDEntry,
  AcumetryData,
} from '../types/audiometry'
import { classifyGrade, createEmptyVocalData } from '../types/audiometry'

const PTA_FREQUENCIES = [500, 1000, 2000, 4000]

function createEmptySession(): AudiometrySessionData {
  return {
    tonal: { thresholds: [] },
    vocal: createEmptyVocalData(),
    supraliminar: { sisi: [], fowler: [], toneDecay: [], luscher: [], reger: [], bekesy: [] },
    highFreq: { thresholds: [] },
    acumetry: {},
    classifications: [],
    notes: '',
  }
}

function migrateVocalData(vocal: any): VocalData {
  // Ya migrado
  if (Array.isArray(vocal.umd_od)) return vocal as VocalData

  const result = createEmptyVocalData()

  // srt_od/oi: number → ThresholdMeasurement
  if (typeof vocal.srt_od === 'number') {
    result.srt_od = { intensity: vocal.srt_od }
  }
  if (typeof vocal.srt_oi === 'number') {
    result.srt_oi = { intensity: vocal.srt_oi }
  }

  // wrs → primer UMDEntry
  if (vocal.wrs_od !== undefined || vocal.wrs_od_intensity !== undefined) {
    result.umd_od = [{ intensity: vocal.wrs_od_intensity, percentage: vocal.wrs_od }]
  }
  if (vocal.wrs_oi !== undefined || vocal.wrs_oi_intensity !== undefined) {
    result.umd_oi = [{ intensity: vocal.wrs_oi_intensity, percentage: vocal.wrs_oi }]
  }

  // speechPoints → entradas UMD adicionales
  if (Array.isArray(vocal.speechPoints)) {
    for (const p of vocal.speechPoints) {
      const entry: UMDEntry = { intensity: p.intensity, percentage: p.percentage }
      if (p.ear === 'od') result.umd_od.push(entry)
      else result.umd_oi.push(entry)
    }
  }

  // Asegurar al menos 1 fila vacía al final
  const lastOD = result.umd_od[result.umd_od.length - 1]
  if (lastOD && (lastOD.intensity !== undefined || lastOD.percentage !== undefined)) {
    result.umd_od.push({})
  }
  const lastOI = result.umd_oi[result.umd_oi.length - 1]
  if (lastOI && (lastOI.intensity !== undefined || lastOI.percentage !== undefined)) {
    result.umd_oi.push({})
  }

  return result
}

function computeClassifications(thresholds: ThresholdPoint[]): HearingClassificationResult[] {
  const results: HearingClassificationResult[] = []

  for (const ear of ['od', 'oi'] as Ear[]) {
    const airThresholds = thresholds.filter(
      t => t.ear === ear && t.conduction === 'aerea' && !t.noResponse
    )
    const boneThresholds = thresholds.filter(
      t => t.ear === ear && t.conduction === 'osea' && !t.noResponse
    )

    // PTA: promedio de 500, 1000, 2000, 4000 Hz vía aérea
    const ptaValues = PTA_FREQUENCIES
      .map(f => airThresholds.find(t => t.frequency === f))
      .filter(Boolean) as ThresholdPoint[]

    if (ptaValues.length === 0) continue

    const pta = ptaValues.reduce((sum, t) => sum + t.intensity, 0) / ptaValues.length

    // Gap aéreo-óseo promedio
    let gapDb = 0
    let gapCount = 0
    for (const freq of PTA_FREQUENCIES) {
      const air = airThresholds.find(t => t.frequency === freq)
      const bone = boneThresholds.find(t => t.frequency === freq)
      if (air && bone) {
        gapDb += air.intensity - bone.intensity
        gapCount++
      }
    }
    gapDb = gapCount > 0 ? gapDb / gapCount : 0

    // Clasificar tipo
    let type: HearingLossType = 'normal'
    if (pta > 20) {
      if (gapDb >= 10 && boneThresholds.length > 0) {
        // Hay gap significativo
        const avgBone = ptaValues.length > 0
          ? PTA_FREQUENCIES
              .map(f => boneThresholds.find(t => t.frequency === f))
              .filter(Boolean)
              .reduce((sum, t) => sum + t!.intensity, 0) /
            Math.max(1, PTA_FREQUENCIES.map(f => boneThresholds.find(t => t.frequency === f)).filter(Boolean).length)
          : 0
        type = avgBone > 20 ? 'mixta' : 'conductiva'
      } else {
        type = 'neurosensorial'
      }
    }

    results.push({
      ear,
      pta: Math.round(pta * 10) / 10,
      type,
      grade: classifyGrade(pta),
      gapDb: Math.round(gapDb * 10) / 10,
    })
  }

  return results
}

export function useAudiometry(_sessionId: number | null, recordingId: number | null) {
  const [data, setData] = useState<AudiometrySessionData>(createEmptySession)
  const [activeEar, setActiveEar] = useState<Ear>('od')
  const [activeConduction, setActiveConduction] = useState<ConductionType>('aerea')
  const [activeMasking, setActiveMasking] = useState(false)
  const [activeSubView, setActiveSubView] = useState<AudiometrySubView>('tonal')
  const [saving, setSaving] = useState(false)

  // Clasificaciones computadas
  const classifications = useMemo(
    () => computeClassifications(data.tonal.thresholds),
    [data.tonal.thresholds]
  )

  // --- Tonal Liminar ---
  const addThreshold = useCallback((frequency: number, intensity: number) => {
    setData(prev => {
      const existing = prev.tonal.thresholds.findIndex(
        t =>
          t.frequency === frequency &&
          t.ear === activeEar &&
          t.conduction === activeConduction &&
          t.masked === activeMasking
      )
      const point: ThresholdPoint = {
        frequency,
        intensity,
        ear: activeEar,
        conduction: activeConduction,
        masked: activeMasking,
      }
      const thresholds = [...prev.tonal.thresholds]
      if (existing >= 0) {
        thresholds[existing] = point
      } else {
        thresholds.push(point)
      }
      return { ...prev, tonal: { ...prev.tonal, thresholds } }
    })
  }, [activeEar, activeConduction, activeMasking])

  const removeThreshold = useCallback((frequency: number, ear: Ear, conduction: ConductionType, masked: boolean) => {
    setData(prev => ({
      ...prev,
      tonal: {
        ...prev.tonal,
        thresholds: prev.tonal.thresholds.filter(
          t => !(t.frequency === frequency && t.ear === ear && t.conduction === conduction && t.masked === masked)
        ),
      },
    }))
  }, [])

  const markNoResponse = useCallback((frequency: number) => {
    setData(prev => {
      const existing = prev.tonal.thresholds.findIndex(
        t =>
          t.frequency === frequency &&
          t.ear === activeEar &&
          t.conduction === activeConduction &&
          t.masked === activeMasking
      )
      const point: ThresholdPoint = {
        frequency,
        intensity: 120,
        ear: activeEar,
        conduction: activeConduction,
        masked: activeMasking,
        noResponse: true,
      }
      const thresholds = [...prev.tonal.thresholds]
      if (existing >= 0) {
        thresholds[existing] = point
      } else {
        thresholds.push(point)
      }
      return { ...prev, tonal: { ...prev.tonal, thresholds } }
    })
  }, [activeEar, activeConduction, activeMasking])

  // --- Vocal ---
  const updateSDT = useCallback((ear: Ear, field: 'intensity' | 'mkg', value: number | undefined) => {
    setData(prev => {
      const key = ear === 'od' ? 'sdt_od' : 'sdt_oi'
      const current = prev.vocal[key] || {}
      return {
        ...prev,
        vocal: { ...prev.vocal, [key]: { ...current, [field]: value } },
      }
    })
  }, [])

  const updateSRT = useCallback((ear: Ear, field: 'intensity' | 'mkg', value: number | undefined) => {
    setData(prev => {
      const key = ear === 'od' ? 'srt_od' : 'srt_oi'
      const current = prev.vocal[key] || {}
      return {
        ...prev,
        vocal: { ...prev.vocal, [key]: { ...current, [field]: value } },
      }
    })
  }, [])

  const updateUMD = useCallback((ear: Ear, index: number, field: keyof UMDEntry, value: number | undefined) => {
    setData(prev => {
      const key = ear === 'od' ? 'umd_od' : 'umd_oi'
      const arr = [...prev.vocal[key]]
      arr[index] = { ...arr[index], [field]: value }
      // Auto-grow: si la última fila tiene datos, agregar fila vacía
      const last = arr[arr.length - 1]
      if (last && (last.intensity !== undefined || last.percentage !== undefined)) {
        arr.push({})
      }
      return { ...prev, vocal: { ...prev.vocal, [key]: arr } }
    })
  }, [])

  const removeUMD = useCallback((ear: Ear, index: number) => {
    setData(prev => {
      const key = ear === 'od' ? 'umd_od' : 'umd_oi'
      let arr = prev.vocal[key].filter((_, i) => i !== index)
      // Mantener mínimo 1 fila vacía
      if (arr.length === 0) arr = [{}]
      return { ...prev, vocal: { ...prev.vocal, [key]: arr } }
    })
  }, [])

  // --- Supraliminar ---
  const addSISI = useCallback((result: SISIResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, sisi: [...prev.supraliminar.sisi, result] },
    }))
  }, [])

  const removeSISI = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        sisi: prev.supraliminar.sisi.filter((_, i) => i !== index),
      },
    }))
  }, [])

  const addFowler = useCallback((result: FowlerResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, fowler: [...prev.supraliminar.fowler, result] },
    }))
  }, [])

  const removeFowler = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        fowler: prev.supraliminar.fowler.filter((_, i) => i !== index),
      },
    }))
  }, [])

  const addToneDecay = useCallback((result: ToneDecayResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, toneDecay: [...prev.supraliminar.toneDecay, result] },
    }))
  }, [])

  const removeToneDecay = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        toneDecay: prev.supraliminar.toneDecay.filter((_, i) => i !== index),
      },
    }))
  }, [])

  const addLuscher = useCallback((result: LuscherResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, luscher: [...prev.supraliminar.luscher, result] },
    }))
  }, [])

  const removeLuscher = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        luscher: prev.supraliminar.luscher.filter((_, i) => i !== index),
      },
    }))
  }, [])

  const addReger = useCallback((result: RegerResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, reger: [...prev.supraliminar.reger, result] },
    }))
  }, [])

  const removeReger = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        reger: prev.supraliminar.reger.filter((_, i) => i !== index),
      },
    }))
  }, [])

  const addBekesy = useCallback((result: BekesyResult) => {
    setData(prev => ({
      ...prev,
      supraliminar: { ...prev.supraliminar, bekesy: [...prev.supraliminar.bekesy, result] },
    }))
  }, [])

  const removeBekesy = useCallback((index: number) => {
    setData(prev => ({
      ...prev,
      supraliminar: {
        ...prev.supraliminar,
        bekesy: prev.supraliminar.bekesy.filter((_, i) => i !== index),
      },
    }))
  }, [])

  // --- Altas Frecuencias ---
  const addHighFreqThreshold = useCallback((frequency: number, intensity: number) => {
    setData(prev => {
      const existing = prev.highFreq.thresholds.findIndex(
        t => t.frequency === frequency && t.ear === activeEar
      )
      const point: HighFreqThreshold = { frequency, intensity, ear: activeEar }
      const thresholds = [...prev.highFreq.thresholds]
      if (existing >= 0) {
        thresholds[existing] = point
      } else {
        thresholds.push(point)
      }
      return { ...prev, highFreq: { ...prev.highFreq, thresholds } }
    })
  }, [activeEar])

  const removeHighFreqThreshold = useCallback((frequency: number, ear: Ear) => {
    setData(prev => ({
      ...prev,
      highFreq: {
        ...prev.highFreq,
        thresholds: prev.highFreq.thresholds.filter(
          t => !(t.frequency === frequency && t.ear === ear)
        ),
      },
    }))
  }, [])

  // --- Acumetría ---
  const updateAcumetry = useCallback((field: keyof AcumetryData, value: string | undefined) => {
    setData(prev => ({
      ...prev,
      acumetry: { ...prev.acumetry, [field]: value },
    }))
  }, [])

  // --- Notas ---
  const setNotes = useCallback((notes: string) => {
    setData(prev => ({ ...prev, notes }))
  }, [])

  // --- Limpiar ---
  const clearAll = useCallback(() => {
    setData(createEmptySession())
  }, [])

  // --- Guardar ---
  const save = useCallback(async () => {
    if (!recordingId) return false
    setSaving(true)
    try {
      const sessionData = { ...data, classifications }
      await invoke('save_vng_test_result', {
        recordingId,
        resultType: 'audiometry',
        resultsJson: JSON.stringify(sessionData),
      })
      return true
    } catch (err) {
      console.error('Error guardando audiometría:', err)
      return false
    } finally {
      setSaving(false)
    }
  }, [data, classifications, recordingId])

  // --- Cargar datos existentes ---
  const load = useCallback(async () => {
    if (!recordingId) return
    try {
      const result = await invoke<{ results_json: string } | null>('get_vng_test_result', {
        recordingId,
      })
      if (result?.results_json) {
        const parsed = JSON.parse(result.results_json) as AudiometrySessionData
        parsed.vocal = migrateVocalData(parsed.vocal)
        if (!parsed.acumetry) parsed.acumetry = {}
        if (!parsed.supraliminar.luscher) parsed.supraliminar.luscher = []
        if (!parsed.supraliminar.reger) parsed.supraliminar.reger = []
        if (!parsed.supraliminar.bekesy) parsed.supraliminar.bekesy = []
        setData(parsed)
      }
    } catch {
      // No hay datos previos, mantener vacío
    }
  }, [recordingId])

  return {
    // Estado
    data,
    activeEar,
    activeConduction,
    activeMasking,
    activeSubView,
    classifications,
    saving,

    // Setters de estado
    setActiveEar,
    setActiveConduction,
    setActiveMasking,
    setActiveSubView,

    // Acciones tonal
    addThreshold,
    removeThreshold,
    markNoResponse,

    // Acciones vocal
    updateSDT,
    updateSRT,
    updateUMD,
    removeUMD,

    // Acciones supraliminar
    addSISI,
    removeSISI,
    addFowler,
    removeFowler,
    addToneDecay,
    removeToneDecay,
    addLuscher,
    removeLuscher,
    addReger,
    removeReger,
    addBekesy,
    removeBekesy,

    // Acciones altas frecuencias
    addHighFreqThreshold,
    removeHighFreqThreshold,

    // Acumetría
    updateAcumetry,

    // Generales
    setNotes,
    clearAll,
    save,
    load,
  }
}
