import { useState, useEffect } from 'react'
import { SmartDateInput } from './SmartDateInput'

interface PatientFormModalProps {
  patient: any | null
  onClose: () => void
  onSave: (data: any) => Promise<{ success: boolean, error?: string }>
}

export default function PatientFormModal({ patient, onClose, onSave }: PatientFormModalProps) {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    dni: '',
    email: '',
    phone: '',
    birth_date: ''
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (patient) {
      setFormData({
        first_name: patient.first_name,
        last_name: patient.last_name,
        dni: patient.dni || '',
        email: patient.email || '',
        phone: patient.phone || '',
        birth_date: patient.birth_date ? patient.birth_date.split('T')[0] : ''
      })
    }
  }, [patient])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const result = await onSave(formData)
      if (!result.success && result.error) {
          setError(result.error)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden animate-fade-in">
        <div className="px-6 py-4 border-b border-dark-800 flex justify-between items-center bg-dark-850">
          <h3 className="text-lg font-bold text-white">
            {patient ? 'Editar Paciente' : 'Nuevo Paciente'}
          </h3>
          <button onClick={onClose} className="text-dark-400 hover:text-white">&times;</button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-900/30 border border-red-800/50 text-red-300 px-4 py-2 rounded text-sm mb-4">
                {error}
            </div>
          )}
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
              <SmartDateInput 
                value={formData.birth_date}
                onChange={val => setFormData({...formData, birth_date: val})}
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
              onClick={onClose} 
              className="btn btn-secondary"
              disabled={saving}
            >
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Guardando...' : (patient ? 'Guardar Cambios' : 'Crear Paciente')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
