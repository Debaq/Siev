import { Video, Users, Settings, LogOut } from 'lucide-react'

interface SidebarProps {
  activeView: 'capture' | 'patients' | 'settings'
  onNavigate: (view: 'capture' | 'patients' | 'settings') => void
}

function Sidebar({ activeView, onNavigate }: SidebarProps) {
  const MenuItem = ({ view, icon: Icon, label }: { view: string, icon: any, label: string }) => (
    <button
      onClick={() => onNavigate(view as any)}
      className={`w-full p-3 flex flex-col items-center gap-1 transition-colors relative group ${
        activeView === view 
          ? 'text-siev-400 bg-dark-900 border-l-2 border-siev-500' 
          : 'text-dark-500 hover:text-dark-200 hover:bg-dark-900/50'
      }`}
      title={label}
    >
      <Icon className={`w-6 h-6 ${activeView === view ? 'stroke-[2.5px]' : ''}`} />
      <span className="text-[9px] font-medium">{label}</span>
    </button>
  )

  return (
    <div className="w-16 bg-dark-950 border-r border-dark-800 flex flex-col items-center py-4 shrink-0 z-50">
      <div className="mb-6">
        <div className="w-10 h-10 bg-siev-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-siev-900/50">
          S
        </div>
      </div>

      <div className="flex-1 w-full space-y-1">
        <MenuItem view="capture" icon={Video} label="Captura" />
        <MenuItem view="patients" icon={Users} label="Pacientes" />
        <MenuItem view="settings" icon={Settings} label="Ajustes" />
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
