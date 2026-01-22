import { Video, Users, Settings, LogOut } from 'lucide-react'

interface SidebarProps {
  activeView: 'capture' | 'patients' | 'settings' | 'test_selection'
  onNavigate: (view: 'capture' | 'patients' | 'settings') => void
}

function Sidebar({ activeView, onNavigate }: SidebarProps) {
  const isCaptureActive = activeView === 'capture' || activeView === 'test_selection'

  const MenuItem = ({ view, icon: Icon, label, isActive }: { view: string, icon: any, label: string, isActive?: boolean }) => (
    <button
      onClick={() => onNavigate(view as any)}
      className={`w-full p-3 flex flex-col items-center gap-1 transition-colors relative group ${
        isActive
          ? 'text-siev-400 bg-dark-900 border-l-2 border-siev-500' 
          : 'text-dark-500 hover:text-dark-200 hover:bg-dark-900/50'
      }`}
      title={label}
    >
      <Icon className={`w-6 h-6 ${isActive ? 'stroke-[2.5px]' : ''}`} />
      <span className="text-[9px] font-medium">{label}</span>
    </button>
  )

  return (
    <div className="w-16 bg-dark-950 border-r border-dark-800 flex flex-col items-center py-2 shrink-0 z-40 pt-4">
      <div className="flex-1 w-full space-y-1">
        <MenuItem view="patients" icon={Users} label="Pacientes" isActive={activeView === 'patients'} />
        <MenuItem view="capture" icon={Video} label="Evaluación" isActive={isCaptureActive} />
        <MenuItem view="settings" icon={Settings} label="Ajustes" isActive={activeView === 'settings'} />
      </div>

      <div className="w-full mt-auto">
        <button className="w-full p-3 flex flex-col items-center gap-1 text-dark-600 hover:text-red-400 transition-colors">
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}

export default Sidebar
