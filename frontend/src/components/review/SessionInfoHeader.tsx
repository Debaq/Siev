import { ArrowLeft, Clock, Activity, Eye } from 'lucide-react'
import type { SessionReviewPayload } from '../../types/review'

interface SessionInfoHeaderProps {
    payload: SessionReviewPayload
    onBack: () => void
}

export default function SessionInfoHeader({ payload, onBack }: SessionInfoHeaderProps) {
    const { manifest, duration_seconds, sample_rate_hz, total_samples } = payload
    const patient = manifest.patient

    const formatDuration = (seconds: number) => {
        const m = Math.floor(seconds / 60)
        const s = Math.floor(seconds % 60)
        return `${m}:${s.toString().padStart(2, '0')}`
    }

    return (
        <div className="bg-dark-900 border-b border-dark-800 px-6 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-4">
                <button
                    onClick={onBack}
                    className="p-2 hover:bg-dark-800 rounded-lg transition-colors text-dark-400 hover:text-white"
                    title="Volver"
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div>
                    <h1 className="text-lg font-bold text-white">
                        {patient.last_name}, {patient.first_name}
                    </h1>
                    <div className="flex items-center gap-3 text-xs text-dark-400">
                        <span>{manifest.test_type}</span>
                        <span className="text-dark-600">|</span>
                        <span>{new Date(manifest.created_at).toLocaleDateString()}</span>
                        <span className="text-dark-600">|</span>
                        <span>{manifest.description || 'Sin descripcion'}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-6 text-xs text-dark-400">
                <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{formatDuration(duration_seconds)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" />
                    <span>{sample_rate_hz.toFixed(0)} Hz</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5" />
                    <span>{total_samples.toLocaleString()} muestras</span>
                </div>
            </div>
        </div>
    )
}
