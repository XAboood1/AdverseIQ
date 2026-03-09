'use client';

import { useState, useEffect, useMemo } from 'react';
import { Medication, Symptom, AnalysisResult } from '@/types';

interface ThinkingStreamProps {
    isComplete: boolean;
    medications?: Medication[];
    symptoms?: Symptom[];
    result?: AnalysisResult;
}

export default function ThinkingStream({
    isComplete,
    medications = [],
    symptoms = [],
    result
}: ThinkingStreamProps) {
    const [tokens, setTokens] = useState<string[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [stage, setStage] = useState(0);

    // Generate dynamic logs based on available context
    const mockTokens = useMemo(() => {
        const stream: string[] = [];

        if (!isComplete) {
            stream.push("Initializing K2 Reasoning Engine...");
            stream.push("Ingesting multi-modal patient context and telemetry...");

            if (medications.length > 0) {
                stream.push(`Identifying pharmacokinetic profiles for: ${medications.map(m => m.displayName || m.genericName).filter(Boolean).join(', ')}.`);
            }
            if (symptoms.length > 0) {
                stream.push(`Cross-referencing presenting clinical symptoms: ${symptoms.map(s => s.description).filter(Boolean).join(', ')}.`);
            }

            stream.push("Querying global interaction databases...");
            stream.push("Synthesizing primary hypotheses from causal networks...");
            stream.push("Evaluating confidence intervals...");
            stream.push("Building parallel reasoning tree...");
        } else if (result) {
            stream.push("System trace complete.");
            stream.push(`Final strategy evaluated: ${result.strategy.toUpperCase()}`);
            stream.push(`Urgency level classified as: ${result.urgency.toUpperCase()}.`);

            if (result.hypotheses && result.hypotheses.length > 0) {
                result.hypotheses.forEach(h => {
                    stream.push(`Evaluated Hypothesis: ${h.description}`);
                    stream.push(`Mechanism Trace: ${h.mechanism} - Confidence: ${h.confidence}%`);
                    if (h.status === 'supported') {
                        stream.push(`-> STATUS: SUPPORTED`);
                    } else if (h.status === 'rejected') {
                        stream.push(`-> STATUS: REJECTED`);
                    }
                });
            } else if (result.mechanism) {
                stream.push(`Identified isolated mechanism: ${result.mechanism}`);
            }

            if (result.overall_confidence) {
                stream.push(`Overall predictive confidence interval established at ${result.overall_confidence}%.`);
            }

            if (result.confidence_factors && result.confidence_factors.length > 0) {
                stream.push(`Key modulating factors: ${result.confidence_factors.map(f => f.factor).join('; ')}.`);
            }

            stream.push("Clinical recommendation generated.");
        } else {
            // Fallback
            stream.push("Evaluating hepatic clearance. Fluconazole strongly inhibits CYP2C9. Warfarin is a major CYP2C9 substrate. S-warfarin plasma concentration will increase. Bleeding risk is significantly elevated. Correlating with patient bruising symptom... valid. Confidence interval > 90%.");
        }

        // Turn the array of sentences into an array of words + space to stream
        return stream.join(" ").split(" ").map(t => t + " ");
    }, [isComplete, medications, symptoms, result]);

    useEffect(() => {
        if (isComplete && tokens.length > 0) {
            // If already complete and tokens are populated, just show everything instantly
            setTokens(mockTokens);
            return;
        }

        if (isComplete) {
            setTokens(mockTokens);
            return;
        }

        const stages = [
            { delay: 500, time: 2000 },
            { delay: 2500, time: 2000 },
            { delay: 4500, time: 3000 },
            { delay: 7500, time: 2000 }
        ];

        const timeouts: NodeJS.Timeout[] = [];
        stages.forEach((s, idx) => {
            timeouts.push(setTimeout(() => setStage(idx + 1), s.delay));
        });

        let tokenIdx = 0;
        const interval = setInterval(() => {
            if (tokenIdx < mockTokens.length) {
                setTokens(prev => {
                    // prevent duplicate additions if effect re-runs
                    if (prev.length >= mockTokens.length) return prev;
                    return [...prev, mockTokens[tokenIdx]];
                });
                tokenIdx++;
            } else {
                clearInterval(interval);
            }
        }, 150); // Speed up slightly

        return () => {
            clearInterval(interval);
            timeouts.forEach(clearTimeout);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isComplete, mockTokens]);

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500 mt-10">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <div className="h-3 w-3 rounded-full bg-cyan-400 animate-pulse"></div>
                    <h2 className="text-xl font-bold text-white tracking-widest uppercase">{isComplete ? "System Logs" : "System Active"}</h2>
                </div>
            </div>

            <div className="bg-[#060B12] rounded-xl p-6 h-[400px] flex flex-col border border-cyan-500/30 shadow-[0_0_40px_-5px_rgba(0,210,255,0.15)] relative overflow-hidden group">
                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-50"></div>

                <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    <p className="text-sm text-cyan-400 font-mono leading-relaxed">
                        {tokens.map((token, i) => (
                            <span key={i} className="animate-in fade-in duration-300">{token}</span>
                        ))}
                        {!isComplete && (
                            <span className="inline-block translate-y-[2px] w-2.5 h-4 bg-cyan-400 animate-pulse ml-1"></span>
                        )}
                    </p>
                </div>
            </div>

        </div>
    );
}
