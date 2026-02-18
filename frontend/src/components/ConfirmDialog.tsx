import { AlertTriangle } from 'lucide-react'

interface ConfirmDialogProps {
  message: string
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({ message, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onCancel}
    >
      <div
        className="bg-dark-900 border border-dark-700 rounded-lg shadow-2xl w-full max-w-sm overflow-hidden animate-fade-in"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-dark-800 flex items-center gap-3 bg-dark-850">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <h3 className="text-lg font-bold text-white">Confirmar eliminación</h3>
        </div>
        <div className="p-6">
          <p className="text-sm text-dark-300">{message}</p>
          <div className="pt-5 flex justify-end gap-3">
            <button onClick={onCancel} className="btn btn-secondary">
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              className="btn bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
