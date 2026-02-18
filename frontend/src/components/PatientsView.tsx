import { useState, useEffect } from 'react'
import {
  Search, Plus, User, Calendar, FileText, Trash2, Edit2,
  ChevronRight, ChevronDown, FolderOpen, ArrowLeft, Mail, Phone, CreditCard, Play
} from 'lucide-react'
import PatientFormModal from './PatientFormModal'
import ConfirmDialog from './ConfirmDialog'
import { useTauriDb, Patient, Recording } from '../hooks/useTauriDb'

interface PatientsViewProps {
  onSelectPatient: (patient: Patient) => void
  onReviewRecording?: (recordingId: number) => void
  onViewReport?: (recordingId: number) => void
}

function PatientsView({ onSelectPatient, onReviewRecording, onViewReport }: PatientsViewProps) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [search, setSearch] = useState('')

  // DB Hook
  const {
      loading,
      getPatients,
      createPatient,
      updatePatient,
      deletePatient,
      deleteSession,
      deleteRecording,
      getSessions,
      getRecordings
  } = useTauriDb()

  // Modals State
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null)
  const [confirmAction, setConfirmAction] = useState<{ message: string; action: () => void } | null>(null)

  // History State - panel deslizante
  const [historyPatient, setHistoryPatient] = useState<Patient | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState<any[]>([])
  const [expandedSessionId, setExpandedSessionId] = useState<number | null>(null)
  const [sessionRecordings, setSessionRecordings] = useState<Record<number, Recording[]>>({})

  useEffect(() => {
    loadPatients()
  }, [search])

  const loadPatients = async () => {
    const data = await getPatients(search)
    setPatients(data)
  }

  const fetchSessions = async (patient: Patient) => {
    setHistoryPatient(patient)
    setSessions([])
    // Pequeño delay para que el panel se monte antes de animar
    requestAnimationFrame(() => setShowHistory(true))
    const data = await getSessions(patient.id)
    setSessions(data)
  }

  const closeHistory = () => {
    setShowHistory(false)
    // Esperar a que termine la animación antes de limpiar
    setTimeout(() => {
      setHistoryPatient(null)
      setSessions([])
    }, 300)
  }

  const handleSavePatient = async (data: any) => {
    let result
    if (editingPatient) {
        result = await updatePatient(editingPatient.id, data)
    } else {
        result = await createPatient(data)
    }

    if (result.success) {
        setShowForm(false)
        setEditingPatient(null)
        loadPatients()
        return { success: true }
    } else {
        return { success: false, error: result.error }
    }
  }

  const handleDelete = (id: number) => {
    setConfirmAction({
      message: '¿Estás seguro de eliminar este paciente?',
      action: async () => {
        const success = await deletePatient(id)
        if (success) loadPatients()
      }
    })
  }

  const handleEdit = (patient: Patient) => {
    setEditingPatient(patient)
    setShowForm(true)
  }

  const handleCreate = () => {
    setEditingPatient(null)
    setShowForm(true)
  }

  const handleDeleteSession = (sessionId: number) => {
    setConfirmAction({
      message: '¿Eliminar esta evaluación? Se borrarán todos los datos y archivos asociados.',
      action: async () => {
        const success = await deleteSession(sessionId)
        if (success && historyPatient) {
          const data = await getSessions(historyPatient.id)
          setSessions(data)
          loadPatients()
        }
      }
    })
  }

  const handleDeleteRecording = (recordingId: number, sessionId: number) => {
    setConfirmAction({
      message: '¿Eliminar esta grabación?',
      action: async () => {
        const success = await deleteRecording(recordingId)
        if (success) {
          const recs = await getRecordings(sessionId)
          setSessionRecordings(prev => ({ ...prev, [sessionId]: recs }))
          if (historyPatient) {
            const data = await getSessions(historyPatient.id)
            setSessions(data)
            loadPatients()
          }
        }
      }
    })
  }

  const toggleSessionExpand = async (sessionId: number) => {
    if (expandedSessionId === sessionId) {
      setExpandedSessionId(null)
      return
    }
    setExpandedSessionId(sessionId)
    if (!sessionRecordings[sessionId]) {
      const recs = await getRecordings(sessionId)
      setSessionRecordings(prev => ({ ...prev, [sessionId]: recs }))
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return s > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${m}min`
  }

  return (
    <div className="h-full flex flex-col bg-dark-950 text-dark-100 p-6 overflow-hidden">

      {/* Contenedor de paneles deslizantes */}
      <div className="flex-1 flex flex-col overflow-hidden relative">

        {/* Panel 1: Lista de pacientes */}
        <div
          className="absolute inset-0 flex flex-col transition-all duration-300 ease-in-out"
          style={{
            transform: showHistory ? 'translateX(-100%)' : 'translateX(0)',
            opacity: showHistory ? 0 : 1,
          }}
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <User className="w-6 h-6 text-siev-500" />
                Gestión de Pacientes
              </h1>
              <p className="text-dark-400 text-sm mt-1">Administra historias clínicas y sesiones</p>
            </div>
            <button
              onClick={handleCreate}
              className="btn btn-primary px-4 py-2 h-10"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Paciente
            </button>
          </div>

          {/* Toolbar */}
          <div className="flex gap-4 mb-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
              <input
                type="text"
                placeholder="Buscar por nombre o DNI..."
                className="w-full bg-dark-900 border border-dark-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:border-siev-500 outline-none"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {/* Table Area */}
          <div className="flex-1 bg-dark-900 border border-dark-800 rounded-lg overflow-hidden flex flex-col">
            <div className="overflow-y-auto custom-scrollbar flex-1">
              <table className="w-full text-left border-collapse">
                <thead className="bg-dark-800 text-dark-400 text-xs uppercase sticky top-0 z-10">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Paciente</th>
                    <th className="px-6 py-3 font-semibold">DNI</th>
                    <th className="px-6 py-3 font-semibold">Contacto</th>
                    <th className="px-6 py-3 font-semibold text-center">Sesiones</th>
                    <th className="px-6 py-3 font-semibold text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-800 text-sm">
                  {loading ? (
                    <tr><td colSpan={5} className="text-center py-8 text-dark-500">Cargando...</td></tr>
                  ) : !Array.isArray(patients) || patients.length === 0 ? (
                    <tr><td colSpan={5} className="text-center py-8 text-dark-500">No se encontraron pacientes</td></tr>
                  ) : (
                    patients.map(patient => (
                      <tr
                        key={patient.id}
                        className="hover:bg-dark-800/50 transition-colors group cursor-pointer"
                        onDoubleClick={() => {
                          if (patient.session_count > 0) {
                            fetchSessions(patient)
                          } else {
                            onSelectPatient(patient)
                          }
                        }}
                      >
                        <td className="px-6 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-siev-900/50 flex items-center justify-center text-siev-400 font-bold border border-siev-800">
                              {(patient.first_name?.[0] || '?').toUpperCase()}{(patient.last_name?.[0] || '').toUpperCase()}
                            </div>
                            <div>
                              <div className="font-medium text-white">{patient.last_name}, {patient.first_name}</div>
                              <div className="text-xs text-dark-500">Registrado: {new Date(patient.created_at).toLocaleDateString()}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-3 text-dark-300 font-mono">{patient.dni || '-'}</td>
                        <td className="px-6 py-3 text-dark-300">
                          <div className="flex flex-col text-xs">
                            <span>{patient.email}</span>
                            <span>{patient.phone}</span>
                          </div>
                        </td>
                        <td className="px-6 py-3 text-center">
                          <span className="inline-flex items-center px-2 py-1 rounded bg-dark-800 text-xs font-medium text-dark-300 border border-dark-700">
                            {patient.session_count}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right">
                          <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => onSelectPatient(patient)}
                              className="p-1.5 hover:bg-siev-900/50 text-siev-400 rounded transition-colors"
                              title="Nueva Evaluación VNG"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => fetchSessions(patient)}
                              className="p-1.5 hover:bg-purple-900/30 text-purple-400 rounded transition-colors"
                              title="Ver Historial"
                            >
                              <FolderOpen className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleEdit(patient)}
                              className="p-1.5 hover:bg-blue-900/30 text-blue-400 rounded transition-colors"
                              title="Editar"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(patient.id)}
                              className="p-1.5 hover:bg-red-900/30 text-red-400 rounded transition-colors"
                              title="Eliminar"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Panel 2: Historial del paciente (desliza desde la derecha) */}
        {historyPatient && (
          <div
            className="absolute inset-0 flex flex-col transition-all duration-300 ease-in-out"
            style={{
              transform: showHistory ? 'translateX(0)' : 'translateX(100%)',
              opacity: showHistory ? 1 : 0,
            }}
          >
            {/* Header del historial */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-4">
                <button
                  onClick={closeHistory}
                  className="p-2 hover:bg-dark-800 rounded-lg transition-colors text-dark-400 hover:text-white"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-siev-900/50 flex items-center justify-center text-siev-400 font-bold text-lg border border-siev-800">
                    {(historyPatient.first_name?.[0] || '?').toUpperCase()}{(historyPatient.last_name?.[0] || '').toUpperCase()}
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white">
                      {historyPatient.last_name}, {historyPatient.first_name}
                    </h1>
                    <div className="flex items-center gap-4 text-dark-400 text-sm mt-0.5">
                      {historyPatient.dni && (
                        <span className="flex items-center gap-1">
                          <CreditCard className="w-3.5 h-3.5" />
                          {historyPatient.dni}
                        </span>
                      )}
                      {historyPatient.email && (
                        <span className="flex items-center gap-1">
                          <Mail className="w-3.5 h-3.5" />
                          {historyPatient.email}
                        </span>
                      )}
                      {historyPatient.phone && (
                        <span className="flex items-center gap-1">
                          <Phone className="w-3.5 h-3.5" />
                          {historyPatient.phone}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  closeHistory()
                  onSelectPatient(historyPatient)
                }}
                className="btn btn-primary px-4 py-2 h-10"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nueva Evaluación VNG
              </button>
            </div>

            {/* Sesiones */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {sessions.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-dark-500">
                  <FileText className="w-12 h-12 mb-4 opacity-20" />
                  <p>No hay evaluaciones registradas para este paciente.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sessions.map((session) => {
                    const isExpanded = expandedSessionId === session.id
                    const recordings = sessionRecordings[session.id] || []
                    const hasMultipleRecordings = session.recording_count > 1

                    return (
                      <div key={session.id} className="bg-dark-900 border border-dark-800 rounded-lg overflow-hidden hover:border-siev-500/30 transition-colors">
                        {/* Session header */}
                        <div className="p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-dark-400" />
                              <span className="text-sm font-medium text-white">
                                {new Date(session.date).toLocaleDateString()}
                              </span>
                              <span className="text-xs text-dark-500">
                                {new Date(session.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                              </span>
                            </div>
                            {session.protocol_type && (
                              <span className="text-xs bg-siev-900/50 text-siev-300 px-2 py-0.5 rounded border border-siev-800/50">
                                {session.protocol_type}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-dark-300 mb-3">
                            {session.description || 'Sin descripcion'}
                          </p>
                          <div className="text-xs text-dark-500 mb-3">
                            {session.recording_count} {session.recording_count === 1 ? 'prueba' : 'pruebas'}
                          </div>

                          <div className="flex gap-2">
                            {hasMultipleRecordings ? (
                              <button
                                className="flex-1 btn btn-secondary text-xs py-1.5"
                                onClick={() => toggleSessionExpand(session.id)}
                              >
                                {isExpanded ? <ChevronDown className="w-3 h-3 mr-1" /> : <ChevronRight className="w-3 h-3 mr-1" />}
                                {isExpanded ? 'Colapsar' : 'Expandir'}
                              </button>
                            ) : (
                              <>
                                <button
                                  className="flex-1 btn btn-secondary text-xs py-1.5"
                                  onClick={async () => {
                                    // Single recording: load and navigate directly
                                    let recs = sessionRecordings[session.id]
                                    if (!recs) {
                                      recs = await getRecordings(session.id)
                                      setSessionRecordings(prev => ({ ...prev, [session.id]: recs }))
                                    }
                                    if (recs.length > 0) {
                                      closeHistory()
                                      onViewReport?.(recs[0].id)
                                    }
                                  }}
                                >
                                  Ver Informe
                                </button>
                                <button
                                  className="flex-1 btn btn-primary text-xs py-1.5"
                                  onClick={async () => {
                                    let recs = sessionRecordings[session.id]
                                    if (!recs) {
                                      recs = await getRecordings(session.id)
                                      setSessionRecordings(prev => ({ ...prev, [session.id]: recs }))
                                    }
                                    if (recs.length > 0) {
                                      closeHistory()
                                      onReviewRecording?.(recs[0].id)
                                    }
                                  }}
                                >
                                  <Play className="w-3 h-3 mr-1" />
                                  Reproducir
                                </button>
                              </>
                            )}
                            <button
                              className="p-1.5 hover:bg-red-900/30 text-red-400 rounded transition-colors"
                              title="Eliminar evaluacion"
                              onClick={() => handleDeleteSession(session.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Expanded recordings list */}
                        {isExpanded && (
                          <div className="border-t border-dark-800">
                            {recordings.length === 0 ? (
                              <div className="p-4 text-center text-dark-500 text-xs">
                                Cargando grabaciones...
                              </div>
                            ) : (
                              <div className="divide-y divide-dark-800">
                                {recordings.map((rec, idx) => (
                                  <div key={rec.id} className="px-4 py-3 flex items-center gap-3 hover:bg-dark-800/50 transition-colors">
                                    <span className="text-xs text-dark-500 w-5 text-right font-mono">{idx + 1}.</span>
                                    <div className="flex-1 min-w-0">
                                      <span className="text-sm text-white truncate block">
                                        {rec.label || rec.test_type}
                                      </span>
                                      <span className="text-xs text-dark-500">
                                        {formatDuration(rec.duration_seconds)}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                      <button
                                        className="px-2 py-1 text-xs bg-dark-800 hover:bg-dark-700 text-dark-300 rounded transition-colors"
                                        onClick={() => {
                                          closeHistory()
                                          onViewReport?.(rec.id)
                                        }}
                                      >
                                        Informe
                                      </button>
                                      <button
                                        className="px-2 py-1 text-xs bg-siev-600 hover:bg-siev-700 text-white rounded transition-colors"
                                        onClick={() => {
                                          closeHistory()
                                          onReviewRecording?.(rec.id)
                                        }}
                                      >
                                        Revisar
                                      </button>
                                      <button
                                        className="p-1 hover:bg-red-900/30 text-red-400 rounded transition-colors"
                                        title="Eliminar grabacion"
                                        onClick={() => handleDeleteRecording(rec.id, session.id)}
                                      >
                                        <Trash2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Patient Form Modal */}
      {showForm && (
        <PatientFormModal
            patient={editingPatient}
            onClose={() => setShowForm(false)}
            onSave={handleSavePatient}
        />
      )}

      {/* Confirm Dialog */}
      {confirmAction && (
        <ConfirmDialog
          message={confirmAction.message}
          onConfirm={() => { confirmAction.action(); setConfirmAction(null) }}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}

export default PatientsView