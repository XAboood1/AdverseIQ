'use client';

import { useState, useEffect, useRef } from 'react';

interface ThinkingStreamProps {
    isComplete: boolean;
    /** Real token chunks streamed from K2 via SSE. Each element is one SSE payload string. */
    rawLogs?: string[];
}

export default function ThinkingStream({ isComplete, rawLogs }: ThinkingStreamProps) {
    const [displayed, setDisplayed] = useState('');
    const pendingCharsRef = useRef<string[]>([]);
    const dripRef = useRef<NodeJS.Timeout | null>(null);
    const lastRawLenRef = useRef(0);
    const fullTextRef = useRef('');

    // Reset when a new analysis starts
    useEffect(() => {
        if (!rawLogs || rawLogs.length === 0) {
            setDisplayed('');
            pendingCharsRef.current = [];
            lastRawLenRef.current = 0;
            fullTextRef.current = '';
            if (dripRef.current) { clearInterval(dripRef.current); dripRef.current = null; }
        }
    }, [rawLogs]);

    // Enqueue new characters as rawLogs grows
    useEffect(() => {
        if (!rawLogs || rawLogs.length === 0) return;

        const newChunks = rawLogs.slice(lastRawLenRef.current);
        lastRawLenRef.current = rawLogs.length;

        const newText = newChunks.join('');
        fullTextRef.current += newText;

        if (isComplete) {
            if (dripRef.current) { clearInterval(dripRef.current); dripRef.current = null; }
            setDisplayed(fullTextRef.current);
            pendingCharsRef.current = [];
            return;
        }

        pendingCharsRef.current.push(...newText.split(''));

        if (!dripRef.current) {
            dripRef.current = setInterval(() => {
                const batch = pendingCharsRef.current.splice(0, 4).join('');
                if (batch) setDisplayed(prev => prev + batch);
            }, 16);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [rawLogs, isComplete]);

    // Flush on completion
    useEffect(() => {
        if (isComplete) {
            if (dripRef.current) { clearInterval(dripRef.current); dripRef.current = null; }
            if (fullTextRef.current) setDisplayed(fullTextRef.current);
        }
    }, [isComplete]);

    useEffect(() => {
        return () => { if (dripRef.current) clearInterval(dripRef.current); };
    }, []);

    const hasContent = displayed.length > 0;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500 mt-10">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <div className="h-3 w-3 rounded-full bg-cyan-400 animate-pulse"></div>
                    <h2 className="text-xl font-bold text-white tracking-widest uppercase">
                        {isComplete ? 'Reasoning Trace' : 'K2 Thinking'}
                    </h2>
                </div>
            </div>

            <div className="bg-[#060B12] rounded-xl p-6 min-h-[120px] max-h-[420px] flex flex-col border border-cyan-500/30 shadow-[0_0_40px_-5px_rgba(0,210,255,0.15)] relative overflow-hidden">
                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-50"></div>

                <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    {hasContent ? (
                        <p className="text-sm text-cyan-400 font-mono leading-relaxed whitespace-pre-wrap">
                            {displayed}
                            {!isComplete && (
                                <span className="inline-block translate-y-[2px] w-2 h-3.5 bg-cyan-400 animate-pulse ml-0.5" />
                            )}
                        </p>
                    ) : (
                        <p className="text-sm text-cyan-400/40 font-mono leading-relaxed">
                            <span className="inline-block w-2 h-3.5 bg-cyan-400/40 animate-pulse mr-2 translate-y-[2px]" />
                            Waiting for K2 reasoning stream...
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
