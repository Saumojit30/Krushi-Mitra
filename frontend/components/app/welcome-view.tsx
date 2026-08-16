'use client';

import React from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Mic, PhoneCall, Globe, Sun, TrendingUp, HelpCircle } from 'lucide-react';
import { AgentStatusBadge } from '@/components/app/agent-status-badge';

// Elegant SVG Drawing of a Cotton Boll / Bud
function CottonBudDrawing({ className = 'size-8' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Stem & Calyx Leaves */}
      <path d="M12 22v-5" />
      <path
        d="M12 17c-2.5-1.5-4.5-1-6.5 1.5 1.2-3.5 3.5-5.5 6.5-5.5s5.3 2 6.5 5.5c-2-2.5-4-3-6.5-1.5z"
        className="fill-emerald-500/20 stroke-emerald-400"
      />
      {/* Fluffy Cotton Bud Tufts */}
      <path
        d="M7.5 12.5a3.5 3.5 0 0 1-1.2-6.7 4 4 0 0 1 7.4-2.3 4 4 0 0 1 5.8 4.8 3.5 3.5 0 0 1-3.5 5.2h-8.5z"
        className="stroke-amber-200 fill-amber-100/10"
      />
      <circle cx="12" cy="8" r="1.5" className="fill-amber-300/40 stroke-none" />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref} className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header: Clean Navbar */}
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-4 backdrop-blur-md">
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="relative size-10 overflow-hidden rounded-xl border border-zinc-700">
            <Image
              src="/cotton-logo.jpg"
              alt="Krushi Mitra Logo"
              fill
              className="object-cover"
              priority
            />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide text-amber-100 sm:text-2xl">
              कृषि मित्र <span className="text-zinc-400 font-normal text-base">| Krushi Mitra</span>
            </h1>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-2 text-xs font-medium text-zinc-300">
          <span className="rounded-lg bg-emerald-950/80 border border-emerald-700/40 text-emerald-300 px-3 py-1.5 flex items-center gap-1.5">
            <Mic className="size-3.5" /> Voice Assistant
          </span>
          <span className="rounded-lg bg-zinc-800/50 hover:bg-zinc-800 text-zinc-400 px-3 py-1.5 flex items-center gap-1.5 transition-colors cursor-pointer">
            <Sun className="size-3.5 text-amber-400" /> Weather
          </span>
          <span className="rounded-lg bg-zinc-800/50 hover:bg-zinc-800 text-zinc-400 px-3 py-1.5 flex items-center gap-1.5 transition-colors cursor-pointer">
            <TrendingUp className="size-3.5 text-emerald-400" /> Market Prices (MSP)
          </span>
          <span className="rounded-lg bg-zinc-800/50 hover:bg-zinc-800 text-zinc-400 px-3 py-1.5 flex items-center gap-1.5 transition-colors cursor-pointer">
            <HelpCircle className="size-3.5 text-blue-400" /> Help
          </span>
        </nav>

        {/* Right Status Badge */}
        <div className="flex items-center gap-3">
          <AgentStatusBadge state="ready" />
          <span className="hidden sm:flex items-center gap-1 text-[11px] font-medium text-zinc-400 border border-zinc-700/60 bg-zinc-800/40 px-2.5 py-1 rounded-full">
            <Globe className="size-3 text-emerald-400" /> Marathi / Hindi
          </span>
        </div>
      </header>

      {/* Main Option 1 Split Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch min-h-[560px]">
        {/* Left Column: Vidarbha Cotton Farmer Portrait */}
        <div className="lg:col-span-7 relative overflow-hidden rounded-3xl border border-zinc-800/80 bg-zinc-950 shadow-2xl min-h-[380px] lg:min-h-[560px] flex flex-col justify-end group">
          <Image
            src="/img-farmer-1.jpg"
            alt="Vidarbha Cotton Farmer"
            fill
            className="object-cover object-top transition-transform duration-700 group-hover:scale-105"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />

          <div className="relative z-10 p-6 sm:p-8 space-y-2">
            <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-wider text-amber-300 bg-black/60 border border-amber-500/30 px-3.5 py-1 rounded-full backdrop-blur-md">
              <CottonBudDrawing className="size-4" /> यवतमाळ व अमरावती कापूस शेतकरी
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white leading-tight">
              विदर्भातील कापूस उत्पादकांसाठी विश्वसनीय साथीदार
            </h2>
            <p className="text-xs sm:text-sm text-zinc-300 max-w-lg font-light leading-relaxed">
              बोंड अळी, हमीभाव (MSP ₹6,620) आणि पीक विम्यासंदर्भात थेट मराठी भाषेत बोलून सल्ला मिळवा.
            </p>
          </div>
        </div>

        {/* Right Column: Agent Card with Subtle Cotton Bud Line Drawing */}
        <div className="lg:col-span-5 relative overflow-hidden rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-[#083020] via-[#052115] to-[#03150d] p-8 sm:p-10 flex flex-col justify-between items-center text-center shadow-2xl shadow-emerald-950/50">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-72 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Pod Top Header Bar */}
          <div className="w-full flex items-center justify-between text-xs font-medium text-emerald-300/80 border-b border-emerald-800/40 pb-4 z-10">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
              Active System
            </span>
            <span className="text-amber-200/90 font-mono text-[11px]">
              Murf Falcon Audio AI
            </span>
          </div>

          {/* Main Voice Agent Card Core */}
          <div className="my-auto py-6 space-y-6 flex flex-col items-center z-10 w-full">
            
            {/* Subtle Cotton Bud Drawing Badge Representation */}
            <div className="flex items-center gap-3 px-4 py-2 rounded-2xl bg-emerald-950/70 border border-amber-400/20 backdrop-blur-md shadow-sm">
              <CottonBudDrawing className="size-6 text-amber-200" />
              <div className="text-left">
                <span className="block text-xs font-semibold text-amber-100 tracking-wide">
                  कापूस बोंड सल्लागार
                </span>
                <span className="block text-[10px] text-emerald-300/80 font-mono">
                  Cotton Bud Advisory
                </span>
              </div>
            </div>

            {/* Main Cotton Logo Image in Soft Ring */}
            <div className="relative size-20 overflow-hidden rounded-full ring-2 ring-amber-400/40 shadow-xl shadow-amber-950/40">
              <Image
                src="/cotton-logo.jpg"
                alt="Cotton Sprout Logo"
                fill
                className="object-cover"
              />
            </div>

            {/* Marathi Title & Prompt */}
            <div className="space-y-1">
              <h3 className="text-3xl sm:text-4xl font-serif font-bold text-amber-100 tracking-wide">
                &lsquo;कृषि मित्र&rsquo;
              </h3>
              <p className="text-xs font-medium text-emerald-200/90">
                Krushi Mitra Voice Advisor
              </p>
            </div>

            <p className="text-xs text-zinc-300 max-w-xs font-light leading-relaxed">
              &ldquo;नमस्कार शेतकरी दादा, आज कापसाविषयी काय विचारायचे आहे?&rdquo;
            </p>

            {/* Glowing Microphone Call Trigger Button */}
            <div className="relative my-2 flex items-center justify-center">
              <div className="absolute size-36 rounded-full border border-amber-400/20 animate-ping pointer-events-none" />
              <div className="absolute size-44 rounded-full border border-emerald-500/20 animate-pulse pointer-events-none" />

              <Button
                size="lg"
                onClick={onStartCall}
                className="group relative size-28 rounded-full bg-gradient-to-br from-emerald-600 via-emerald-700 to-amber-600 border-4 border-amber-400/40 text-amber-100 flex flex-col items-center justify-center gap-1 shadow-[0_0_60px_rgba(212,175,55,0.35)] transition-all transform hover:scale-105 active:scale-95"
              >
                <Mic className="size-9 text-amber-200 group-hover:scale-110 transition-transform" />
                <span className="text-[11px] font-bold tracking-wider uppercase text-amber-100">
                  Call Now
                </span>
              </Button>
            </div>
          </div>

          {/* Bottom Action Button */}
          <div className="w-full text-center z-10">
            <Button
              variant="outline"
              onClick={onStartCall}
              className="w-full rounded-full border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-200 text-xs font-semibold py-3 gap-2"
            >
              <PhoneCall className="size-3.5 text-amber-400 animate-bounce" />
              {startButtonText || 'कॉल सुरू करा (Start Call)'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
