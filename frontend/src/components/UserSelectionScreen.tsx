import { useState, useEffect } from 'react'
import { Plus, User, Trash2 } from 'lucide-react'
import { useTauriDb, Specialist } from '../hooks/useTauriDb'
import ConfirmDialog from './ConfirmDialog'

interface UserSelectionScreenProps {
  onSelect: (specialist: Specialist) => void
}

export default function UserSelectionScreen({ onSelect }: UserSelectionScreenProps) {
  const { getSpecialists, createSpecialist, deleteSpecialist } = useTauriDb()
  const [specialists, setSpecialists] = useState<Specialist[]>([])
  const [isAdding, setIsAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [isDeletingMode, setIsDeletingMode] = useState(false)
  const [confirmAction, setConfirmAction] = useState<{ message: string; action: () => void } | null>(null)

  useEffect(() => {
    loadSpecialists()
  }, [])

  const loadSpecialists = async () => {
    const data = await getSpecialists()
    setSpecialists(data)
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    
    const newSpec = await createSpecialist(newName)
    if (newSpec) {
        setSpecialists([...specialists, newSpec])
        setNewName('')
        setIsAdding(false)
    }
  }

  const handleDelete = (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmAction({
      message: '¿Eliminar perfil de especialista?',
      action: async () => {
        const success = await deleteSpecialist(id)
        if (success) loadSpecialists()
      }
    })
  }

  return (
    <div className="fixed inset-0 bg-dark-950 flex flex-col items-center justify-center p-8 z-[100]">
      <div className="w-full max-w-4xl text-center">
        <img src="/logo-large.png" alt="SIEV" className="w-20 h-20 mx-auto mb-6 opacity-80" />
        <h1 className="text-4xl font-bold text-white mb-12">¿Quién está evaluando hoy?</h1>
        
        <div className="flex flex-wrap justify-center gap-8 animate-fade-in">
          {specialists.map((spec) => (
            <div 
                key={spec.id}
                className="group relative flex flex-col items-center gap-4 cursor-pointer"
                onClick={() => !isDeletingMode && onSelect(spec)}
            >
                <div className={`w-32 h-32 rounded-lg flex items-center justify-center transition-all duration-300 ${
                    isDeletingMode 
                        ? 'bg-red-900/20 border-2 border-red-500 hover:bg-red-900/40' 
                        : 'bg-dark-800 border-2 border-transparent hover:border-siev-500 hover:bg-dark-700'
                }`}>
                    <User className={`w-16 h-16 ${isDeletingMode ? 'text-red-400' : 'text-dark-400 group-hover:text-white'}`} />
                    
                    {isDeletingMode && (
                        <div 
                            className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1.5 shadow-lg hover:scale-110 transition-transform"
                            onClick={(e) => handleDelete(spec.id, e)}
                        >
                            <Trash2 className="w-4 h-4 text-white" />
                        </div>
                    )}
                </div>
                <span className="text-lg font-medium text-dark-200 group-hover:text-white">
                    {spec.name}
                </span>
            </div>
          ))}

          {/* Add Button */}
          {!isDeletingMode && (
              <button 
                onClick={() => setIsAdding(true)}
                className="group flex flex-col items-center gap-4"
              >
                <div className="w-32 h-32 rounded-lg bg-dark-900 border-2 border-dashed border-dark-700 flex items-center justify-center group-hover:border-dark-500 group-hover:bg-dark-800 transition-all">
                    <Plus className="w-12 h-12 text-dark-600 group-hover:text-dark-400" />
                </div>
                <span className="text-lg font-medium text-dark-500 group-hover:text-dark-300">
                    Añadir Perfil
                </span>
              </button>
          )}
        </div>

        {/* Action Bar */}
        <div className="mt-16 flex justify-center gap-4">
            <button 
                className={`btn ${isDeletingMode ? 'btn-primary' : 'btn-secondary'} px-6 py-2`}
                onClick={() => setIsDeletingMode(!isDeletingMode)}
                disabled={specialists.length === 0}
            >
                {isDeletingMode ? 'Terminar Edición' : 'Administrar Perfiles'}
            </button>
        </div>
      </div>

      {/* Confirm Dialog */}
      {confirmAction && (
        <ConfirmDialog
          message={confirmAction.message}
          onConfirm={() => { confirmAction.action(); setConfirmAction(null) }}
          onCancel={() => setConfirmAction(null)}
        />
      )}

      {/* Add Modal */}
      {isAdding && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
            <div className="bg-dark-900 border border-dark-700 rounded-xl p-8 w-full max-w-md animate-scale-in">
                <h3 className="text-xl font-bold text-white mb-6">Nuevo Especialista</h3>
                <form onSubmit={handleAdd}>
                    <input 
                        autoFocus
                        className="input text-lg py-3 mb-6"
                        placeholder="Nombre"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                    />
                    <div className="flex justify-end gap-3">
                        <button 
                            type="button" 
                            onClick={() => setIsAdding(false)}
                            className="btn btn-secondary"
                        >
                            Cancelar
                        </button>
                        <button 
                            type="submit" 
                            className="btn btn-primary"
                            disabled={!newName.trim()}
                        >
                            Guardar
                        </button>
                    </div>
                </form>
            </div>
        </div>
      )}
    </div>
  )
}
