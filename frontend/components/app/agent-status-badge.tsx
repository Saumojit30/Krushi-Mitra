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
    labelEn: string;
    badgeBg: string;
    textColor: string;
    borderColor: string;
    pulseColor: string;
  }
> = {
  ready: {
    labelMr: 'कॉलसाठी तयार',
    labelEn: 'Ready to assist',
    badgeBg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    textColor: 'text-emerald-700 dark:text-emerald-300',
    borderColor: 'border-emerald-500/30',
    pulseColor: 'bg-emerald-500',
  },
  connecting: {
    labelMr: 'कॉल जोडत आहे...',
    labelEn: 'Connecting to Krushi Mitra...',
    badgeBg: 'bg-amber-500/10 dark:bg-amber-500/20',
    textColor: 'text-amber-700 dark:text-amber-300',
    borderColor: 'border-amber-500/30',
    pulseColor: 'bg-amber-500',
  },
  listening: {
    labelMr: 'ऐकत आहे... (तुम्ही बोला)',
    labelEn: 'Listening to you',
    badgeBg: 'bg-emerald-500/15 dark:bg-emerald-500/25',
    textColor: 'text-emerald-800 dark:text-emerald-200',
    borderColor: 'border-emerald-500/40',
    pulseColor: 'bg-emerald-500',
  },
  thinking: {
    labelMr: 'विचार करत आहे...',
    labelEn: 'Krushi Mitra is thinking...',
    badgeBg: 'bg-blue-500/10 dark:bg-blue-500/20',
    textColor: 'text-blue-700 dark:text-blue-300',
    borderColor: 'border-blue-500/30',
    pulseColor: 'bg-blue-500',
  },
  speaking: {
    labelMr: 'कृषि मित्र बोलत आहेत...',
    labelEn: 'Krushi Mitra is speaking',
    badgeBg: 'bg-purple-500/15 dark:bg-purple-500/25',
    textColor: 'text-purple-800 dark:text-purple-200',
    borderColor: 'border-purple-500/40',
    pulseColor: 'bg-purple-500',
  },
  ended: {
    labelMr: 'कॉल संपला',
    labelEn: 'Call ended',
    badgeBg: 'bg-zinc-500/10 dark:bg-zinc-500/20',
    textColor: 'text-zinc-700 dark:text-zinc-300',
    borderColor: 'border-zinc-500/30',
    pulseColor: 'bg-zinc-400',
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
        initial={{ opacity: 0, y: -6, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 6, scale: 0.95 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={cn(
          'inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5 text-xs font-semibold backdrop-blur-md shadow-xs',
          config.badgeBg,
          config.textColor,
          config.borderColor,
          className
        )}
      >
        {/* Animated Icon Container */}
        <span className="relative flex size-3.5 items-center justify-center">
          {state === 'listening' && (
            <>
              <span
                className={cn(
                  'absolute inline-flex size-full animate-ping rounded-full opacity-75',
                  config.pulseColor
                )}
              />
              <Mic className="size-3.5" />
            </>
          )}

          {state === 'speaking' && (
            <>
              <span
                className={cn(
                  'absolute inline-flex size-full animate-ping rounded-full opacity-75',
                  config.pulseColor
                )}
              />
              <Volume2 className="size-3.5" />
            </>
          )}

          {state === 'connecting' && (
            <RefreshCw className="size-3.5 animate-spin" />
          )}

          {state === 'thinking' && <Sparkles className="size-3.5 animate-pulse" />}

          {state === 'ready' && (
            <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />
          )}

          {state === 'ended' && <PhoneOff className="size-3.5" />}
        </span>

        {/* Status Label (Bilingual) */}
        <div className="flex items-center gap-1.5">
          <span className="font-medium tracking-wide">{config.labelMr}</span>
          <span className="opacity-40">|</span>
          <span className="text-[11px] font-normal opacity-80">{config.labelEn}</span>
        </div>

        {/* Restart Button if Call Ended */}
        {state === 'ended' && onRestartCall && (
          <button
            onClick={onRestartCall}
            className="ml-1.5 rounded-full bg-emerald-700 px-2.5 py-0.5 text-[10px] text-white transition-colors hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500"
          >
            पुन्हा कॉल करा (Restart)
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
