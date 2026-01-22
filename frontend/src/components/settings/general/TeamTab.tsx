import React, { useState, useEffect } from 'react';
import { User, Trash2, UserPlus } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { useTauriDb, Specialist } from '../../../hooks/useTauriDb';

export const TeamTab: React.FC = () => {
    const [specialists, setSpecialists] = useState<Specialist[]>([]);
    const [newName, setNewName] = useState('');
    const { getSpecialists, createSpecialist, deleteSpecialist } = useTauriDb();

    useEffect(() => {
        fetchSpecialists();
    }, []);

    const fetchSpecialists = async () => {
        const data = await getSpecialists();
        setSpecialists(data);
    };

    const handleAdd = async () => {
        if (!newName.trim()) return;
        await createSpecialist(newName);
        setNewName('');
        fetchSpecialists();
    };

    const handleDelete = async (id: number) => {
        if (confirm('¿Eliminar especialista?')) {
            await deleteSpecialist(id);
            fetchSpecialists();
        }
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection 
                title="Equipo de Especialistas" 
                description="Gestione los profesionales que realizan las pruebas y firman los reportes."
            >
                <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
                    {specialists.length === 0 ? (
                        <div className="p-8 text-center text-sm text-dark-500">
                            No hay especialistas registrados. Añada uno para comenzar.
                        </div>
                    ) : (
                        <div className="divide-y divide-dark-700">
                            {specialists.map(spec => (
                                <div key={spec.id} className="flex justify-between items-center px-4 py-3 hover:bg-dark-750 transition-colors">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-siev-900/50 flex items-center justify-center text-siev-400 border border-siev-500/20">
                                            <User className="w-4 h-4" />
                                        </div>
                                        <span className="text-sm font-medium text-dark-100">{spec.name}</span>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(spec.id)}
                                        className="text-dark-500 hover:text-red-400 p-2 rounded-lg hover:bg-dark-700 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    
                    <div className="p-4 bg-dark-850 border-t border-dark-700 flex gap-2">
                        <input 
                            className="flex-1 bg-dark-900 border border-dark-700 rounded-lg text-sm px-4 py-2 focus:border-siev-500 outline-none transition-colors"
                            placeholder="Nombre del nuevo especialista..."
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                        />
                        <button 
                            onClick={handleAdd}
                            className="btn btn-secondary px-4 py-2 flex items-center gap-2"
                            disabled={!newName.trim()}
                        >
                            <UserPlus className="w-4 h-4" />
                            Añadir
                        </button>
                    </div>
                </div>
            </SettingsSection>
        </div>
    );
};
