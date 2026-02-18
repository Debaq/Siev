import { BodyPosition } from '../../../types/config'

const LABELS: Record<string, string> = {
    seated: 'Sentado',
    supine: 'Supino',
    prone: 'Prono',
    side_right: 'Lateral D',
    side_left: 'Lateral I',
}

interface BodyPositionIconProps {
    position?: BodyPosition
    showLabel?: boolean
}

export default function BodyPositionIcon({ position = 'seated', showLabel = true }: BodyPositionIconProps) {
    return (
        <div className="flex items-center gap-2">
            <svg viewBox="0 0 56 36" className="w-14 h-9 shrink-0">
                {/* Table / surface */}
                <line x1="4" y1="30" x2="52" y2="30" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" />

                {position === 'seated' && <>
                    {/* Torso vertical */}
                    <rect x="22" y="10" width="5" height="16" rx="2.5" fill="#475569" opacity="0.5" />
                    {/* Head */}
                    <circle cx="24.5" cy="7" r="4.5" fill="#4a90d9" opacity="0.8" />
                    {/* Legs hint */}
                    <line x1="22" y1="26" x2="16" y2="30" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
                    <line x1="27" y1="26" x2="33" y2="30" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
                </>}

                {position === 'supine' && <>
                    {/* Body horizontal on table */}
                    <rect x="8" y="22" width="24" height="5" rx="2.5" fill="#475569" opacity="0.5" />
                    {/* Head at end — can overhang */}
                    <circle cx="38" cy="24" r="4.5" fill="#4a90d9" opacity="0.8" />
                    {/* Nose dot up */}
                    <circle cx="38" cy="19" r="1" fill="#60a5fa" opacity="0.6" />
                </>}

                {position === 'prone' && <>
                    {/* Body horizontal face-down */}
                    <rect x="20" y="22" width="24" height="5" rx="2.5" fill="#475569" opacity="0.5" />
                    {/* Head at end — face down */}
                    <circle cx="14" cy="24" r="4.5" fill="#4a90d9" opacity="0.5" stroke="#60a5fa" strokeWidth="0.5" strokeDasharray="2 1.5" />
                    {/* Nose dot down */}
                    <circle cx="14" cy="29" r="1" fill="#60a5fa" opacity="0.4" />
                </>}

                {position === 'side_right' && <>
                    {/* Body on right side (thinner profile) */}
                    <rect x="8" y="23" width="24" height="4" rx="2" fill="#475569" opacity="0.5" />
                    {/* Head */}
                    <circle cx="38" cy="24.5" r="4" fill="#4a90d9" opacity="0.8" />
                    {/* Right ear indicator (red = down) */}
                    <circle cx="38" cy="28.5" r="1" fill="#ef4444" opacity="0.7" />
                </>}

                {position === 'side_left' && <>
                    {/* Body on left side */}
                    <rect x="8" y="23" width="24" height="4" rx="2" fill="#475569" opacity="0.5" />
                    {/* Head */}
                    <circle cx="38" cy="24.5" r="4" fill="#4a90d9" opacity="0.8" />
                    {/* Left ear indicator (blue = down) */}
                    <circle cx="38" cy="28.5" r="1" fill="#3b82f6" opacity="0.7" />
                </>}
            </svg>
            {showLabel && (
                <span className="text-[10px] text-dark-400 font-medium">
                    {LABELS[position] ?? position}
                </span>
            )}
        </div>
    )
}
