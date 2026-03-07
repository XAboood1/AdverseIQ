import { useState, useCallback, useMemo, useEffect } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    Position,
    Handle,
    NodeProps,
    Node,
    Edge
} from 'reactflow';
import 'reactflow/dist/style.css';
import { TreeNode as CustomTreeNode, TreeEdge } from '@/types';
import { EvidenceSourceBadge } from '../shared/EvidenceSourceBadge';
import { XCircle, Settings } from 'lucide-react';

// Custom Nodes mapping
const PatientNode = ({ data }: NodeProps) => (
    <div className={`bg-slate-900 border-2 border-slate-700 rounded-lg p-3 text-center w-[180px] shadow-lg transition-all duration-300 ${data.isDimmed ? 'opacity-30' : 'opacity-100'} ${data.animateClass || ''}`}>
        <div className="text-white font-bold whitespace-pre-wrap">{data.label}</div>
        <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-slate-500" />
    </div>
);

const HypothesisNode = ({ data }: NodeProps) => {
    const isSupported = data.status === 'supported';
    const isPossible = data.status === 'possible';

    return (
        <div className={`bg-slate-800 border-2 rounded-xl p-4 w-[240px] shadow-lg transition-all duration-300 cursor-pointer ${data.isDimmed ? 'opacity-30' : 'opacity-100'} ${data.animateClass || ''} hover:scale-105 ${isSupported ? 'border-green-500 shadow-green-900/40' :
            isPossible ? 'border-amber-500 shadow-amber-900/40' : 'border-slate-500'
            }`}>
            <Handle type="target" position={Position.Top} className="!opacity-0" />
            <div className="flex justify-between items-center mb-2">
                <span className="text-white font-bold text-lg">{data.label}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${isSupported ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>{data.confidence}%</span>
            </div>
            <div className="text-sm text-slate-300 font-medium mb-4">{data.mechanism}</div>
            <div className="flex justify-between items-end">
                <EvidenceSourceBadge source={data.evidence_source} />
            </div>
            <Handle type="source" position={Position.Bottom} className="!opacity-0" />
        </div>
    );
};

const MechanismNode = ({ data }: NodeProps) => (
    <div className={`bg-blue-950/80 border-2 border-dashed border-blue-500/50 rounded-lg p-3 w-[200px] shadow-lg backdrop-blur-sm transition-all duration-300 ${data.isDimmed ? 'opacity-30' : 'opacity-100'} ${data.animateClass || ''}`}>
        <Handle type="target" position={Position.Top} className="!opacity-0" />
        <div className="flex items-center gap-2 mb-2">
            <Settings size={14} className="text-blue-400" />
            <span className="text-blue-300 text-xs font-bold uppercase">{data.label}</span>
        </div>
        <p className="text-blue-100 text-xs">{data.mechanism}</p>
        <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </div>
);

const EvidenceNode = ({ data }: NodeProps) => (
    <div className={`bg-purple-950/50 border border-purple-500/30 rounded-lg p-3 w-[200px] shadow-lg transition-all duration-300 ${data.isDimmed ? 'opacity-30' : 'opacity-100'} ${data.animateClass || ''} ${data.isDimmed ? '' : 'animate-[literaturePulse_2s_ease-in-out_infinite]'}`}>
        <Handle type="target" position={Position.Top} className="!opacity-0" />
        <div className="text-purple-300 text-xs font-bold mb-2 flex items-center gap-1">EVIDENCE <EvidenceSourceBadge source={data.source} /></div>
        <ul className="text-xs text-purple-100 space-y-1 list-disc pl-3">
            {data.supporting_evidence?.map((ev: string, idx: number) => <li key={idx}>{ev}</li>)}
        </ul>
    </div>
);

const RejectedNode = ({ data }: NodeProps) => (
    <div className={`bg-slate-900/50 border border-slate-700/50 rounded-lg p-4 w-[200px] transition-all duration-300 ${data.isDimmed ? 'opacity-20' : 'opacity-60 hover:opacity-100'} cursor-pointer ${data.animateClass || ''}`}>
        <Handle type="target" position={Position.Top} className="!bg-slate-700" />
        <div className="flex items-center gap-2 mb-2">
            <XCircle size={16} className="text-red-500" />
            <span className="text-slate-400 font-bold line-through text-sm">{data.mechanism}</span>
        </div>
        <div className="text-xs text-slate-500 italic">
            Rejected: {data.rejecting_evidence?.[0]}
        </div>
    </div>
);

const nodeTypes = {
    patientNode: PatientNode,
    hypothesisNode: HypothesisNode,
    mechanismNode: MechanismNode,
    evidenceNode: EvidenceNode,
    rejectedNode: RejectedNode
};

export default function ReasoningTree({ nodes: initialNodes, edges: initialEdges }: { nodes: CustomTreeNode[], edges: TreeEdge[] }) {
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);

    // Give nodes the entrance animation classes based on their presumed depth (y pos)
    const decoratedInitialNodes = useMemo(() => {
        return initialNodes.map(node => {
            let delayNum = 0;
            if (node.position.y > 50) delayNum = 1;
            if (node.position.y > 150) delayNum = 2;
            if (node.position.y > 250) delayNum = 3;
            if (node.position.y > 350) delayNum = 4;

            return {
                ...node,
                data: {
                    ...node.data,
                    animateClass: `node-animate-in node-delay-${delayNum}`
                }
            };
        });
    }, [initialNodes]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [nodes, setNodes, onNodesChange] = useNodesState(decoratedInitialNodes as any);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any);

    useEffect(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setNodes(decoratedInitialNodes as any);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setEdges(initialEdges as any);
    }, [decoratedInitialNodes, initialEdges, setNodes, setEdges]);

    // Calculate path highlights
    const { highlightedNodes, highlightedEdges } = useMemo(() => {
        if (!hoveredNode) return { highlightedNodes: new Set<string>(), highlightedEdges: new Set<string>() };

        const upNodes = new Set<string>([hoveredNode]);
        const upEdges = new Set<string>();
        const downNodes = new Set<string>([hoveredNode]);
        const downEdges = new Set<string>();

        let changed = true;
        while (changed) {
            changed = false;
            // Traverse UP
            edges.forEach(e => {
                if (upNodes.has(e.target) && !upNodes.has(e.source)) {
                    upNodes.add(e.source);
                    upEdges.add(e.id);
                    changed = true;
                }
            });
            // Traverse DOWN
            edges.forEach(e => {
                if (downNodes.has(e.source) && !downNodes.has(e.target)) {
                    downNodes.add(e.target);
                    downEdges.add(e.id);
                    changed = true;
                }
            });
        }

        return {
            highlightedNodes: new Set(Array.from(upNodes).concat(Array.from(downNodes))),
            highlightedEdges: new Set(Array.from(upEdges).concat(Array.from(downEdges)))
        };
    }, [hoveredNode, edges]);

    const activeNodes = useMemo(() => {
        return nodes.map((node: Node) => ({
            ...node,
            data: {
                ...node.data,
                isDimmed: hoveredNode !== null && !highlightedNodes.has(node.id)
            }
        }));
    }, [nodes, hoveredNode, highlightedNodes]);

    const activeEdges = useMemo(() => {
        return edges.map((edge: Edge) => ({
            ...edge,
            className: hoveredNode !== null && !highlightedEdges.has(edge.id) ? 'opacity-20 transition-opacity' : 'opacity-100 transition-opacity drop-shadow-[0_0_8px_rgba(56,189,248,0.5)]',
            animated: highlightedEdges.has(edge.id) || hoveredNode === null
        }));
    }, [edges, hoveredNode, highlightedEdges]);

    const onNodeMouseEnter = useCallback((_: React.MouseEvent, node: Node) => {
        setHoveredNode(node.id);
    }, []);

    const onNodeMouseLeave = useCallback(() => {
        setHoveredNode(null);
    }, []);

    return (
        <div className="w-full h-[600px] rounded-xl overflow-hidden bg-slate-950 relative group" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.05) 1px, transparent 0)', backgroundSize: '24px 24px' }}>
            <ReactFlow
                nodes={activeNodes}
                edges={activeEdges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeMouseEnter={onNodeMouseEnter}
                onNodeMouseLeave={onNodeMouseLeave}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.5}
                maxZoom={1.5}
                attributionPosition="bottom-right"
            >
                <Background gap={24} size={2} color="#1e293b" />
                <Controls className="!bg-slate-900 !border-slate-800 !text-slate-300" />
                <MiniMap className="!bg-slate-900 !border-slate-800" maskColor="rgba(15, 23, 42, 0.7)" />
            </ReactFlow>
        </div>
    );
}
