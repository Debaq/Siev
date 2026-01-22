import { useState, useEffect } from 'react'
import { 
  Search, Plus, User, Calendar, FileText, Trash2, Edit2, 
  ChevronRight, FolderOpen 
} from 'lucide-react'
import PatientFormModal from './PatientFormModal'
import { useTauriDb, Patient } from '../hooks/useTauriDb'

interface PatientsViewProps {
  onSelectPatient: (patient: Patient) => void
}

function PatientsView({ onSelectPatient }: PatientsViewProps) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [search, setSearch] = useState('')
  
  // DB Hook
  const {
      loading, 
      getPatients, 
      createPatient, 
      updatePatient, 
      deletePatient, 
      getSessions 
  } = useTauriDb()
  
  // Modals State
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null)
  
  // History State
  const [showHistory, setShowHistory] = useState(false)
  const [historyPatient, setHistoryPatient] = useState<Patient | null>(null)
  const [sessions, setSessions] = useState<any[]>([])

  useEffect(() => {
    loadPatients()
  }, [search])

  const loadPatients = async () => {
    const data = await getPatients(search)
    setPatients(data)
  }

  const fetchSessions = async (patient: Patient) => {
    setHistoryPatient(patient)
    setShowHistory(true)
    setSessions([])
    const data = await getSessions(patient.id)
    setSessions(data)
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

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este paciente?')) return
    const success = await deletePatient(id)
    if (success) loadPatients()
  }

  const handleEdit = (patient: Patient) => {
    setEditingPatient(patient)
    setShowForm(true)
  }

  const handleCreate = () => {
    setEditingPatient(null)
    setShowForm(true)
  }

  return (
    <div className="h-full flex flex-col bg-dark-950 text-dark-100 p-6 overflow-hidden">
      
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
                  <tr key={patient.id} className="hover:bg-dark-800/50 transition-colors group">
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

      {/* Patient Form Modal - Extracted for performance */}
      {showForm && (
        <PatientFormModal 
            patient={editingPatient}
            onClose={() => setShowForm(false)}
            onSave={handleSavePatient}
        />
      )}

      {/* History Modal */}
      {showHistory && historyPatient && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700 rounded-lg shadow-2xl w-full max-w-4xl h-[80vh] flex flex-col overflow-hidden animate-fade-in">
            <div className="px-6 py-4 border-b border-dark-800 flex justify-between items-center bg-dark-850 shrink-0">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <FolderOpen className="w-5 h-5 text-purple-400" />
                  Historial Clínico
                </h3>
                <p className="text-xs text-dark-400">
                  {historyPatient.last_name}, {historyPatient.first_name} — {historyPatient.dni}
                </p>
              </div>
              <button onClick={() => setShowHistory(false)} className="text-dark-400 hover:text-white">&times;</button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                {sessions.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-dark-500">
                        <FileText className="w-12 h-12 mb-4 opacity-20" />
                        <p>No hay evaluaciones registradas para este paciente.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {sessions.map((session) => (
                            <div key={session.id} className="bg-dark-800 border border-dark-700 rounded-lg p-4 hover:border-siev-500/50 transition-colors group">
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
                                    <span className="text-xs bg-dark-950 text-dark-300 px-2 py-0.5 rounded border border-dark-700">
                                        {session.duration_seconds}s
                                    </span>
                                </div>
                                <p className="text-sm text-dark-300 mb-4 line-clamp-2">
                                    {session.description || 'Sin descripción'}
                                </p>
                                <div className="flex gap-2">
                                    <button className="flex-1 btn btn-secondary text-xs py-1.5">
                                        Ver Informe
                                    </button>
                                    <button className="flex-1 btn btn-primary text-xs py-1.5">
                                        Reproducir
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            <div className="p-4 border-t border-dark-800 bg-dark-850 flex justify-end gap-3 shrink-0">
                <button 
                  onClick={() => {
                      setShowHistory(false)
                      onSelectPatient(historyPatient)
                  }} 
                  className="btn btn-primary"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Nueva Evaluación VNG
                </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PatientsView