"use client";
import Link from "next/link";
import {
  Shield, Cloud, Zap, Lock, GitMerge, Server,
  ArrowRight, Check, ChevronRight, HardDrive, Globe
} from "lucide-react";

const FEATURES = [
  { icon: Lock,     title: "AES-256 Encryption",      desc: "Files are encrypted before leaving your device. Zero-knowledge architecture means only you can decrypt your data.", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  { icon: GitMerge, title: "Smart Deduplication",      desc: "Content-defined chunking detects duplicate data across all files. Store only unique chunks — save up to 70% storage.", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  { icon: Globe,    title: "IPFS Distributed Storage", desc: "Encrypted file chunks are pinned to IPFS via Pinata. No single point of failure. Your data lives on the decentralized web.", color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  { icon: Zap,      title: "Lightning Fast Upload",    desc: "Parallel chunk uploading with real-time progress tracking. Process and store large files in seconds.", color: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" },
  { icon: Shield,   title: "SHA-256 Integrity",        desc: "Every file and chunk is hashed. Merkle trees verify complete file integrity on download. Tamper-proof storage.", color: "bg-red-500/10 text-red-400 border-red-500/20" },
  { icon: HardDrive, title: "5 GB Free Storage",       desc: "Start with 5 GB completely free. Upgrade as you grow. No credit card required to get started.", color: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
];

const PLANS = [
  { name: "Free", price: "0", storage: "5 GB", features: ["AES-256 Encryption", "IPFS Storage", "Smart Deduplication", "5 GB Storage", "Share Links"], popular: false },
  { name: "Pro",  price: "9", storage: "100 GB", features: ["Everything in Free", "100 GB Storage", "Priority Support", "Advanced Analytics", "Custom Folders", "API Access"], popular: true },
  { name: "Team", price: "29", storage: "1 TB", features: ["Everything in Pro", "1 TB Storage", "Team Collaboration", "Admin Dashboard", "SLA Guarantee", "SSO"], popular: false },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-surface-border/50 backdrop-blur-xl bg-surface/80">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shadow-glow">
              <Cloud className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-lg">CloudStore</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            {["Features", "Pricing"].map(l => (
              <a key={l} href={`#${l.toLowerCase()}`} className="text-sm text-slate-400 hover:text-white transition-colors">{l}</a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="btn-secondary btn-sm">Sign In</Link>
            <Link href="/auth/register" className="btn-primary btn-sm">
              Get Started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6 text-center">
        <div className="absolute inset-0 bg-hero-gradient pointer-events-none" />
        <div className="absolute inset-0 bg-grid-slate pointer-events-none" />
        <div className="absolute top-24 left-1/4 w-80 h-80 bg-brand-700/10 rounded-full blur-3xl" />
        <div className="absolute top-40 right-1/4 w-60 h-60 bg-purple-700/10 rounded-full blur-3xl" />

        <div className="relative max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 glass px-4 py-1.5 rounded-full text-sm text-brand-300 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            Encrypted · Deduplicated · Decentralized
            <ChevronRight className="w-3.5 h-3.5" />
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-tight tracking-tight mb-6">
            Cloud Storage That{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400">
              Actually Protects
            </span>{" "}
            Your Files
          </h1>

          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            AES-256 encryption, content-defined deduplication, and IPFS distributed storage.
            Your files encrypted before upload — only you can read them.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/auth/register" className="btn-primary btn-lg">
              Start Free — 5 GB <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/auth/login" className="btn-secondary btn-lg">
              Sign In to Dashboard
            </Link>
          </div>

          <div className="flex items-center justify-center gap-8 mt-12 text-sm text-slate-500">
            {["No credit card", "5 GB free forever", "Cancel anytime"].map(t => (
              <span key={t} className="flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5 text-emerald-400" /> {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Built for Security First</h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Every design decision prioritizes the security and privacy of your files.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="card group hover:-translate-y-1">
                <div className={`w-11 h-11 rounded-xl border flex items-center justify-center mb-4 ${f.color}`}>
                  <f.icon className="w-5 h-5" />
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Simple Pricing</h2>
            <p className="text-slate-400 text-lg">No hidden fees. Start free, scale as you grow.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {PLANS.map((plan) => (
              <div key={plan.name} className={`card relative ${plan.popular ? "border-brand-500/50 shadow-glow" : ""}`}>
                {plan.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 badge-blue text-xs px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                )}
                <div className="mb-6">
                  <h3 className="text-xl font-bold text-white">{plan.name}</h3>
                  <div className="flex items-end gap-1 mt-3">
                    <span className="text-4xl font-bold text-white">${plan.price}</span>
                    <span className="text-slate-400 mb-1">/mo</span>
                  </div>
                  <p className="text-slate-400 text-sm mt-1">{plan.storage} storage</p>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-center gap-2.5 text-sm text-slate-300">
                      <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />
                      {feat}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/auth/register"
                  className={plan.popular ? "btn-primary w-full" : "btn-secondary w-full"}
                >
                  {plan.price === "0" ? "Start Free" : "Get Started"}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-surface-border py-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Cloud className="w-4 h-4 text-brand-400" />
            <span className="text-sm text-slate-400">© 2024 CloudStore. All rights reserved.</span>
          </div>
          <div className="flex gap-6 text-sm text-slate-500">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">API</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
