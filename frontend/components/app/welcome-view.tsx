'use client';

import React from 'react';
import Image from 'next/image';
import { Globe, HelpCircle, Mic, PhoneCall, Sun, TrendingUp } from 'lucide-react';
import { AgentStatusBadge } from '@/components/app/agent-status-badge';
import { Button } from '@/components/ui/button';

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
        className="fill-amber-100/10 stroke-amber-200"
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
    <div ref={ref} className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
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
              कृषि मित्र <span className="text-base font-normal text-zinc-400">| Krushi Mitra</span>
            </h1>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden items-center gap-2 text-xs font-medium text-zinc-300 md:flex">
          <span className="flex items-center gap-1.5 rounded-lg border border-emerald-700/40 bg-emerald-950/80 px-3 py-1.5 text-emerald-300">
            <Mic className="size-3.5" /> Voice Assistant
          </span>
          <span className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-zinc-800/50 px-3 py-1.5 text-zinc-400 transition-colors hover:bg-zinc-800">
            <Sun className="size-3.5 text-amber-400" /> Weather
          </span>
          <span className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-zinc-800/50 px-3 py-1.5 text-zinc-400 transition-colors hover:bg-zinc-800">
            <TrendingUp className="size-3.5 text-emerald-400" /> Market Prices (MSP)
          </span>
          <span className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-zinc-800/50 px-3 py-1.5 text-zinc-400 transition-colors hover:bg-zinc-800">
            <HelpCircle className="size-3.5 text-blue-400" /> Help
          </span>
        </nav>

        {/* Right Status Badge */}
        <div className="flex items-center gap-3">
          <AgentStatusBadge state="ready" />
          <span className="hidden items-center gap-1 rounded-full border border-zinc-700/60 bg-zinc-800/40 px-2.5 py-1 text-[11px] font-medium text-zinc-400 sm:flex">
            <Globe className="size-3 text-emerald-400" /> Marathi / Hindi
          </span>
        </div>
      </header>

      {/* Main Option 1 Split Layout Grid */}
      <div className="grid min-h-[560px] grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
        {/* Left Column: Vidarbha Cotton Farmer Portrait */}
        <div className="group relative flex min-h-[380px] flex-col justify-end overflow-hidden rounded-3xl border border-zinc-800/80 bg-zinc-950 shadow-2xl lg:col-span-7 lg:min-h-[560px]">
          <Image
            src="/img-farmer-1.jpg"
            alt="Vidarbha Cotton Farmer"
            fill
            className="object-cover object-top transition-transform duration-700 group-hover:scale-105"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />

          <div className="relative z-10 space-y-2 p-6 sm:p-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-black/60 px-3.5 py-1 text-xs font-semibold tracking-wider text-amber-300 backdrop-blur-md">
              <CottonBudDrawing className="size-4" /> यवतमाळ व अमरावती कापूस शेतकरी
            </div>
            <h2 className="text-2xl leading-tight font-bold text-white sm:text-3xl">
              विदर्भातील कापूस उत्पादकांसाठी विश्वसनीय साथीदार
            </h2>
            <p className="max-w-lg text-xs leading-relaxed font-light text-zinc-300 sm:text-sm">
              बोंड अळी, हमीभाव (MSP ₹6,620) आणि पीक विम्यासंदर्भात थेट मराठी भाषेत बोलून सल्ला
              मिळवा.
            </p>
          </div>
        </div>

        {/* Right Column: Agent Card with Subtle Cotton Bud Line Drawing */}
        <div className="relative flex flex-col items-center justify-between overflow-hidden rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-[#083020] via-[#052115] to-[#03150d] p-8 text-center shadow-2xl shadow-emerald-950/50 sm:p-10 lg:col-span-5">
          <div className="pointer-events-none absolute top-1/2 left-1/2 size-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/10 blur-3xl" />

          {/* Pod Top Header Bar */}
          <div className="z-10 flex w-full items-center justify-between border-b border-emerald-800/40 pb-4 text-xs font-medium text-emerald-300/80">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="size-2 animate-pulse rounded-full bg-emerald-400" />
              Active System
            </span>
            <span className="font-mono text-[11px] text-amber-200/90">Murf Falcon Audio AI</span>
          </div>

          {/* Main Voice Agent Card Core */}
          <div className="z-10 my-auto flex w-full flex-col items-center space-y-6 py-6">
            {/* Subtle Cotton Bud Drawing Badge Representation */}
            <div className="flex items-center gap-3 rounded-2xl border border-amber-400/20 bg-emerald-950/70 px-4 py-2 shadow-sm backdrop-blur-md">
              <CottonBudDrawing className="size-6 text-amber-200" />
              <div className="text-left">
                <span className="block text-xs font-semibold tracking-wide text-amber-100">
                  कापूस बोंड सल्लागार
                </span>
                <span className="block font-mono text-[10px] text-emerald-300/80">
                  Cotton Bud Advisory
                </span>
              </div>
            </div>

            {/* Main Cotton Logo Image in Soft Ring */}
            <div className="relative size-20 overflow-hidden rounded-full shadow-xl ring-2 shadow-amber-950/40 ring-amber-400/40">
              <Image
                src="/cotton-logo.jpg"
                alt="Cotton Sprout Logo"
                fill
                className="object-cover"
              />
            </div>

            {/* Marathi Title & Prompt */}
            <div className="space-y-1">
              <h3 className="font-serif text-3xl font-bold tracking-wide text-amber-100 sm:text-4xl">
                &lsquo;कृषि मित्र&rsquo;
              </h3>
              <p className="text-xs font-medium text-emerald-200/90">Krushi Mitra Voice Advisor</p>
            </div>

            <p className="max-w-xs text-xs leading-relaxed font-light text-zinc-300">
              &ldquo;नमस्कार शेतकरी दादा, आज कापसाविषयी काय विचारायचे आहे?&rdquo;
            </p>

            {/* Glowing Microphone Call Trigger Button */}
            <div className="relative my-2 flex items-center justify-center">
              <div className="pointer-events-none absolute size-36 animate-ping rounded-full border border-amber-400/20" />
              <div className="pointer-events-none absolute size-44 animate-pulse rounded-full border border-emerald-500/20" />

              <Button
                size="lg"
                onClick={onStartCall}
                className="group relative flex size-28 transform flex-col items-center justify-center gap-1 rounded-full border-4 border-amber-400/40 bg-gradient-to-br from-emerald-600 via-emerald-700 to-amber-600 text-amber-100 shadow-[0_0_60px_rgba(212,175,55,0.35)] transition-all hover:scale-105 active:scale-95"
              >
                <Mic className="size-9 text-amber-200 transition-transform group-hover:scale-110" />
                <span className="text-[11px] font-bold tracking-wider text-amber-100 uppercase">
                  Call Now
                </span>
              </Button>
            </div>
          </div>

          {/* Bottom Action Button */}
          <div className="z-10 w-full text-center">
            <Button
              variant="outline"
              onClick={onStartCall}
              className="w-full gap-2 rounded-full border-amber-500/30 bg-amber-500/10 py-3 text-xs font-semibold text-amber-200 hover:bg-amber-500/20"
            >
              <PhoneCall className="size-3.5 animate-bounce text-amber-400" />
              {startButtonText || 'कॉल सुरू करा (Start Call)'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
