'use client';

import { useState, useEffect } from 'react';


export default function ThinkingStream({ isComplete }: { isComplete: boolean }) {
    const [tokens, setTokens] = useState<string[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [stage, setStage] = useState(0);

    // Mock Streaming Effect for the demo
    useEffect(() => {
        if (isComplete) return;

        const stages = [
            { delay: 500, time: 2000 },
            { delay: 2500, time: 2000 },
            { delay: 4500, time: 3000 },
            { delay: 7500, time: 2000 }
        ];

        stages.forEach((s, idx) => {
            setTimeout(() => setStage(idx + 1), s.delay);
        });

        const mockTokens = "Evaluating hepatic clearance. Fluconazole strongly inhibits CYP2C9. Warfarin is a major CYP2C9 substrate. S-warfarin plasma concentration will increase. Bleeding risk is significantly elevated. Correlating with patient bruising symptom... valid. Confidence interval > 90%.".split(" ");

        let tokenIdx = 0;
        const interval = setInterval(() => {
            if (tokenIdx < mockTokens.length) {
                setTokens(prev => [...prev, mockTokens[tokenIdx] + " "]);
                tokenIdx++;
            } else {
                clearInterval(interval);
            }
        }, 200);

        return () => clearInterval(interval);
    }, [isComplete]);

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500 mt-10">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <div className="h-3 w-3 rounded-full bg-cyan-400 animate-pulse"></div>
                    <h2 className="text-xl font-bold text-white tracking-widest uppercase">System Active</h2>
                </div>
            </div>

            <div className="bg-[#060B12] rounded-xl p-6 h-[400px] flex flex-col border border-cyan-500/30 shadow-[0_0_40px_-5px_rgba(0,210,255,0.15)] relative overflow-hidden group">
                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-50"></div>

                <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                    {tokens.map((token, i) => (
                        <div key={i} className="flex gap-3 text-sm animate-in slide-in-from-bottom-2 fade-in duration-300">
                            <span className="text-cyan-500/50 font-mono shrink-0 select-none">[{String(i).padStart(4, '0')}]</span>
                            <span className="text-cyan-400 font-mono flex-1">{token}</span>
                        </div>
                    ))}
                    {!isComplete && (
                        <div className="flex gap-3 text-sm pt-2">
                            <span className="text-cyan-500/50 font-mono shrink-0 select-none">[{String(tokens.length).padStart(4, '0')}]</span>
                            <span className="inline-block w-2.5 h-4 bg-cyan-400 animate-pulse"></span>
                        </div>
                    )}
                </div>
            </div>

        </div>
    );
}
