import { AnalysisRequest, AnalysisResult, Medication } from '../types';
import { demoCases } from './demoData';

const getApiBaseUrl = () => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
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

type StreamEventHandler = (eventType: string, data: string) => void;

const streamSse = (
    url: string,
    payload: unknown,
    onEvent: StreamEventHandler
): { abort: () => void } => {
    const controller = new AbortController();

    (async () => {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            if (!response.ok || !response.body) {
                onEvent('error', `Stream failed: ${response.status}`);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop() ?? '';

                for (const block of parts) {
                    let eventType = 'message';
                    const dataLines: string[] = [];
                    for (const rawLine of block.split('\n')) {
                        const line = rawLine.replace(/\r$/, '');
                        if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                        else if (line.startsWith('data: ')) dataLines.push(line.slice(6));
                    }
                    if (dataLines.length > 0) onEvent(eventType, dataLines.join('\n').trim());
                }
            }

            if (!controller.signal.aborted) {
                onEvent('eof', '');
            }
        } catch (e: unknown) {
            if (e instanceof Error && e.name !== 'AbortError') {
                onEvent('error', e.message);
            }
        }
    })();

    return { abort: () => controller.abort() };
};

/**
 * Stream a Mystery Solver analysis via SSE.
 * Calls `onEvent` for each SSE event received.
 * Returns an abort function to cancel mid-stream.
 */
export function streamAnalyzeCase(
    request: AnalysisRequest,
    onEvent: StreamEventHandler
): { abort: () => void } {
    return streamSse(`${getApiBaseUrl()}/api/analyze/stream`, request, onEvent);
}

export function streamProfileAnalyze(
    profile: Record<string, unknown>,
    onEvent: StreamEventHandler
): { abort: () => void } {
    return streamSse(`${getApiBaseUrl()}/api/profile/analyze/stream`, profile, onEvent);
}

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
