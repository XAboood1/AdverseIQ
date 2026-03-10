export interface Medication {
  id: string;
  displayName: string;
  genericName: string;
  dose?: string;
  frequency?: 'once daily' | 'twice daily' | 'three times daily' | 'as needed' | 'other';
  isHerb?: boolean;
}

export interface Symptom {
  id: string;
  description: string;
  severity: 'mild' | 'moderate' | 'severe';
}

export interface PatientContext {
  age?: number;
  sex?: 'M' | 'F' | 'Other';
  renalImpairment?: boolean;
  hepaticImpairment?: boolean;
  pregnant?: boolean;
}

export type AnalysisStrategy = 'rapid' | 'mechanism' | 'hypothesis';

export interface AnalysisRequest {
  medications: Medication[];
  symptoms: Symptom[];
  patientContext?: PatientContext;
  strategy: AnalysisStrategy;
  recentlyAdded?: string;
}

export interface Hypothesis {
  id: string;
  description: string;
  mechanism: string;
  confidence: number;
  supporting_evidence: string[];
  rejecting_evidence: string[];
  status: 'supported' | 'possible' | 'rejected';
  evidence_source: 'database' | 'literature' | 'mechanism';
  pubmed_refs?: string[];
}

export interface CausalStep {
  step: number;
  mechanism: string;
  expected_finding: string;
  evidence: string;
  source: 'database' | 'literature' | 'mechanism';
}

export interface TreeNode {
  id: string;
  type: 'hypothesisNode' | 'mechanismNode' | 'evidenceNode' | 'rejectedNode' | 'patientNode';
  data: {
    label: string;
    confidence?: number;
    source?: string;
    status?: string;
    color?: string;
    mechanism?: string;
    supporting_evidence?: string[];
    rejecting_evidence?: string[];
    evidence_source?: string;
  };
  position: { x: number; y: number };
}

export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  animated?: boolean;
  style?: React.CSSProperties;
}

export interface AnalysisResult {
  strategy: AnalysisStrategy;
  urgency: 'routine' | 'urgent' | 'emergent';
  urgency_reason: string;
  overall_confidence: number;
  confidence_factors: {
    factor: string;
    direction: 'increases' | 'decreases';
    weight?: 'high' | 'medium' | 'low';
  }[];
  recommendation: string;
  disclaimer: string;

  interaction_found?: boolean;
  mechanism?: string;
  causal_steps?: CausalStep[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  db_interaction?: any;

  hypotheses?: Hypothesis[];
  top_hypothesis?: string;
  tree_nodes?: TreeNode[];
  tree_edges?: TreeEdge[];

  safe_alternative?: string;
  tools_used?: string[];
}
