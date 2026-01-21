import { useState, useEffect } from 'react'
import { 
  Search, Plus, User, Calendar, FileText, Trash2, Edit2, 
  ChevronRight, MoreVertical, FolderOpen 
} from 'lucide-react'

interface Patient {
  id: number
  first_name: string
  last_name: string
  dni: string
  birth_date: string | null
  email: string | null
  phone: string | null
  created_at: string
  session_count: number
}

interface PatientsViewProps {
  apiUrl: string
  onSelectPatient: (patient: Patient) => void
}

function PatientsView({ apiUrl, onSelectPatient }: PatientsViewProps) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null)

  // Form State
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    dni: '',
    email: '',
    phone: '',
    birth_date: ''
  })

  useEffect(() => {
    fetchPatients()
  }, [search])

  const fetchPatients = async () => {
    setLoading(true)
    try {
      const query = search ? `?search=${search}` : ''
      const res = await fetch(`${apiUrl}/patients${query}`)
      if (res.ok) {
        const data = await res.json()
        setPatients(data)
      }
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const url = editingPatient 
        ? `${apiUrl}/patients/${editingPatient.id}`
        : `${apiUrl}/patients`
      
      const method = editingPatient ? 'PUT' : 'POST'
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (res.ok) {
        setShowForm(false)
        setEditingPatient(null)
        setFormData({ first_name: '', last_name: '', dni: '', email: '', phone: '', birth_date: '' })
        fetchPatients()
      }
    } catch (error) {
      console.error(error)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este paciente?')) return
    try {
      await fetch(`${apiUrl}/patients/${id}`, { method: 'DELETE' })
      fetchPatients()
    } catch (error) { console.error(error) }
  }

  const handleEdit = (patient: Patient) => {
    setEditingPatient(patient)
    setFormData({
      first_name: patient.first_name,
      last_name: patient.last_name,
      dni: patient.dni || '',
      email: patient.email || '',
      phone: patient.phone || '',
      birth_date: patient.birth_date ? patient.birth_date.split('T')[0] : ''
    })
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
          onClick={() => {
            setEditingPatient(null)
            setFormData({ first_name: '', last_name: '', dni: '', email: '', phone: '', birth_date: '' })
            setShowForm(true)
          }}
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
                          title="Iniciar Sesión"
                        >
                          <ChevronRight className="w-4 h-4" />
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

      {/* Modal Form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden animate-fade-in">
            <div className="px-6 py-4 border-b border-dark-800 flex justify-between items-center bg-dark-850">
              <h3 className="text-lg font-bold text-white">
                {editingPatient ? 'Editar Paciente' : 'Nuevo Paciente'}
              </h3>
              <button onClick={() => setShowForm(false)} className="text-dark-400 hover:text-white">&times;</button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">Nombre</label>
                  <input 
                    required 
                    className="input" 
                    value={formData.first_name}
                    onChange={e => setFormData({...formData, first_name: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">Apellido</label>
                  <input 
                    required 
                    className="input" 
                    value={formData.last_name}
                    onChange={e => setFormData({...formData, last_name: e.target.value})}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">DNI</label>
                  <input 
                    className="input" 
                    value={formData.dni}
                    onChange={e => setFormData({...formData, dni: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">Fecha Nacimiento</label>
                  <input 
                    type="date"
                    className="input" 
                    value={formData.birth_date}
                    onChange={e => setFormData({...formData, birth_date: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">Email</label>
                  <input 
                    type="email"
                    className="input" 
                    value={formData.email}
                    onChange={e => setFormData({...formData, email: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-dark-400 mb-1">Teléfono</label>
                  <input 
                    className="input" 
                    value={formData.phone}
                    onChange={e => setFormData({...formData, phone: e.target.value})}
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setShowForm(false)} 
                  className="btn btn-secondary"
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingPatient ? 'Guardar Cambios' : 'Crear Paciente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default PatientsView
