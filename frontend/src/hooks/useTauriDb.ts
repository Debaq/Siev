import { useState, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'

export interface Patient {
  id: number
  first_name: string
  last_name: string
  dni: string | null
  birth_date: string | null // ISO string from Rust
  email: string | null
  phone: string | null
  created_at: string
  session_count: number // Note: Rust struct currently doesn't compute this dynamically in the model
  // We might need to adjust the Rust query or handle it here
}

export interface Session {
  id: number
  patient_id: number
  date: string
  description: string | null
  duration_seconds: number
  video_path: string | null
  data_path: string | null
}

export interface Specialist {
  id: number
  name: string
  created_at: string
}

export function useTauriDb() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const getPatients = useCallback(async (search?: string): Promise<Patient[]> => {
    setLoading(true)
    setError(null)
    try {
      const patients = await invoke<Patient[]>('get_patients', { search: search || null })
      return patients
    } catch (err) {
      console.error('Failed to fetch patients:', err)
      setError(typeof err === 'string' ? err : 'Error al cargar pacientes')
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  const createPatient = useCallback(async (data: any): Promise<{ success: boolean, data?: Patient, error?: string }> => {
    setLoading(true)
    try {
      // Ensure empty strings are sent as null for Option fields if needed, 
      // but Rust handles Option well if we match the DTO.
      // DTO expects: dni: Option<String>, so undefined/null is fine.
      const patient = await invoke<Patient>('create_patient', { data })
      return { success: true, data: patient }
    } catch (err) {
      console.error('Failed to create patient:', err)
      return { success: false, error: typeof err === 'string' ? err : 'Error al crear paciente' }
    } finally {
      setLoading(false)
    }
  }, [])

  const updatePatient = useCallback(async (id: number, data: any): Promise<{ success: boolean, data?: Patient, error?: string }> => {
    setLoading(true)
    try {
      const patient = await invoke<Patient>('update_patient', { id, data })
      return { success: true, data: patient }
    } catch (err) {
      console.error('Failed to update patient:', err)
      return { success: false, error: typeof err === 'string' ? err : 'Error al actualizar paciente' }
    } finally {
      setLoading(false)
    }
  }, [])

  const deletePatient = useCallback(async (id: number): Promise<boolean> => {
    setLoading(true)
    try {
      await invoke('delete_patient', { id })
      return true
    } catch (err) {
      console.error('Failed to delete patient:', err)
      setError(typeof err === 'string' ? err : 'Error al eliminar paciente')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const getSessions = useCallback(async (patientId: number): Promise<Session[]> => {
    try {
      return await invoke<Session[]>('get_sessions', { patientId })
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
      return []
    }
  }, [])

  const createSession = useCallback(async (patientId: number, specialistId: number | null, description: string | null): Promise<Session | null> => {
    try {
      return await invoke<Session>('create_session', { patientId, specialistId, description })
    } catch (err) {
      console.error('Failed to create session:', err)
      return null
    }
  }, [])

  const getSetting = useCallback(async (key: string): Promise<string | null> => {
    try {
      return await invoke<string | null>('get_setting', { key })
    } catch (err) {
      console.error(`Failed to get setting ${key}:`, err)
      return null
    }
  }, [])

  const setSetting = useCallback(async (key: string, value: string): Promise<boolean> => {
    try {
      await invoke('set_setting', { key, value })
      return true
    } catch (err) {
      console.error(`Failed to set setting ${key}:`, err)
      return false
    }
  }, [])

  const getSpecialists = useCallback(async (): Promise<Specialist[]> => {
    try {
      return await invoke<Specialist[]>('get_specialists')
    } catch (err) {
      console.error('Failed to get specialists:', err)
      return []
    }
  }, [])

  const createSpecialist = useCallback(async (name: string): Promise<Specialist | null> => {
    try {
      return await invoke<Specialist>('create_specialist', { name })
    } catch (err) {
      console.error('Failed to create specialist:', err)
      return null
    }
  }, [])

  const deleteSpecialist = useCallback(async (id: number): Promise<boolean> => {
    try {
      await invoke('delete_specialist', { id })
      return true
    } catch (err) {
      console.error('Failed to delete specialist:', err)
      return false
    }
  }, [])

  return {
    loading,
    error,
    getPatients,
    createPatient,
    updatePatient,
    deletePatient,
    getSessions,
    createSession,
    getSetting,
    setSetting,
    getSpecialists,
    createSpecialist,
    deleteSpecialist
  }
}
