'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { analyzeCase } from '@/services/api';
import { AnalysisRequest, Medication, Symptom, PatientContext, AnalysisStrategy, CausalStep } from '@/types';
import { Button } from '@/components/ui/button';
import { ActivitySquare, GitBranch, Network, AlertOctagon, CheckCircle, AlertTriangle, Download, FileText, ArrowLeft, Plus } from 'lucide-react';
import ReasoningTree from '@/components/tree/ReasoningTree';
import ThinkingStream from '@/components/streaming/ThinkingStream';

export default function AnalyzePage() {
    const [medications, setMedications] = useState<Medication[]>([]);
    const [symptoms, setSymptoms] = useState<Symptom[]>([]);
    const [patientContext] = useState<PatientContext>({});
    const [strategy, setStrategy] = useState<AnalysisStrategy>('hypothesis');

    const { mutate: runAnalysis, data: result, isPending } = useMutation({
        mutationFn: (req: AnalysisRequest) => analyzeCase(req),
    });

    const handleDemoClick = (id: 'demo_1' | 'demo_2' | 'demo_3') => {
        if (id === 'demo_1') {
            setMedications([
                { id: '1', displayName: 'Warfarin', genericName: 'warfarin' },
                { id: '2', displayName: 'Fluconazole', genericName: 'fluconazole' }
            ]);
            setSymptoms([{ id: 's1', description: 'Unexplained bruising', severity: 'moderate' }]);
            setStrategy('rapid');
        } else if (id === 'demo_2') {
            setMedications([
                { id: '1', displayName: 'Metformin', genericName: 'metformin' },
                { id: '2', displayName: "St. John's Wort", genericName: 'st johns wort', isHerb: true }
            ]);
            setSymptoms([{ id: 's1', description: 'Spiking Hyperglycemia', severity: 'severe' }]);
            setStrategy('mechanism');
        } else if (id === 'demo_3') {
            setMedications([
                { id: '1', displayName: 'Tramadol', genericName: 'tramadol' },
                { id: '2', displayName: 'Sertraline', genericName: 'sertraline' }
            ]);
            setSymptoms([
                { id: 's1', description: 'Fever', severity: 'severe' },
                { id: 's2', description: 'Confusion', severity: 'severe' },
                { id: 's3', description: 'Muscle rigidity', severity: 'severe' }
            ]);
            setStrategy('hypothesis');
        }
    };

    const handleAnalyze = () => {
        if (medications.length < 2 || symptoms.length < 1) return;
        runAnalysis({ medications, symptoms, patientContext, strategy });
    };

    // ===== RESULT VIEW =====
    if (result) {
        return (
            <div className="container mx-auto p-6 max-w-6xl space-y-8 mt-6 mb-16">
                {/* Top Bar */}
                <div className="flex justify-between items-center pb-4 border-b border-white/10">
                    <Button variant="outline" onClick={() => window.location.reload()} className="border-white/10 text-white/80 bg-white/5 hover:bg-white/10 hover:text-white">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        New Analysis
                    </Button>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => alert('PDF Report exported (Mock)')} className="border-white/10 text-white/80 bg-white/5 hover:bg-white/10 hover:text-white">
                            <FileText className="mr-2 h-4 w-4" /> Export PDF
                        </Button>
                        <Button variant="outline" onClick={() => alert('JSON exported (Mock)')} className="border-white/10 text-white/80 bg-white/5 hover:bg-white/10 hover:text-white">
                            <Download className="mr-2 h-4 w-4" /> Export JSON
                        </Button>
                    </div>
                </div>

                {/* Urgency Banner */}
                <div className={`w-full p-5 rounded-xl flex items-start gap-4 ring-1 ${result.urgency === 'emergent'
                    ? 'bg-red-500/10 text-red-400 ring-red-500/20'
                    : result.urgency === 'urgent'
                        ? 'bg-amber-500/10 text-amber-400 ring-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'
                    }`}>
                    {result.urgency === 'emergent' ? <AlertOctagon size={28} /> : result.urgency === 'urgent' ? <AlertTriangle size={28} /> : <CheckCircle size={28} />}
                    <div>
                        <h2 className="text-xl font-heading font-bold uppercase tracking-wide">{result.urgency} — Immediate clinical evaluation required.</h2>
                        <p className="opacity-90 mt-1 font-medium">{result.urgency_reason}</p>
                    </div>
                </div>

                {/* Top Hypothesis & Confidence Dashboard */}
                <div className="grid md:grid-cols-5 gap-6">
                    <div className="md:col-span-3 bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10 flex flex-col">
                        <div className="text-xs font-bold uppercase tracking-widest text-cyan-400 mb-3">
                            {result.strategy === 'hypothesis' ? 'Primary Hypothesis' : 'Identified Mechanism'}
                        </div>
                        <h3 className="text-2xl font-heading font-bold text-white mb-3">
                            {result.strategy === 'hypothesis'
                                ? result.hypotheses?.[0]?.description || 'No hypothesis generated'
                                : (result.db_interaction ? `${result.db_interaction.drug_a} + ${result.db_interaction.drug_b}` : 'Causal Pathway Identified')}
                        </h3>
                        <p className="text-white/60 italic mb-6 leading-relaxed flex-1 bg-white/[0.03] p-4 rounded-lg border border-white/5">
                            {result.strategy === 'hypothesis'
                                ? result.hypotheses?.[0]?.mechanism || result.mechanism
                                : (result.mechanism || result.causal_steps?.[0]?.mechanism || result.db_interaction?.mechanism || 'Pharmacological pathway mapped successfully.')}
                        </p>

                        <div className="space-y-3">
                            {result.strategy === 'hypothesis'
                                ? result.hypotheses?.[0]?.supporting_evidence?.map((ev: string, i: number) => (
                                    <div key={i} className="flex gap-3 items-start text-sm">
                                        <CheckCircle className="text-emerald-400 shrink-0 h-4 w-4 mt-0.5" />
                                        <span className="text-white/80 font-medium">{ev}</span>
                                    </div>
                                ))
                                : result.causal_steps?.map((step: CausalStep, i: number) => (
                                    <div key={i} className="flex gap-3 items-start text-sm">
                                        <CheckCircle className="text-emerald-400 shrink-0 h-4 w-4 mt-0.5" />
                                        <div className="flex flex-col">
                                            <span className="text-white/80 font-medium">Step {step.step}: {step.mechanism}</span>
                                            <span className="text-white/50 text-xs mt-0.5">Clinical Finding: {step.expected_finding}</span>
                                        </div>
                                    </div>
                                ))
                            }
                        </div>
                    </div>

                    <div className="md:col-span-2 bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10 flex flex-col items-center justify-center">
                        <div className="text-xs font-bold uppercase tracking-widest text-white/60 mb-5 w-full text-center pb-3 border-b border-white/10">Confidence Score</div>
                        <div className="relative flex items-center justify-center w-48 h-48 mb-6">
                            {/* Pulse ring */}
                            <div className={`absolute inset-0 rounded-full animate-ping opacity-10 ${(result.overall_confidence || 0) > 70 ? 'bg-emerald-500' : (result.overall_confidence || 0) > 40 ? 'bg-amber-500' : 'bg-red-500'
                                }`} style={{ animationDuration: '3s' }}></div>

                            <svg className="w-full h-full transform -rotate-90 relative z-10" viewBox="0 0 192 192">
                                {/* Background track */}
                                <circle cx="96" cy="96" r="84" stroke="rgba(255,255,255,0.08)" strokeWidth="8" fill="transparent" />
                                {/* Progress arc */}
                                <circle
                                    cx="96" cy="96" r="84"
                                    stroke="currentColor"
                                    strokeWidth="8"
                                    fill="transparent"
                                    strokeDasharray={2 * Math.PI * 84}
                                    strokeDashoffset={2 * Math.PI * 84 * (1 - (result.overall_confidence || 0) / 100)}
                                    className={
                                        (result.overall_confidence || 0) > 70 ? 'text-emerald-400' : (result.overall_confidence || 0) > 40 ? 'text-amber-400' : 'text-red-400'
                                    }
                                    strokeLinecap="round"
                                    style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.22, 1, 0.36, 1)' }}
                                />
                            </svg>
                            <div className="absolute flex flex-col items-center justify-center z-20">
                                <div className="text-5xl font-heading font-extrabold text-white flex items-baseline tracking-tighter">
                                    {result.overall_confidence}
                                    <span className="text-2xl text-white/50 ml-0.5">%</span>
                                </div>
                                <span className="text-[10px] font-bold uppercase tracking-widest text-white/40 mt-1">Probability</span>
                            </div>
                        </div>
                        <div className="w-full space-y-2.5 text-sm bg-white/[0.03] p-4 rounded-lg border border-white/5">
                            {result.confidence_factors?.map((f: { factor: string; direction: string }, i: number) => (
                                <div key={i} className="flex justify-between items-center border-b border-white/5 pb-2 last:border-0 last:pb-0">
                                    <span className="text-white/60 font-medium">{f.factor}</span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${f.direction === 'increases' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                        {f.direction === 'increases' ? '↑ Increasing' : '↓ Decreasing'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Interactive Reasoning Tree Visualizer */}
                {result.tree_nodes && result.tree_edges && (
                    <div className="w-full mt-8 bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10">
                        <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
                            <h3 className="text-xl font-heading font-bold text-white flex items-center gap-2">
                                <Network className="text-cyan-400" /> Parallel Reasoning Tree
                            </h3>
                            <div className="flex items-center gap-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-60" />
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400" />
                                </span>
                                <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">Active</span>
                            </div>
                        </div>
                        <div className="bg-white/[0.02] rounded-lg border border-white/5 p-4">
                            <ReasoningTree nodes={result.tree_nodes} edges={result.tree_edges} />
                        </div>
                    </div>
                )}

                {/* Investigation Panel */}
                {result.tools_used && result.tools_used.length > 0 && (
                    <div className="w-full mb-8 bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10">
                        <h3 className="text-lg font-heading font-bold text-white mb-3 flex items-center gap-2">
                            <ActivitySquare className="h-5 w-5 text-cyan-400" />
                            Autonomous Investigation
                        </h3>
                        <p className="text-sm text-white/60 mb-4">The following tools were executed dynamically by the reasoning engine to gather clinical evidence.</p>
                        <div className="flex flex-wrap gap-2">
                            {result.tools_used.map((tool, i) => (
                                <span key={i} className="px-3 py-1.5 rounded-md text-xs font-mono bg-white/5 border border-white/10 text-white/70 flex items-center gap-2">
                                    <span className="text-cyan-400">{i + 1}.</span> {tool}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Recommendation Panel */}
                <div className="bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10 border-l-4 border-l-cyan-400">
                    <h3 className="text-lg font-heading font-bold text-white mb-3 flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-cyan-400" />
                        Clinical Recommendation
                    </h3>
                    <p className="text-white/80 font-medium mb-5">{result.recommendation}</p>

                    {result.safe_alternative && (
                        <div className="mt-4 mb-5 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                            <h4 className="font-bold mb-2 flex items-center gap-2">
                                <CheckCircle className="h-4 w-4" /> Safer Alternative Considered
                            </h4>
                            <p className="text-sm font-medium text-emerald-100">{result.safe_alternative}</p>
                        </div>
                    )}

                    <p className="text-xs text-white/40 italic border-t pt-4 border-white/5">{result.disclaimer}</p>
                </div>
            </div>
        )
    }

    // ===== FORM VIEW =====
    return (
        <div className="container mx-auto p-6 max-w-4xl space-y-8 mt-6 mb-16">

            {/* Quick Demo Bar */}
            <div className="rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0B1120]/80 border border-white/10 backdrop-blur-xl">
                <div>
                    <h2 className="font-heading font-bold text-white text-base">Quick Start: Pre-Loaded Demo Cases</h2>
                    <p className="text-xs text-white/50 mt-0.5 font-medium">Select a demo to see Adverse in action</p>
                </div>
                <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => handleDemoClick('demo_1')} disabled={isPending}
                        className="border-white/15 text-white/80 bg-white/5 hover:bg-white/10 hover:text-white text-xs font-semibold">
                        Demo 1 (Warfarin)
                    </Button>
                    <Button size="sm" variant="outline" className="border-amber-500/30 text-amber-400 bg-amber-500/10 hover:bg-amber-500/15 text-xs font-semibold" onClick={() => handleDemoClick('demo_2')} disabled={isPending}>
                        Demo 2 (SJW Mystery)
                    </Button>
                    <Button size="sm" variant="outline" className="border-red-500/30 text-red-400 bg-red-500/10 hover:bg-red-500/15 text-xs font-semibold" onClick={() => handleDemoClick('demo_3')} disabled={isPending}>
                        Demo 3 (Serotonin)
                    </Button>
                </div>
            </div>

            {/* Page Title */}
            <div className="space-y-1 pb-4 border-b border-white/10">
                <h2 className="text-3xl font-heading font-extrabold text-white tracking-tight">Patient Case Analysis</h2>
                <p className="text-white/50 text-sm font-medium">Enter medications and symptoms below to begin intelligent telemetry analysis.</p>
            </div>

            {/* Medications Card */}
            <div className="bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10">
                <div className="flex items-center justify-between mb-5 pb-3 border-b border-white/10">
                    <h3 className="text-lg font-heading font-bold text-white">Current Medications</h3>
                    <span className="text-xs font-bold uppercase tracking-widest text-white/50 bg-white/5 px-2.5 py-1 rounded border border-white/10">Required: 2+</span>
                </div>

                <div className="space-y-4 mb-5">
                    {medications.map((med, index) => (
                        <div key={med.id} className="relative p-5 border border-white/10 rounded-lg bg-white/[0.03] group transition-all hover:border-white/20">
                            <button
                                onClick={() => setMedications(medications.filter((_, i) => i !== index))}
                                className="absolute top-3 right-3 text-white/40 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all text-sm font-bold bg-white/5 rounded-md w-6 h-6 flex items-center justify-center border border-white/10"
                            >
                                ✕
                            </button>
                            <div className="space-y-3">
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-widest text-white/50 block mb-1.5 ml-1">Drug Name</label>
                                    <input
                                        type="text"
                                        value={med.displayName}
                                        onChange={(e) => {
                                            const newMeds = [...medications];
                                            newMeds[index].displayName = e.target.value;
                                            newMeds[index].genericName = e.target.value.toLowerCase();
                                            setMedications(newMeds);
                                        }}
                                        className="w-full p-2.5 border border-white/10 rounded-lg bg-white/[0.05] text-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-cyan-400/30 focus:border-cyan-400/50 transition-all placeholder:text-white/30"
                                        placeholder="e.g. Warfarin"
                                    />
                                </div>
                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className="text-xs font-bold uppercase tracking-widest text-white/50 block mb-1.5 ml-1">Dose (Optional)</label>
                                        <input type="text" className="w-full p-2.5 border border-white/10 rounded-lg bg-white/[0.05] text-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-cyan-400/30 focus:border-cyan-400/50 transition-all placeholder:text-white/30" placeholder="e.g. 5mg" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <button
                    className="w-full flex items-center justify-center gap-2 p-4 border-2 border-dashed rounded-lg border-white/15 hover:border-cyan-400/50 hover:bg-cyan-400/5 transition-colors text-white/50 hover:text-cyan-400 font-semibold text-sm"
                    onClick={() => setMedications([...medications, { id: Date.now().toString(), displayName: '', genericName: '' }])}
                >
                    <Plus className="h-4 w-4" /> Add Medication Entry
                </button>

                {medications.length > 0 && (
                    <div className="mt-4 flex justify-end">
                        <span className="text-xs font-bold text-cyan-400 bg-cyan-400/10 px-3 py-1.5 rounded-md border border-cyan-400/20">
                            {medications.length} Medication{medications.length > 1 ? 's' : ''} Tracked
                        </span>
                    </div>
                )}
            </div>

            {/* Symptoms Card */}
            <div className="bg-[#0B1120]/80 backdrop-blur-xl rounded-xl p-7 border border-white/10">
                <div className="flex items-center justify-between mb-5 pb-3 border-b border-white/10">
                    <h3 className="text-lg font-heading font-bold text-white">Presenting Symptoms</h3>
                    <span className="text-xs font-bold uppercase tracking-widest text-white/50 bg-white/5 px-2.5 py-1 rounded border border-white/10">Required: 1+</span>
                </div>

                <div className="space-y-4 mb-5">
                    {symptoms.map((symptom, index) => (
                        <div key={symptom.id} className="relative p-5 border border-white/10 rounded-lg bg-white/[0.03] group transition-all hover:border-white/20">
                            <button
                                onClick={() => setSymptoms(symptoms.filter((_, i) => i !== index))}
                                className="absolute top-3 right-3 text-white/40 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all text-sm font-bold bg-white/5 rounded-md w-6 h-6 flex items-center justify-center border border-white/10"
                            >
                                ✕
                            </button>
                            <div className="space-y-3">
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-widest text-white/50 block mb-1.5 ml-1">Symptom Description</label>
                                    <input
                                        type="text"
                                        value={symptom.description}
                                        onChange={(e) => {
                                            const newSymptoms = [...symptoms];
                                            newSymptoms[index].description = e.target.value;
                                            setSymptoms(newSymptoms);
                                        }}
                                        className="w-full p-2.5 border border-white/10 rounded-lg bg-white/[0.05] text-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-cyan-400/30 focus:border-cyan-400/50 transition-all placeholder:text-white/30"
                                        placeholder="e.g. Spiking Hyperglycemia"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-widest text-white/50 block mb-1.5 ml-1">Severity Assessment</label>
                                    <select
                                        value={symptom.severity || 'moderate'}
                                        onChange={(e) => {
                                            const newSymptoms = [...symptoms];
                                            newSymptoms[index].severity = e.target.value as 'mild' | 'moderate' | 'severe';
                                            setSymptoms(newSymptoms);
                                        }}
                                        className="w-full p-2.5 border border-white/10 rounded-lg bg-white/[0.05] text-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-cyan-400/30 focus:border-cyan-400/50 transition-all"
                                    >
                                        <option value="mild" className="bg-[#0B1120] text-white">Mild</option>
                                        <option value="moderate" className="bg-[#0B1120] text-white">Moderate</option>
                                        <option value="severe" className="bg-[#0B1120] text-white">Severe</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <button
                    className="w-full flex items-center justify-center gap-2 p-4 border-2 border-dashed rounded-lg border-white/15 hover:border-cyan-400/50 hover:bg-cyan-400/5 transition-colors text-white/50 hover:text-cyan-400 font-semibold text-sm"
                    onClick={() => setSymptoms([...symptoms, { id: Date.now().toString(), description: '', severity: 'moderate' }])}
                >
                    <Plus className="h-4 w-4" /> Add Symptom Entry
                </button>
            </div>

            {/* Strategy Selector */}
            <div className="pt-4">
                <div className="flex items-center justify-between mb-5 pb-3 border-b border-white/10">
                    <h3 className="text-lg font-heading font-bold text-white">Analysis Strategy</h3>
                </div>
                <div className="grid md:grid-cols-3 gap-5">

                    <div
                        className={`cursor-pointer transition-all rounded-xl bg-[#0B1120]/80 border backdrop-blur-xl hover:-translate-y-0.5 ${strategy === 'rapid' ? 'ring-2 ring-cyan-400 border-cyan-400/30 shadow-[0_0_20px_-4px_rgba(0,210,255,0.3)]' : 'border-white/10 hover:border-white/20'}`}
                        onClick={() => setStrategy('rapid')}
                    >
                        <div className="p-6">
                            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4 border border-white/10">
                                <ActivitySquare className="h-6 w-6 text-cyan-400" />
                            </div>
                            <h4 className="font-heading font-bold text-white mb-1 text-base">Rapid Check</h4>
                            <p className="text-xs text-white/40 mb-3 font-mono">~5s execution</p>
                            <p className="text-sm text-white/60 mb-4 leading-relaxed font-medium">Known interaction lookup confirming established mechanisms.</p>
                            <span className="text-[10px] font-bold uppercase tracking-wider bg-white/5 text-white/50 px-2.5 py-1.5 rounded-md border border-white/10">Best for known pairs</span>
                        </div>
                    </div>

                    <div
                        className={`cursor-pointer transition-all rounded-xl bg-[#0B1120]/80 border backdrop-blur-xl hover:-translate-y-0.5 ${strategy === 'mechanism' ? 'ring-2 ring-cyan-400 border-cyan-400/30 shadow-[0_0_20px_-4px_rgba(0,210,255,0.3)]' : 'border-white/10 hover:border-white/20'}`}
                        onClick={() => setStrategy('mechanism')}
                    >
                        <div className="p-6">
                            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4 border border-white/10">
                                <GitBranch className="h-6 w-6 text-cyan-400" />
                            </div>
                            <h4 className="font-heading font-bold text-white mb-1 text-base">Mechanism Trace</h4>
                            <p className="text-xs text-white/40 mb-3 font-mono">~15s execution</p>
                            <p className="text-sm text-white/60 mb-4 leading-relaxed font-medium">Step-by-step causal chain charting pharmacokinetics.</p>
                            <span className="text-[10px] font-bold uppercase tracking-wider bg-white/5 text-white/50 px-2.5 py-1.5 rounded-md border border-white/10">Best for pathways</span>
                        </div>
                    </div>

                    <div
                        className={`relative cursor-pointer transition-all rounded-xl bg-[#0B1120]/80 border backdrop-blur-xl hover:-translate-y-0.5 ${strategy === 'hypothesis' ? 'ring-2 ring-cyan-400 border-cyan-400/30 shadow-[0_0_20px_-4px_rgba(0,210,255,0.3)]' : 'border-white/10 hover:border-white/20'}`}
                        onClick={() => setStrategy('hypothesis')}
                    >
                        <div className="absolute top-0 right-0 bg-cyan-400 text-[#060B12] text-[10px] font-bold px-3 py-1.5 rounded-bl-xl rounded-tr-xl tracking-widest uppercase">Recommended</div>
                        <div className="p-6">
                            <div className="w-12 h-12 rounded-xl bg-cyan-400/10 flex items-center justify-center mb-4 border border-cyan-400/20">
                                <Network className="h-6 w-6 text-cyan-400" />
                            </div>
                            <h4 className="font-heading font-bold text-white mb-1 text-base">Mystery Solver</h4>
                            <p className="text-xs text-white/40 mb-3 font-mono">~30s execution</p>
                            <p className="text-sm text-white/60 mb-4 leading-relaxed font-medium">Multi-hypothesis reasoning with dynamic PubMed literature search.</p>
                            <span className="text-[10px] font-bold uppercase tracking-wider bg-white/5 text-white/50 px-2.5 py-1.5 rounded-md border border-white/10">Best for complex cases</span>
                        </div>
                    </div>

                </div>
            </div>

            {/* Run Analysis */}
            <div className="pt-6 border-t border-white/10">
                {isPending && strategy === 'hypothesis' ? (
                    <div className="bg-[#0B1120]/80 rounded-xl p-6 border border-cyan-400/20 ring-1 ring-cyan-400/10 shadow-[0_0_30px_-6px_rgba(0,210,255,0.2)]">
                        <ThinkingStream isComplete={!!result} />
                    </div>
                ) : (
                    <>
                        <button
                            className="w-full py-4 text-base font-heading font-bold rounded-xl text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-2 border border-blue-500/30"
                            style={{ boxShadow: '0 0 20px -4px rgba(59, 130, 246, 0.5)' }}
                            disabled={medications.length < 2 || symptoms.length < 1 || isPending}
                            onClick={handleAnalyze}
                        >
                            {isPending ? (
                                <>
                                    <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Executing Telemetry Analysis...
                                </>
                            ) : (
                                <>
                                    <ActivitySquare className="h-5 w-5" /> Execute Clinical Analysis
                                </>
                            )}
                        </button>
                        {(medications.length < 2 || symptoms.length < 1) && (
                            <div className="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-3 text-sm text-red-400 font-medium">
                                <AlertTriangle className="h-5 w-5 shrink-0" />
                                <p>Analysis blocked: Please enter at least 2 medications and 1 presenting symptom to build the causal graph.</p>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
