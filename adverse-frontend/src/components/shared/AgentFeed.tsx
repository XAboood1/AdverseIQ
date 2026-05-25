import React from 'react';
import { AgentEvent } from '@/types';

const AGENT_LABELS: Record<string, string> = {
  orchestrator: 'Orchestrator',
  polypharmacy: 'Polypharmacy',
  lab_reasoning: 'Lab Reasoning',
  timeline: 'Timeline',
};

export function AgentFeed({ events }: { events: AgentEvent[] }) {
  if (!events || events.length === 0) return null;

  return (
    <div className="w-full bg-[#0B1120]/80 p-5 rounded-xl border border-white/10 mb-2 space-y-3 font-mono text-sm max-h-96 overflow-y-auto">
      {events.map((event, i) => (
        <AgentEventRow key={`${event.type}-${event.agent ?? 'orchestrator'}-${i}`} event={event} />
      ))}
    </div>
  );
}

function UrgencyBadge({ urgency }: { urgency: 'routine' | 'urgent' | 'emergent' }) {
  const colorClass =
    urgency === 'emergent'
      ? 'bg-red-500/20 text-red-400 border-red-500/30'
      : urgency === 'urgent'
        ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
        : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';

  return (
    <span className={`px-2 py-0.5 rounded text-xs tracking-wide border ml-2 ${colorClass}`}>
      {urgency.toUpperCase()}
    </span>
  );
}

function AgentEventRow({ event }: { event: AgentEvent }) {
  const label = AGENT_LABELS[event.agent ?? 'orchestrator'] ?? 'Orchestrator';

  const icon =
    event.type === 'agent_complete'
      ? 'Ô£ô'
      : event.type === 'agent_finding'
        ? 'ÔÜá'
        : event.type === 'agent_start'
          ? 'Ôû║'
          : event.type === 'agent_thinking'
            ? 'Ôƒ│'
            : '┬À';

  return (
    <div className="flex items-start gap-3 p-2 rounded-md hover:bg-white/[0.02] transition-colors border-l-2 border-cyan-500/40">
      <span className="font-bold w-36 shrink-0 text-cyan-300/80">[{label}]</span>
      <span className={event.type === 'agent_complete' ? 'text-emerald-400' : 'text-white/60'}>{icon}</span>
      <span className="text-white/80">{event.message}</span>
      {event.urgency && <UrgencyBadge urgency={event.urgency} />}
      {event.guideline && (
        <span className="text-xs text-white/40 italic ml-2 border border-white/10 px-2 py-0.5 rounded bg-white/5">
          {event.guideline}
        </span>
      )}
    </div>
  );
}
