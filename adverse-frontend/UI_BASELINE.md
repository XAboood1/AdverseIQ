# AdverseIQ UI Baseline Design System

This document serves as the baseline design snapshot for the AdverseIQ frontend interface. It captures the exact structure, aesthetics, and configurations implemented to give the application its premium, clinical, and high-trust feel. Any future UI changes should be evaluated against this baseline, and this document can be used to restore the design if necessary.

## 1. Page Structure & Sections (`src/app/page.tsx`)
The main landing page is composed of distinct sections, each utilizing `AnimatedSection` for scroll-triggered reveal animations.

*   **Hero Section**: Split layout (`grid lg:grid-cols-2`). 
    *   **Left**: Animated staggered headline ("When Medications Interact," / "Every Second Counts"), concise subtext, primary/secondary CTA buttons, and credibility trust badges.
    *   **Right**: An elevated glass panel displaying a live, animated Reasoning Tree visual (`<ReasoningTreeVisual />`), depicting the parallel evaluation of clinical hypotheses.
    *   **Background**: Uses a panning clinical grid (`medical-grid-bg`) and an ECG line subtle overlay (`ecg-line-bg`).
*   **Stats Section**: 3-column layout featuring `AnimatedCounter` components highlighting key metrics.
*   **How It Works Section**: 3-stage pipeline (Input $\rightarrow$ Parallel Reasoning $\rightarrow$ Transparent Explanations) displayed in a 3-column grid with horizontal connecting lines on desktop.
*   **Demo Cases Section**: 3 clinical cases (Routine, Mystery Solver, Emergent) using cards with left-aligned severity color strips. The Emergent card includes a glowing red border and an SVG heartbeat animation in the background.
*   **Trust Signals / Clinical Integrity**: 3-column cards detailing PubMed links, reasoning, and causal graphs, followed by a simulated "Citation Preview" mock-up.

## 2. Color Palette & Gradients
Defined in `tailwind.config.ts` and `src/app/globals.css`. The palette enforces a professional, medical intelligence aesthetic.

**Core Clinical Colors:**
*   **Navy** (`#0f172a` / `slate-900`): Headers, primary text. Trust & Structure.
*   **Text** (`#334155` / `slate-700`): Body text.
*   **Text Muted** (`#64748b` / `slate-500`): Secondary text, sub-labels.
*   **Surface** (`#f8fafc` / `slate-50`): App background base.
*   **Surface Alt** (`#f1f5f9` / `slate-100`): Secondary background layers.
*   **Border** (`#e2e8f0` / `slate-200`): Dividers, panel borders.

**Action & Intelligence Colors:**
*   **Blue** (`#0ea5e9` / `sky-500`): Primary actions, highlights.
*   **Teal** (`#0d9488` / `teal-600`): Secondary actions, intelligence indicators, glowing effects.

**Status / Severity Indicators:**
*   **Green** (`#059669` / `emerald-600`): Routine / Safe.
*   **Amber** (`#d97706` / `amber-600`): Urgent / Warning / Mystery cases.
*   **Red** (`#b91c1c` / `red-700`): Emergent / Danger. Glows organically for emergency cards.

**Gradients:**
*   **Primary Button**: `linear-gradient(135deg, hsl(210 50% 30%) 0%, hsl(210 45% 25%) 100%)`
*   **Section Top Dividers**: `linear-gradient(90deg, transparent, border, teal, border, transparent)`

## 3. Typography Hierarchy
*   **Headings** (`h1` through `h6`, `.font-heading`): `Plus Jakarta Sans`, falling back to `Inter`. Tighter letter spacing (`-0.02em`) for a modern, focused look. Heavy weights (Extrabold) used for major headers.
*   **Body Text**: `Inter`, system-ui, sans-serif. Optimally balanced text wrapping.
*   **Tracking Elements**: `.overline-clinical` uses uppercase, widely spaced (`tracking-[0.15em]`), small (`text-[10px]`) font for technical or status labels.

## 4. Component Styles (`src/app/globals.css`)
*   **Glass Panels** (`.glass-panel`, `.glass-panel-elevated`): 
    *   Base background white with heavy transparency (`0.7` to `0.8`).
    *   Backdrop blur (`12px` to `16px`).
    *   Layered, soft clinical shadows simulating depth (`shadow-clinical-sm`, `shadow-clinical-md`).
*   **Card Hover Interactions** (`.card-hover-lift`):
    *   Lifts the card upwards (`translate-Y(-4px)`).
    *   Expands the shadow drop for physical prominence.
*   **Buttons** (`.btn-clinical`):
    *   Contains a custom CSS ripple effect using radial gradients.
    *   Primary triggers a teal glow drop-shadow on hover.
*   **Severity Strips** (`.severity-strip`): Absolute positioned, `4px` wide left-border accents that adopt colored theme indicating routine/urgent/emergent status.
*   **Trust Badges**: Small, pill-shaped glass items with delicate borders and subtle hover glow (`box-shadow: 0 0 12px hsl(...)`).

## 5. Layout Spacing Rules
*   **Container**: Max width screen XL (`max-w-screen-xl`), centered, with horizontal padding (`px-6`).
*   **Vertical Section Rhythm**: Generous padding isolating ideas. Hero uses `py-16 md:py-24 lg:py-32`. Standard sections use `py-20 md:py-28`.
*   **Grids & Gaps**: Standard 3-column desktop layouts. Feature grids use `gap-8`, while denser case-card grids use `gap-6`. Hero split uses `gap-12 lg:gap-16`.

## 6. Animations
*   **Framer Motion Reveal**: Standard entry for elements is fading in and sliding up (`y: 40` to `0`, `opacity: 0` to `1`) using smooth physics profiles (`ease: [0.22, 1, 0.36, 1]`).
*   **Background Panning** (`panGrid`): Medical grid pattern moves continually at `60s` linear rates across the X/Y plane.
*   **Reasoning Tree Drawings**: SVG path animation (`pathLength` transition) unspools the network paths, followed by marching-ants data flow effect (`strokeDashoffset` loop). Nodes expand outward (`nodeExpand` scaling).
*   **Status Beacons**: Native Tailwind `animate-ping` used on small colored dots (teal for active telemetry, red for emergency).
*   **Heartbeat Monitor** (`heartbeat-pulse`): Continuous looped CSS path drawing on the background of Emergency cards simulating an ECG read.
