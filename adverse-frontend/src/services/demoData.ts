import { AnalysisResult } from '../types';

export const demoCases: Record<string, AnalysisResult> = {
    warfarin: {
        strategy: 'rapid',
        urgency: 'urgent',
        urgency_reason: 'Severe Bleeding Risk: Anticoagulant + enzyme inhibitor with reported bruising.',
        overall_confidence: 95,
        top_hypothesis: 'H1',
        hypotheses: [
            {
                id: 'H1',
                description: 'Fluconazole CYP2C9 inhibition increases Warfarin plasma levels',
                mechanism: 'Fluconazole potently inhibits CYP2C9, the primary enzyme responsible for the metabolism of S-warfarin. This leads to decreased hepatic clearance, elevated plasma concentrations of warfarin, and an exaggerated anticoagulant effect, increasing the risk of bleeding events.',
                confidence: 95,
                status: 'supported',
                evidence_source: 'database',
                supporting_evidence: [
                    'Known Database Interaction: Fluconazole + Warfarin (Major Severity)',
                    'Mechanism Plausibility Confirmed (+)20',
                    'Symptom matches expected pharmacological effect: Bruising (+)15'
                ],
                rejecting_evidence: []
            }
        ],
        causal_steps: [
            {
                step: 1,
                mechanism: 'Fluconazole administration potently inhibits hepatic CYP2C9 enzyme.',
                expected_finding: 'Clearance of CYP2C9 substrates is significantly diminished.',
                evidence: 'DrugBank Interaction Database',
                source: 'database'
            },
            {
                step: 2,
                mechanism: 'Warfarin (specifically the more active S-enantiomer) relies on CYP2C9 for metabolism.',
                expected_finding: 'Plasma levels of S-warfarin rise above therapeutic range.',
                evidence: 'Pharmacokinetic models',
                source: 'database'
            },
            {
                step: 3,
                mechanism: 'Elevated Warfarin suppresses vitamin K-dependent clotting factors II, VII, IX, X.',
                expected_finding: 'Prolonged prothrombin time / Elevated INR, leading to symptomatic bruising or bleeding.',
                evidence: 'Patient symptom match: moderate bruising',
                source: 'mechanism'
            }
        ],
        db_interaction: {
            drug_a: 'Warfarin',
            drug_b: 'Fluconazole',
            severity: 'Major',
            mechanism: 'Fluconazole may increase the anticoagulant activities of Warfarin.',
            source: 'DrugBank API'
        },
        recommendation: 'Reduce Warfarin dose by 30-50% immediately. Monitor INR frequently (every 1-2 days) while on concurrent fluconazole therapy and adjust warfarin dose as needed.',
        safe_alternative: 'Consider topical clotrimazole or miconazole for superficial fungal infections (minimal systemic absorption, negligible CYP2C9 inhibition). If a systemic antifungal is required, terbinafine carries lower CYP2C9 inhibition risk. If fluconazole is unavoidable, reduce warfarin dose by 30–50% and monitor INR every 2–3 days until stable.',
        disclaimer: 'This is clinical decision support, not a substitute for medical judgment. Confirm all findings clinically before acting.',
        confidence_factors: [
            { factor: 'Known Database Interaction Found', direction: 'increases' },
            { factor: 'Symptom matches pharmacological effect', direction: 'increases' }
        ]
    },

    stjohnswort: {
        strategy: 'hypothesis',
        urgency: 'urgent',
        urgency_reason: 'Hyperglycemia in a diabetic patient on Metformin indicating potential treatment failure or interaction.',
        overall_confidence: 78,
        top_hypothesis: 'H1',
        hypotheses: [
            {
                id: 'H1',
                description: 'St. John\'s Wort inducing CYP3A4 increases metformin clearance',
                mechanism: 'Recent case reports indicate that concurrent administration of St. John\'s Wort, a known potent inducer of hepatic CYP3A4 and P-glycoprotein, may inadvertently increase the clearance or alter the transporter-mediated absorption of Metformin, leading to sub-therapeutic plasma levels and resultant hyperglycemia.',
                confidence: 78,
                status: 'supported',
                evidence_source: 'literature',
                pubmed_refs: ['38475621'],
                supporting_evidence: [
                    'Timeline matches SJW introduction 3 weeks ago',
                    '2024 PubMed case report (PMID: 38475621) confirms novel interaction pathway',
                    'Symptom match: Unexplained hyperglycemia spiking'
                ],
                rejecting_evidence: []
            },
            {
                id: 'H2',
                description: 'Medication non-adherence or diet failure',
                mechanism: 'Patient is failing to appropriately dose Metformin leading to hyperglycemia.',
                confidence: 12,
                status: 'rejected',
                evidence_source: 'mechanism',
                supporting_evidence: [],
                rejecting_evidence: [
                    'Sudden onset correlates directly with SJW start, not a gradual adherence or dietary pattern shift.'
                ]
            },
            {
                id: 'H3',
                description: 'Atorvastatin-induced insulin resistance',
                mechanism: 'Statins are known to modestly increase blood glucose levels and risk of incident diabetes.',
                confidence: 25,
                status: 'rejected',
                evidence_source: 'database',
                supporting_evidence: ['Atorvastatin is associated with slight glucose elevations.'],
                rejecting_evidence: [
                    'Dose is only 20mg daily.',
                    'Timeline mismatch: patient has been on Atorvastatin long-term, spike is acute.'
                ]
            },
            {
                id: 'H4',
                description: 'Disease Progression (Beta-cell decline)',
                mechanism: 'Natural progression of Type 2 Diabetes leading to absolute insulin deficiency.',
                confidence: 8,
                status: 'rejected',
                evidence_source: 'mechanism',
                supporting_evidence: [],
                rejecting_evidence: [
                    'Usually a gradual progression, doesn\'t explain acute 2-week spiking.'
                ]
            }
        ],
        tree_nodes: [
            { id: 'root', type: 'patientNode', data: { label: 'Patient (45M)\nMetformin, SJW' }, position: { x: 400, y: 0 } },

            { id: 'h1', type: 'hypothesisNode', data: { label: 'H1', confidence: 78, status: 'supported', mechanism: 'SJW induces clearance of Metformin', evidence_source: 'literature' }, position: { x: 100, y: 150 } },
            { id: 'm1', type: 'mechanismNode', data: { label: 'M1', mechanism: 'CYP3A4/Transporter Induction -> Sub-therapeutic Metformin levels -> Hyperglycemia' }, position: { x: 100, y: 350 } },
            { id: 'e1', type: 'evidenceNode', data: { label: 'E1', source: 'literature', supporting_evidence: ['Recent 2024 Study PMID:38475621'] }, position: { x: 100, y: 500 } },

            { id: 'h2', type: 'rejectedNode', data: { label: 'H2', confidence: 12, status: 'rejected', mechanism: 'Medication Non-adherence', rejecting_evidence: ['Timeline mismatches acute SJW introduction'] }, position: { x: 380, y: 150 } },
            { id: 'h3', type: 'rejectedNode', data: { label: 'H3', confidence: 25, status: 'rejected', mechanism: 'Atorvastatin Insulin Resistance', rejecting_evidence: ['Spike is acute, Atorvastatin is long-term'] }, position: { x: 660, y: 150 } }
        ],
        tree_edges: [
            { id: 'e-root-h1', source: 'root', target: 'h1', animated: true, style: { stroke: '#059669', strokeWidth: 2 } },
            { id: 'e-h1-m1', source: 'h1', target: 'm1', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5,5' } },
            { id: 'e-m1-e1', source: 'm1', target: 'e1', animated: true, style: { stroke: '#9333ea', strokeWidth: 2 } },

            { id: 'e-root-h2', source: 'root', target: 'h2', style: { stroke: '#64748b', strokeWidth: 1, strokeDasharray: '5,5' } },
            { id: 'e-root-h3', source: 'root', target: 'h3', style: { stroke: '#64748b', strokeWidth: 1, strokeDasharray: '5,5' } }
        ],
        recommendation: 'Discontinue St. John\'s Wort immediately. Monitor blood glucose closely over the next 7-14 days as induction effects wash out. Metformin dose adjustment likely not necessary once SJW is cleared.',
        safe_alternative: 'Discontinue St. John\'s Wort immediately. For mood support without CYP3A4 induction, refer for CBT or discuss a conventional antidepressant with the prescriber — noting that SSRIs in diabetic patients require glucose monitoring.',
        disclaimer: 'This is clinical decision support, not a substitute for medical judgment. Confirm all findings clinically before acting.',
        confidence_factors: [
            { factor: 'Literature support from recent 2024 case report', direction: 'increases' },
            { factor: 'Timeline strongly correlates', direction: 'increases' },
            { factor: 'No known DB interaction (Novel)', direction: 'increases' }
        ]
    },

    serotonin: {
        strategy: 'hypothesis',
        urgency: 'emergent',
        urgency_reason: 'Serotonin Syndrome Pattern Detected: Multiple serotonergic agents (SSRI + Opioid) with fever, confusion, and rigidity triad.',
        overall_confidence: 92,
        top_hypothesis: 'H1',
        hypotheses: [
            {
                id: 'H1',
                description: 'Serotonin Syndrome Toxicity',
                mechanism: 'Dual administration of Sertraline (SSRI) and Tramadol (which inhibits serotonin reuptake) leads to severe over-accumulation of serotonin in the central nervous system, crossing the toxic threshold and producing the classic triad of altered mental status, autonomic hyperactivity, and neuromuscular abnormalities.',
                confidence: 92,
                status: 'supported',
                evidence_source: 'database',
                supporting_evidence: [
                    'Database Interaction Alert: Major - Risk of Serotonin Syndrome',
                    'Symptom: Severe fever (Autonomic Instability)',
                    'Symptom: Confusion (Altered Mental Status)',
                    'Symptom: Muscle Rigidity (Neuromuscular Abnormality)'
                ],
                rejecting_evidence: []
            },
            {
                id: 'H2',
                description: 'Neuroleptic Malignant Syndrome (NMS)',
                mechanism: 'Dopamine receptor blockade leading to hyperthermia and rigidity.',
                confidence: 15,
                status: 'rejected',
                evidence_source: 'mechanism',
                supporting_evidence: ['Shares symptoms of fever and rigidity with Serotonin Syndrome.'],
                rejecting_evidence: [
                    'Patient is not on any dopamine antagonists (antipsychotics).',
                    'Onset of SS is typically rapid (hours to days), NMS is slower (days to weeks).'
                ]
            },
            {
                id: 'H3',
                description: 'Severe Influenza / Viral Infection',
                mechanism: 'Viral syndrome causing high fever and secondary confusion / malaise.',
                confidence: 10,
                status: 'rejected',
                evidence_source: 'mechanism',
                supporting_evidence: ['Fever is a hallmark of influenza.'],
                rejecting_evidence: [
                    'Does not explain severe muscle rigidity (distinct from generalized body aches).',
                    'Ignores the massive pharmacological risk factors present (Tramadol + Sertraline).'
                ]
            }
        ],
        tree_nodes: [
            { id: 'root', type: 'patientNode', data: { label: 'Patient (52M)\nTramadol, Sertraline' }, position: { x: 400, y: 0 } },

            { id: 'h1', type: 'hypothesisNode', data: { label: 'H1', confidence: 92, status: 'supported', mechanism: 'Serotonin Toxicity', evidence_source: 'database' }, position: { x: 100, y: 150 } },
            { id: 'm1', type: 'mechanismNode', data: { label: 'M1', mechanism: 'SSRI + Reuptake Inhibitor -> CNS Serotonin Overload -> Receptors overwhelmed' }, position: { x: 100, y: 350 } },
            { id: 'e1', type: 'evidenceNode', data: { label: 'E1', source: 'database', supporting_evidence: ['Hunter Toxicity Criteria Met: Fever, Rigid, Confusion'] }, position: { x: 100, y: 500 } },

            { id: 'h2', type: 'rejectedNode', data: { label: 'H2', confidence: 15, status: 'rejected', mechanism: 'Neuroleptic Malignant Syndrome', rejecting_evidence: ['No Dopamine Antagonist Present'] }, position: { x: 400, y: 150 } },
            { id: 'h3', type: 'rejectedNode', data: { label: 'H3', confidence: 10, status: 'rejected', mechanism: 'Viral Infection / Flu', rejecting_evidence: ['Does not explain rigidity', 'Misses pharmacological risk'] }, position: { x: 700, y: 150 } }
        ],
        tree_edges: [
            { id: 'e-root-h1', source: 'root', target: 'h1', animated: true, style: { stroke: '#059669', strokeWidth: 3 } },
            { id: 'e-h1-m1', source: 'h1', target: 'm1', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5,5' } },
            { id: 'e-m1-e1', source: 'm1', target: 'e1', animated: true, style: { stroke: '#2563eb', strokeWidth: 2 } },

            { id: 'e-root-h2', source: 'root', target: 'h2', style: { stroke: '#64748b', strokeWidth: 1, strokeDasharray: '5,5' } },
            { id: 'e-root-h3', source: 'root', target: 'h3', style: { stroke: '#64748b', strokeWidth: 1, strokeDasharray: '5,5' } }
        ],
        recommendation: 'Immediate Emergency Department evaluation is required. Discontinue both Tramadol and Sertraline immediately. Administer serotonin antagonists (e.g., Cyproheptadine) and provide supportive care for hyperthermia and autonomic instability.',
        safe_alternative: 'Replace tramadol with a non-serotonergic analgesic: acetaminophen for mild-to-moderate pain, or a short-course NSAID if no GI/renal contraindication. Avoid all opioids with serotonergic properties in any patient on an SSRI or SNRI.',
        disclaimer: 'This is clinical decision support, not a substitute for medical judgment. Confirm all findings clinically before acting.',
        confidence_factors: [
            { factor: 'Multiple independent serotonergic agents present (+)', direction: 'increases' },
            { factor: 'Classic Hunter Toxicity symptom triad match (+)', direction: 'increases' }
        ]
    }
};
