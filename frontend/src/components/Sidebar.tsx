import { Users, Settings, LogOut } from 'lucide-react'

interface MenuItemProps {
  view: string
  icon: any
  label: string
  isActive?: boolean
  onNavigate: (view: any) => void
}

function MenuItem({ view, icon, label, isActive, onNavigate }: MenuItemProps) {
  const isImagePath = typeof icon === 'string';
  const Icon = icon;

  return (
    <button
      onClick={() => onNavigate(view)}
      className={`w-full p-3 flex flex-col items-center gap-1 transition-colors relative group ${
        isActive
          ? 'text-siev-400 bg-dark-900 border-l-2 border-siev-500'
          : 'text-dark-500 hover:text-dark-200 hover:bg-dark-900/50'
      }`}
      title={label}
    >
      {isImagePath ? (
        <img src={icon} alt={label} className={`w-6 h-6 object-contain ${isActive ? '' : 'opacity-40 grayscale group-hover:opacity-100 group-hover:grayscale-0'} transition-all`} />
      ) : (
        <Icon className={`w-6 h-6 ${isActive ? 'stroke-[2.5px]' : ''}`} />
      )}
      <span className="text-[9px] font-medium">{label}</span>
    </button>
  );
}

interface SidebarProps {
  activeView: 'capture' | 'patients' | 'settings' | 'test_selection' | 'onboarding' | 'user_selection' | 'session_review'
  onNavigate: (view: 'capture' | 'patients' | 'settings') => void
  onLogout: () => void
  activeSpecialist: { name: string } | null
}

function Sidebar({ activeView, onNavigate, onLogout, activeSpecialist }: SidebarProps) {
  const isCaptureActive = activeView === 'capture' || activeView === 'test_selection'

  return (
    <div className="w-16 bg-dark-950 border-r border-dark-800 flex flex-col items-center py-2 shrink-0 z-40 pt-4">
      <div className="flex-1 w-full space-y-1">
        <MenuItem view="patients" icon={Users} label="Pacientes" isActive={activeView === 'patients'} onNavigate={onNavigate} />
        <MenuItem view="capture" icon="/mod_vng.png" label="VNG" isActive={isCaptureActive} onNavigate={onNavigate} />
        <MenuItem view="settings" icon={Settings} label="Ajustes" isActive={activeView === 'settings'} onNavigate={onNavigate} />
      </div>

      <div className="w-full mt-auto mb-2 flex justify-center">
        <button 
            onClick={onLogout}
            className="w-10 h-10 rounded-full bg-dark-800 hover:bg-dark-700 border border-dark-700 flex items-center justify-center transition-all group relative"
            title={`Sesión: ${activeSpecialist?.name || 'Desconocido'}`}
        >
          {activeSpecialist ? (
              <span className="text-xs font-bold text-dark-300 group-hover:hidden">
                  {activeSpecialist.name.substring(0, 2).toUpperCase()}
              </span>
          ) : <LogOut className="w-4 h-4 text-dark-400" />}
          
          <LogOut className="w-4 h-4 text-red-400 absolute hidden group-hover:block animate-in fade-in zoom-in duration-200" />
        </button>
      </div>
    </div>
  )
}

export default Sidebar
