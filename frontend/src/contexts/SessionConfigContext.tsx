import { createContext, useContext, ReactNode } from 'react';
import { useSessionConfig, UseSessionConfigReturn } from '../hooks/useSessionConfig';

const SessionConfigContext = createContext<UseSessionConfigReturn | null>(null);

interface SessionConfigProviderProps {
    children: ReactNode;
    send?: (msg: any) => void;
}

export function SessionConfigProvider({ children, send }: SessionConfigProviderProps) {
    const sessionConfig = useSessionConfig(send);

    return (
        <SessionConfigContext.Provider value={sessionConfig}>
            {children}
        </SessionConfigContext.Provider>
    );
}

export function useSessionConfigContext(): UseSessionConfigReturn {
    const context = useContext(SessionConfigContext);
    if (!context) {
        throw new Error('useSessionConfigContext must be used within a SessionConfigProvider');
    }
    return context;
}

/**
 * Hook that returns session overrides if available, or empty object if not in provider.
 * Safe to use in components that might be outside the provider.
 */
export function useSessionOverrides(): Partial<UseSessionConfigReturn['overrides']> {
    const context = useContext(SessionConfigContext);
    return context?.overrides ?? {};
}
