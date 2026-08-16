'use client';

import React from 'react';
import { AgentStatusBadge } from '@/components/app/agent-status-badge';
import { Button } from '@/components/ui/button';
import { Sprout, ShieldCheck, Banknote, Bug, PhoneCall, MapPin } from 'lucide-react';

function CottonSproutIcon() {
  return (
    <div className="relative flex size-20 items-center justify-center rounded-3xl bg-emerald-700/10 p-4 ring-1 ring-emerald-700/30 dark:bg-emerald-500/10 dark:ring-emerald-500/30 shadow-lg shadow-emerald-950/5">
      <Sprout className="size-12 text-emerald-700 dark:text-emerald-400" />
      <div className="absolute -bottom-1 -right-1 flex size-7 items-center justify-center rounded-full bg-emerald-700 text-white shadow-md">
        <PhoneCall className="size-3.5" />
      </div>
    </div>
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
    <div ref={ref} className="mx-auto w-full max-w-3xl px-4 py-8">
      <section className="flex flex-col items-center justify-center text-center">
        {/* Header & Logo */}
        <CottonSproutIcon />

        <div className="mt-4 flex flex-col items-center gap-1.5">
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
            कृषि मित्र <span className="text-emerald-700 dark:text-emerald-400">(Krushi Mitra)</span>
          </h1>
          <p className="max-w-xl text-sm font-medium text-muted-foreground sm:text-base">
            विदर्भातील कापूस उत्पादक शेतकऱ्यांसाठी विश्वासार्ह आवाजी सहाय्यक
          </p>
          <p className="text-xs text-muted-foreground/80">
            Trusted Voice AI Advisor for Cotton Farmers of Vidarbha, Maharashtra
          </p>
        </div>

        {/* 5 Agent States: Explicit READY State */}
        <div className="mt-4">
          <AgentStatusBadge state="ready" />
        </div>

        {/* Target Districts */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="flex items-center gap-1 text-xs text-muted-foreground font-medium mr-1">
            <MapPin className="size-3.5 text-emerald-600 dark:text-emerald-400" />
            प्रमुख जिल्हे:
          </span>
          {['यवतमाळ (Yavatmal)', 'अमरावती (Amravati)', 'अकोला (Akola)', 'वर्धा (Wardha)'].map((district) => (
            <span
              key={district}
              className="rounded-md border border-emerald-600/20 bg-emerald-500/5 px-2.5 py-1 text-[11px] font-medium text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
            >
              {district}
            </span>
          ))}
        </div>

        {/* Start Call Action Button */}
        <Button
          size="lg"
          onClick={onStartCall}
          className="mt-6 h-14 w-full max-w-md rounded-full bg-emerald-700 text-base font-bold tracking-wide text-white shadow-xl shadow-emerald-900/20 transition-all hover:scale-102 hover:bg-emerald-800 active:scale-98 dark:bg-emerald-600 dark:hover:bg-emerald-500"
        >
          <PhoneCall className="mr-2 size-5 animate-pulse" />
          {startButtonText || 'कॉल सुरू करा (Start Call)'}
        </Button>

        {/* Advisory Feature Cards */}
        <div className="mt-10 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-3">
          <div className="rounded-xl border border-border/60 bg-card p-4 shadow-xs transition-colors hover:border-emerald-500/40">
            <div className="flex size-9 items-center justify-center rounded-lg bg-red-500/10 text-red-600 dark:text-red-400">
              <Bug className="size-5" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-foreground">
              बोंड अळी सल्लागार
            </h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              गुलाबी बोंड अळीची (Pink Bollworm) लक्षणे ओळखा व वेळेवर उपाययोजना करा.
            </p>
          </div>

          <div className="rounded-xl border border-border/60 bg-card p-4 shadow-xs transition-colors hover:border-emerald-500/40">
            <div className="flex size-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
              <Banknote className="size-5" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-foreground">
              MSP व CCI खरेदी
            </h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              कापसाचा शासकीय हमीभाव (₹6,620/क्विंटल) व CCI केंद्र मार्गदर्शक.
            </p>
          </div>

          <div className="rounded-xl border border-border/60 bg-card p-4 shadow-xs transition-colors hover:border-emerald-500/40">
            <div className="flex size-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <ShieldCheck className="size-5" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-foreground">
              PMFBY पिक विमा
            </h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              पिकाचे नुकसान झाल्यास विमा भरपाई दाव्याच्या मुदतीबाबत माहिती.
            </p>
          </div>
        </div>
      </section>

      {/* Footer Info */}
      <footer className="mt-8 text-center text-xs text-muted-foreground">
        <p>
          व्हॉईस एजंट मराठी व हिंदी भाषेत उत्तर देतो. (Voice AI responds in Marathi & Hindi)
        </p>
      </footer>
    </div>
  );
};
