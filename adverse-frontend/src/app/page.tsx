'use client';

import Link from "next/link";
import { ActivitySquare, Network, Shield, BookOpen, GitBranch, ArrowRight, CheckCircle2 } from "lucide-react";
import { motion, useInView, animate } from "framer-motion";
import { useRef, useEffect, useState } from "react";

/* ====== Animated Counter Component ====== */
function AnimatedCounter({ target, prefix = '', suffix = '', duration = 2 }: { target: number; prefix?: string; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (!isInView) return;
    const controls = animate(0, target, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => setCount(Math.round(v)),
    });
    return () => controls.stop();
  }, [isInView, target, duration]);

  return <span ref={ref}>{prefix}{count.toLocaleString()}{suffix}</span>;
}

/* ====== Custom Dark Mode AI Reasoning Tree SVG ====== */
function AIReasoningTree() {
  return (
    <div className="relative w-full h-[420px] flex items-center justify-center">
      <svg viewBox="0 0 500 400" className="w-full h-full" fill="none">
        {/* Glow Filters */}
        <defs>
          <filter id="glow-blue" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <radialGradient id="rootGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(58, 123, 213, 0.4)" />
            <stop offset="100%" stopColor="rgba(58, 123, 213, 0.1)" />
          </radialGradient>
        </defs>

        {/* Causal Network Edges */}
        {[
          { d: "M250,60 L150,150", delay: 0 },
          { d: "M250,60 L350,150", delay: 0.2 },
          { d: "M150,150 L80,260", delay: 0.5 },
          { d: "M150,150 L200,260", delay: 0.6 },
          { d: "M350,150 L300,260", delay: 0.7 },
          { d: "M350,150 L420,260", delay: 0.8 },
          { d: "M80,260 L50,340", delay: 1.1 },
          { d: "M80,260 L110,340", delay: 1.2 },
          { d: "M420,260 L390,340", delay: 1.4 },
          { d: "M420,260 L450,340", delay: 1.5 },
        ].map((edge, i) => (
          <g key={`edge-${i}`}>
            <motion.path
              d={edge.d}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="2"
              fill="none"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.5, delay: edge.delay, ease: "easeInOut" }}
            />
            <motion.path
              d={edge.d}
              stroke="#00d2ff"
              strokeWidth="1.5"
              fill="none"
              strokeDasharray="4 12"
              initial={{ opacity: 0 }}
              animate={{ strokeDashoffset: [0, -48], opacity: [0, 0.7, 0] }}
              transition={{
                strokeDashoffset: { duration: 1.5, repeat: Infinity, ease: "linear" },
                opacity: { duration: 2.5, repeat: Infinity, delay: edge.delay }
              }}
              filter="url(#glow-cyan)"
            />
          </g>
        ))}

        {/* Causal Nodes */}
        {[
          { cx: 250, cy: 60, r: 26, fill: "url(#rootGradient)", stroke: "#3a7bd5", label: "Patient", sw: 2 },
          { cx: 150, cy: 150, r: 18, fill: "rgba(14, 165, 233, 0.12)", stroke: "#0ea5e9", label: "Drug A", sw: 1.5 },
          { cx: 350, cy: 150, r: 18, fill: "rgba(14, 165, 233, 0.12)", stroke: "#0ea5e9", label: "Drug B", sw: 1.5 },
          { cx: 80, cy: 260, r: 14, fill: "rgba(17, 153, 142, 0.12)", stroke: "#11998e", label: "CYP", sw: 1.5 },
          { cx: 200, cy: 260, r: 14, fill: "rgba(17, 153, 142, 0.12)", stroke: "#11998e", label: "PK", sw: 1.5 },
          { cx: 300, cy: 260, r: 14, fill: "rgba(17, 153, 142, 0.12)", stroke: "#11998e", label: "PD", sw: 1.5 },
          { cx: 420, cy: 260, r: 14, fill: "rgba(245, 175, 25, 0.12)", stroke: "#f5af19", label: "Lit", sw: 1.5 },
          { cx: 50, cy: 340, r: 9, fill: "#11998e", stroke: "none", label: "✓", sw: 0 },
          { cx: 110, cy: 340, r: 9, fill: "#ef4444", stroke: "none", label: "✗", sw: 0 },
          { cx: 390, cy: 340, r: 9, fill: "#11998e", stroke: "none", label: "✓", sw: 0 },
          { cx: 450, cy: 340, r: 9, fill: "#ef4444", stroke: "none", label: "✗", sw: 0 },
        ].map((node, i) => (
          <motion.g
            key={`node-${i}`}
            initial={{ scale: 0, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.1, type: "spring", bounce: 0.3 }}
            style={{ transformOrigin: `${node.cx}px ${node.cy}px` }}
          >
            <circle
              cx={node.cx}
              cy={node.cy}
              r={node.r}
              fill={node.fill}
              stroke={node.stroke}
              strokeWidth={node.sw}
              filter="url(#glow-blue)"
            />
            {node.label && (
              <text
                x={node.cx}
                y={node.cy}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#F8FAFC"
                fontSize={node.r > 16 ? 10 : 8}
                fontWeight="600"
                fontFamily="Inter, sans-serif"
              >
                {node.label}
              </text>
            )}
          </motion.g>
        ))}

        {/* Pulse ring on root */}
        <motion.circle
          cx={250} cy={60} r={26}
          stroke="#3a7bd5"
          strokeWidth="1"
          fill="none"
          animate={{ r: [26, 44], opacity: [0.5, 0] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeOut" }}
        />
      </svg>
    </div>
  );
}

/* ====== Section Wrapper ====== */
function AnimatedSection({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "0px", amount: 0.1 });

  return (
    <motion.section
      ref={ref}
      id={id}
      className={className}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    >
      {children}
    </motion.section>
  );
}

/* ====== Main Landing Page ====== */
export default function Home() {
  return (
    <main className="flex-1 overflow-hidden relative">

      {/* ===== HERO SECTION ===== */}
      <section className="relative w-full pt-28 pb-20 md:pt-36 md:pb-28 overflow-hidden">
        {/* Grid pattern background */}
        <div className="absolute inset-0 grid-overlay pointer-events-none" />
        <div className="container max-w-screen-xl mx-auto px-6 relative z-10">
          <div className="grid lg:grid-cols-12 gap-8 items-center">

            {/* Left: Headline */}
            <div className="space-y-8 lg:col-span-7 pr-4">
              <motion.div
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: {},
                  visible: { transition: { staggerChildren: 0.2 } },
                }}
                className="space-y-6"
              >
                <motion.div variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
                  <span className="badge-dark mb-4 inline-flex">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                    </span>
                    K2-THINK-V2 Telemetry Online
                  </span>
                </motion.div>

                <motion.h1
                  className="font-heading text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] text-white"
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { duration: 0.8 } } }}
                >
                  When Medications Interact,<br />
                  <span className="text-gradient text-gradient-cyan">Every Second Counts</span>
                </motion.h1>
              </motion.div>

              <motion.p
                className="max-w-lg text-lg text-white/60 leading-relaxed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6, duration: 0.8 }}
              >
                Adverse explores every possible cause through transparent reasoning chains — identifying dangerous drug interactions that conventional databases miss.
              </motion.p>

              <motion.div
                className="flex flex-wrap gap-4 pt-2"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8, duration: 0.8 }}
              >
                <Link href="/analyze">
                  <button className="btn-sys btn-primary">
                    Start Analysis
                    <ArrowRight className="inline-block ml-2 h-4 w-4" />
                  </button>
                </Link>
                <Link href="#demo-cases">
                  <button className="btn-sys btn-secondary">
                    View Demo Cases
                  </button>
                </Link>
              </motion.div>

              {/* Credibility badges */}
              <motion.div
                className="flex flex-wrap gap-3 pt-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1, duration: 0.8 }}
              >
                <span className="badge-dark"><Shield className="h-3.5 w-3.5 text-cyan-400" /> Clinical simulation</span>
                <span className="badge-dark"><BookOpen className="h-3.5 w-3.5 text-cyan-400" /> PubMed-linked</span>
                <span className="badge-dark"><GitBranch className="h-3.5 w-3.5 text-cyan-400" /> Causal graphs</span>
              </motion.div>
            </div>

            {/* Right: AI Reasoning Tree */}
            <motion.div
              className="hidden lg:flex items-center justify-center lg:col-span-5"
              initial={{ opacity: 0, filter: "blur(10px)" }}
              animate={{ opacity: 1, filter: "blur(0px)" }}
              transition={{ delay: 0.3, duration: 1.2 }}
            >
              <AIReasoningTree />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ===== STATS SECTION ===== */}
      <AnimatedSection className="w-full py-16 border-y border-white/5 mt-16 lg:mt-0">
        <div className="container max-w-screen-xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="text-cyan-400 font-semibold tracking-widest uppercase text-sm mb-4 block">The Global Toll</span>
            <h2 className="font-heading text-3xl md:text-4xl font-bold text-white">
              The Reality of <span className="text-gradient text-gradient-cyan">Adverse Events</span>
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { prefix: '', value: 250, suffix: ',000+', label: 'Deaths/year from adverse drug events', sublabel: 'in the US alone (ASP 2025)' },
              { prefix: '', value: 85, suffix: '-95%', label: 'Missed by treating physicians', sublabel: 'without automated surveillance systems' },
              { prefix: '', value: 90, suffix: '%+', label: 'Alert override rate', sublabel: 'due to lack of clinical reasoning context' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                className="text-center p-8 rounded-2xl bg-white/[0.03] border border-white/5"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
              >
                <div className="font-heading text-4xl md:text-5xl font-bold text-white mb-2">
                  <AnimatedCounter target={stat.value} prefix={stat.prefix} suffix={stat.suffix} />
                </div>
                <p className="font-semibold text-white/80 text-sm">{stat.label}</p>
                <p className="text-xs text-white/40 mt-1">{stat.sublabel}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </AnimatedSection>

      {/* ===== FEATURES / HOW IT WORKS ===== */}
      <AnimatedSection id="features" className="w-full py-24 md:py-32 relative">
        <div className="container max-w-screen-xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="text-cyan-400 font-semibold tracking-widest uppercase text-sm mb-4 block">How It Works</span>
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-white mb-6">
              Multi-Hypothesis{' '}
              <span className="text-gradient text-gradient-cyan">Reasoning</span>
            </h2>
            <p className="text-white/50 text-lg max-w-2xl mx-auto">
              Adverse runs a three-stage parallel reasoning pipeline that checks drug interactions, herbal effects, adverse reactions, and disease progression simultaneously.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: "Personalized", desc: "Adverse explores multiple hypotheses tailored to your exact symptoms and multi-drug regimen.", icon: <ActivitySquare className="h-6 w-6 text-cyan-400" />, color: "glow-cyan" },
              { title: "Parallelized", desc: "Powered by K2 Think V2, concurrently evaluating PK/PD mechanisms and metabolic pathways.", icon: <Network className="h-6 w-6 text-emerald-400" />, color: "glow-emerald" },
              { title: "Transparent", desc: "Every conclusion is mapped to a fully traversable causal network with 2024 literature citations.", icon: <BookOpen className="h-6 w-6 text-purple-400" />, color: "glow-purple" },
              { title: "Integrated", desc: "Upload labs, define chronic conditions, and receive actionable, secure intelligence.", icon: <Shield className="h-6 w-6 text-amber-400" />, color: "glow-amber" }
            ].map((feature, i) => (
              <motion.div
                key={i}
                className={`glow-card ${feature.color} p-8 flex flex-col items-start group`}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.12, duration: 0.6 }}
              >
                <div className="mb-5 p-3 rounded-xl bg-white/5 border border-white/10 group-hover:bg-white/10 transition-colors">
                  {feature.icon}
                </div>
                <h3 className="font-heading text-xl font-bold text-white mb-3">{feature.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </AnimatedSection>

      {/* ===== DEMO CASES / ROADMAP ===== */}
      <AnimatedSection id="demo-cases" className="w-full py-24 md:py-32 bg-[#080D1A]/50 border-y border-white/5">
        <div className="container max-w-screen-xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="text-cyan-400 font-semibold tracking-widest uppercase text-sm mb-4 block">Interactive Demos</span>
            <h2 className="font-heading text-4xl md:text-5xl font-bold mb-4">
              <span className="text-gradient text-gradient-cyan">Clinical</span>{' '}
              <span className="text-white">Demo Cases</span>
            </h2>
            <p className="text-white/50 text-lg max-w-2xl mx-auto">Explore pre-loaded patient scenarios to see how Adverse reasons through real-world drug interactions.</p>
          </div>

          {/* Timeline Progress Bar */}
          <div className="relative mb-12 hidden md:flex items-center justify-between max-w-2xl mx-auto">
            <div className="absolute inset-x-0 top-1/2 h-[2px] bg-gradient-to-r from-blue-500/60 via-blue-800/30 to-white/10 -translate-y-1/2"></div>
            <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center border-2 border-blue-400/30 relative z-10" style={{ boxShadow: '0 0 15px rgba(59,130,246,0.6)' }}>
              <CheckCircle2 className="w-4 h-4 text-white" />
            </div>
            <div className="w-7 h-7 rounded-md bg-[#0B1120] border-2 border-blue-500/50 relative z-10" style={{ boxShadow: '0 0 10px rgba(59,130,246,0.3)' }}></div>
            <div className="w-7 h-7 rounded-md bg-[#0B1120] border-2 border-white/15 relative z-10"></div>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                period: "Routine Severity",
                title: "Warfarin + Fluconazole",
                items: [
                  { sub: "Patient Presentation", desc: "Unexpected mucosal bruising despite stable dosing." },
                  { sub: "Adverse Analysis", desc: "Identifies CYP2C9 inhibition mechanism via parallel hypothesis testing." },
                  { sub: "Clinical Outcome", desc: "Recommends INR check & temporary dose adjustment." },
                ],
                link: "/analyze?demo=demo_1"
              },
              {
                period: "Mystery Case",
                title: "Metformin + St. John\u0027s Wort",
                items: [
                  { sub: "Patient Presentation", desc: "Spiking post-prandial hyperglycemia with no dietary changes." },
                  { sub: "Adverse Analysis", desc: "Flags hepatic enzyme induction by herbal supplement affecting drug clearance." },
                  { sub: "Clinical Outcome", desc: "Advises immediate supplement cessation and glucose monitoring." },
                ],
                link: "/analyze?demo=demo_2"
              },
              {
                period: "Emergency Alert",
                title: "Tramadol + Sertraline",
                items: [
                  { sub: "Patient Presentation", desc: "Acute fever, confusion, and muscle rigidity requiring urgent assessment." },
                  { sub: "Adverse Analysis", desc: "Immediate flag for Serotonin Syndrome via dual serotonergic mechanism detection." },
                  { sub: "Clinical Outcome", desc: "Recommends emergency department diversion and withholding serotonergic agents." },
                ],
                link: "/analyze?demo=demo_3"
              }
            ].map((col, i) => (
              <motion.div
                key={i}
                className="glow-card p-0 flex flex-col"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.6 }}
              >
                <div className="p-8 pb-5 border-b border-white/5 text-center">
                  <span className="text-xs text-white/40 tracking-widest uppercase">{col.period}</span>
                  <h3 className="font-heading text-xl font-bold text-white mt-2">{col.title}</h3>
                </div>

                <div className="p-8 space-y-5 flex-1">
                  {col.items.map((item, j) => (
                    <div key={j}>
                      <h5 className="text-white font-semibold text-sm mb-1">{item.sub}</h5>
                      <p className="text-xs text-white/50 leading-relaxed">{item.desc}</p>
                      {j < col.items.length - 1 && <div className="mt-4 border-t border-dashed border-white/5" />}
                    </div>
                  ))}
                </div>

                <div className="p-6 border-t border-white/5">
                  <Link href={col.link} className="w-full block">
                    <button className="w-full py-3 rounded-lg text-sm font-semibold text-white/70 hover:text-white hover:bg-white/5 transition-all border border-white/10">
                      Launch Demo
                    </button>
                  </Link>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </AnimatedSection>

      {/* ===== TRUST / CLINICAL INTEGRITY ===== */}
      <AnimatedSection id="trust" className="w-full py-24 md:py-32">
        <div className="container max-w-screen-xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="text-cyan-400 font-semibold tracking-widest uppercase text-sm mb-4 block">Clinical Integrity</span>
            <h2 className="font-heading text-3xl md:text-5xl font-bold text-white mb-6">
              Evidence-Based Reasoning<br />
              <span className="text-gradient text-gradient-cyan">At Every Step</span>
            </h2>
            <p className="text-white/50 text-lg max-w-2xl mx-auto">
              Adverse is built on transparency and accountability. Every conclusion is traceable back to peer-reviewed literature and established pharmacological databases.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {[
              { icon: <BookOpen className="h-7 w-7 text-cyan-400" />, title: "PubMed-Linked Sources", desc: "Every hypothesis links to real PubMed case reports and pharmacological databases. No black-box answers." },
              { icon: <GitBranch className="h-7 w-7 text-emerald-400" />, title: "Transparent Reasoning", desc: "Full reasoning tree visualization with supporting and contradicting evidence for every hypothesis branch." },
              { icon: <Shield className="h-7 w-7 text-blue-400" />, title: "Causal Graph Verified", desc: "Each mechanistic chain is structured as a directed causal graph with confidence scoring and factor analysis." },
            ].map((card, i) => (
              <motion.div
                key={i}
                className="glow-card p-8 text-center"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
              >
                <div className="w-14 h-14 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-5">
                  {card.icon}
                </div>
                <h3 className="font-heading text-lg font-bold text-white mb-3">{card.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{card.desc}</p>
              </motion.div>
            ))}
          </div>

        </div>
      </AnimatedSection>

    </main>
  );
}
