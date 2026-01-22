import React, { createContext, useContext, ReactNode } from 'react';
import { useSessionConfig, UseSessionConfigReturn } from '../hooks/useSessionConfig';

const SessionConfigContext = createContext<UseSessionConfigReturn | null>(null);

interface SessionConfigProviderProps {
    children: ReactNode;
    apiUrl: string;
}

export function SessionConfigProvider({ children, apiUrl }: SessionConfigProviderProps) {
    const sessionConfig = useSessionConfig(apiUrl);

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
