import { useState, useEffect, useRef, useCallback } from 'react';
import { useTauriDb } from './useTauriDb';

export interface ReportEdits {
    sectionComments: Record<string, string>;
    conclusion: string;
    recommendations: string;
    findings: string;
}

const EMPTY_EDITS: ReportEdits = {
    sectionComments: {},
    conclusion: '',
    recommendations: '',
    findings: '',
};

export function useReportEdits(recordingId: number) {
    const [edits, setEdits] = useState<ReportEdits>(EMPTY_EDITS);
    const [loaded, setLoaded] = useState(false);
    const { getSetting, setSetting } = useTauriDb();
    const saveTimerRef = useRef<NodeJS.Timeout | null>(null);
    const editsRef = useRef(edits);
    editsRef.current = edits;

    const storageKey = `report_edits_${recordingId}`;

    useEffect(() => {
        let cancelled = false;
        setLoaded(false);
        getSetting(storageKey).then(stored => {
            if (cancelled) return;
            if (stored) {
                try {
                    setEdits({ ...EMPTY_EDITS, ...JSON.parse(stored) });
                } catch { /* ignore parse errors */ }
            } else {
                setEdits(EMPTY_EDITS);
            }
            setLoaded(true);
        });
        return () => { cancelled = true; };
    }, [recordingId]);

    // Auto-save with debounce
    useEffect(() => {
        if (!loaded) return;
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => {
            setSetting(storageKey, JSON.stringify(editsRef.current));
        }, 1500);
        return () => {
            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        };
    }, [edits, loaded]);

    const setSectionComment = useCallback((sectionId: string, comment: string) => {
        setEdits(prev => ({
            ...prev,
            sectionComments: { ...prev.sectionComments, [sectionId]: comment },
        }));
    }, []);

    const setConclusion = useCallback((conclusion: string) => {
        setEdits(prev => ({ ...prev, conclusion }));
    }, []);

    const setRecommendations = useCallback((recommendations: string) => {
        setEdits(prev => ({ ...prev, recommendations }));
    }, []);

    const setFindings = useCallback((findings: string) => {
        setEdits(prev => ({ ...prev, findings }));
    }, []);

    return {
        edits,
        loaded,
        setSectionComment,
        setConclusion,
        setRecommendations,
        setFindings,
    };
}
