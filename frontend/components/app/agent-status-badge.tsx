'use client';

import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Mic,
  Volume2,
  PhoneOff,
  CheckCircle2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/shadcn/utils';

export type AgentStateDisplay =
  | 'ready'
  | 'connecting'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'ended';

interface AgentStatusBadgeProps {
  state: AgentStateDisplay;
  className?: string;
  onRestartCall?: () => void;
}

const STATE_CONFIG: Record<
  AgentStateDisplay,
  {
    labelMr: string;
    bgClass: string;
    textClass: string;
    pulseClass: string;
  }
> = {
  ready: {
    labelMr: 'कॉलसाठी तयार (Ready)',
    bgClass: 'bg-emerald-950/80 border-emerald-500/40',
    textClass: 'text-emerald-300',
    pulseClass: 'bg-emerald-400',
  },
  connecting: {
    labelMr: 'कॉल जोडत आहे...',
    bgClass: 'bg-amber-950/80 border-amber-500/40',
    textClass: 'text-amber-300',
    pulseClass: 'bg-amber-400',
  },
  listening: {
    labelMr: 'ऐकत आहे... (Speak Now)',
    bgClass: 'bg-emerald-950/90 border-emerald-400/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]',
    textClass: 'text-emerald-200 font-semibold',
    pulseClass: 'bg-emerald-400',
  },
  thinking: {
    labelMr: 'विचार करत आहे...',
    bgClass: 'bg-amber-950/90 border-amber-400/50',
    textClass: 'text-amber-200',
    pulseClass: 'bg-amber-400',
  },
  speaking: {
    labelMr: 'कृषि मित्र बोलत आहेत...',
    bgClass: 'bg-amber-900/80 border-amber-400/50 shadow-[0_0_15px_rgba(245,158,11,0.25)]',
    textClass: 'text-amber-100 font-semibold',
    pulseClass: 'bg-amber-300',
  },
  ended: {
    labelMr: 'कॉल संपला (Ended)',
    bgClass: 'bg-zinc-900/80 border-zinc-700/50',
    textClass: 'text-zinc-400',
    pulseClass: 'bg-zinc-500',
  },
};

export function AgentStatusBadge({
  state,
  className,
  onRestartCall,
}: AgentStatusBadgeProps) {
  const config = STATE_CONFIG[state] || STATE_CONFIG.ready;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={state}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
        className={cn(
          'inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium backdrop-blur-md shadow-md transition-colors',
          config.bgClass,
          config.textClass,
          className
        )}
      >
        {/* Status Icon */}
        <span className="relative flex size-3.5 items-center justify-center">
          {state === 'listening' && (
            <>
              <span className={cn('absolute inline-flex size-full animate-ping rounded-full opacity-75', config.pulseClass)} />
              <Mic className="size-3.5" />
            </>
          )}

          {state === 'speaking' && (
            <>
              <span className={cn('absolute inline-flex size-full animate-ping rounded-full opacity-75', config.pulseClass)} />
              <Volume2 className="size-3.5" />
            </>
          )}

          {state === 'connecting' && <RefreshCw className="size-3.5 animate-spin" />}
          {state === 'thinking' && <Sparkles className="size-3.5 animate-pulse" />}
          {state === 'ready' && <CheckCircle2 className="size-3.5 text-emerald-400" />}
          {state === 'ended' && <PhoneOff className="size-3.5" />}
        </span>

        {/* Marathi Label */}
        <span className="tracking-wide">{config.labelMr}</span>

        {/* Restart Button if Call Ended */}
        {state === 'ended' && onRestartCall && (
          <button
            onClick={onRestartCall}
            className="ml-2 flex items-center gap-1 rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 px-2.5 py-0.5 text-[11px] transition-colors"
          >
            पुन्हा कॉल करा
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
