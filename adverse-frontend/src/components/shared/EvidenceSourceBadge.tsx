import { Database, BookOpen, Cpu } from 'lucide-react';
import { clsx } from "clsx";

interface EvidenceSourceBadgeProps {
    source?: string;
}

export function EvidenceSourceBadge({ source }: EvidenceSourceBadgeProps) {
    if (!source) return null;

    const isDB = source === 'database';
    const isLit = source === 'literature';
    const isMech = source === 'mechanism';

    return (
        <span className={clsx(
            "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold",
            isDB && "bg-blue-500/15 text-blue-400",
            isLit && "bg-purple-500/15 text-purple-400",
            isMech && "bg-slate-500/15 text-slate-300",
            (!isDB && !isLit && !isMech) && "bg-white/10 text-white/60"
        )}>
            {isDB && <Database size={12} />}
            {isLit && <BookOpen size={12} />}
            {isMech && <Cpu size={12} />}
            {source.toUpperCase()}
        </span>
    );
}
