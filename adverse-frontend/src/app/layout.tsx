// src/app/layout.tsx
import './globals.css';
import { Inter } from 'next/font/google';
import type { Metadata } from 'next';
import Providers from './providers';
import Link from 'next/link';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'Adverse | Multi-Hypothesis Reasoning Engine',
  description: 'Identify dangerous drug interactions using K2 Think V2 transparent reasoning chains.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable}`}>
      <body className="min-h-screen bg-[#060B12] font-sans text-white antialiased flex flex-col">
        <Providers>
          {/* Dark Mode Header */}
          <header className="sticky top-0 z-50 w-full bg-[#060B12]/80 backdrop-blur-xl border-b border-white/5">
            <div className="container flex h-16 max-w-screen-xl items-center justify-between mx-auto px-6">
              <a className="flex items-center space-x-2.5" href="/">
                <div className="flex items-center gap-2.5">
                  {/* Premium Clinical Shield Logo */}
                  <svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-300">
                    <path d="M16 3L4 8v8c0 7 12 13 12 13s12-6 12-13V8L16 3z" />
                    <path d="M6 16h4l3-6 5 12 3-6h5" className="text-cyan-400" strokeWidth="2" />
                  </svg>
                  <span className="font-heading font-bold text-lg tracking-tight text-white">
                    Adverse
                  </span>
                </div>
              </a>
              <nav className="hidden md:flex items-center gap-8">
                <a href="#features" className="text-sm font-medium text-white/60 hover:text-white transition-colors">Features</a>
                <a href="#demo-cases" className="text-sm font-medium text-white/60 hover:text-white transition-colors">Demo Cases</a>
                <a href="#trust" className="text-sm font-medium text-white/60 hover:text-white transition-colors">Integrity</a>
                <Link href="/analyze">
                  <button className="btn-sys btn-primary text-sm px-5 py-2">
                    Analyze a Case
                  </button>
                </Link>
              </nav>
            </div>
            {/* Bottom glow line */}
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent" />
          </header>

          {/* Main content */}
          <div className="flex-1">
            {children}
          </div>

          {/* Footer */}
          <footer className="w-full border-t border-white/5 bg-[#060B12]">
            <div className="container max-w-screen-xl mx-auto px-6 py-10">
              <div className="grid md:grid-cols-3 gap-8">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    {/* Premium Clinical Shield Logo */}
                    <svg width="20" height="20" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400">
                      <path d="M16 3L4 8v8c0 7 12 13 12 13s12-6 12-13V8L16 3z" />
                      <path d="M6 16h4l3-6 5 12 3-6h5" className="text-cyan-400" strokeWidth="2" />
                    </svg>
                    <span className="font-heading font-bold text-sm text-white">Adverse Engine</span>
                  </div>
                  <p className="text-xs text-white/50 leading-relaxed max-w-xs">
                    Multi-hypothesis reasoning engine for adverse drug event detection. Powered by K2 Think V2.
                  </p>
                </div>
                <div>
                  <h4 className="font-heading font-semibold text-sm text-white mb-3">Platform</h4>
                  <ul className="space-y-2">
                    <li><a href="#features" className="text-xs text-white/50 hover:text-cyan-400 transition-colors">Features</a></li>
                    <li><a href="#demo-cases" className="text-xs text-white/50 hover:text-cyan-400 transition-colors">Demo Cases</a></li>
                    <li><Link href="/analyze" className="text-xs text-white/50 hover:text-cyan-400 transition-colors">Analyze a Case</Link></li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-heading font-semibold text-sm text-white mb-3">Clinical & Legal</h4>
                  <ul className="space-y-2">
                    <li><span className="text-xs text-white/50">PubMed-linked Sources</span></li>
                    <li><span className="text-xs text-white/50">Transparent Reasoning</span></li>
                    <li><span className="text-xs text-white/50">Research Use Only</span></li>
                  </ul>
                </div>
              </div>
              <div className="mt-8 pt-6 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-3">
                <p className="text-xs text-white/40">
                  © 2026 Adverse. For clinical research and educational purposes only.
                </p>
                <p className="text-xs text-white/40 italic">
                  Not a substitute for professional medical advice, diagnosis, or treatment.
                </p>
              </div>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
