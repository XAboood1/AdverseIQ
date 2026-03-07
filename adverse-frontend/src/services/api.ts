import { AnalysisRequest, AnalysisResult, Medication } from '../types';
import { demoCases } from './demoData';

const getApiBaseUrl = () => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'https://adverseiq.onrender.com';
};

export const searchDrugs = async (query: string): Promise<Medication[]> => {
    if (!query) return [];

    try {
        const response = await fetch(`${getApiBaseUrl()}/api/drugs/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error(`Failed to search drugs: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Drug search error:', error);
        return [];
    }
};

export const analyzeCase = async (request: AnalysisRequest): Promise<AnalysisResult> => {
    try {
        const response = await fetch(`${getApiBaseUrl()}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`Failed to analyze case: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Analyze case error:', error);
        throw error;
    }
};

export const loadDemoCase = async (id: 'demo_1' | 'demo_2' | 'demo_3'): Promise<AnalysisResult> => {
    const backendIdMap: Record<string, string> = {
        'demo_1': 'warfarin',
        'demo_2': 'stjohnswort',
        'demo_3': 'serotonin'
    };
    const backendId = backendIdMap[id];

    try {
        const response = await fetch(`${getApiBaseUrl()}/api/cases/${backendId}`);
        if (!response.ok) {
            throw new Error(`Failed to load demo case: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Load demo case error:', error);

        // Final fallback
        if (id === 'demo_1') return demoCases.warfarin;
        if (id === 'demo_2') return demoCases.stjohnswort;
        return demoCases.serotonin;
    }
};
