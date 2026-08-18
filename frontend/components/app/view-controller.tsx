'use client';

import { useCallback, useState } from 'react';
import { useTheme } from 'next-themes';
import { PhoneCall, PhoneOff } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { type AgentStateDisplay, AgentStatusBadge } from '@/components/app/agent-status-badge';
import { MicPermissionModal } from '@/components/app/mic-permission-modal';
import { WelcomeView } from '@/components/app/welcome-view';
import { Button } from '@/components/ui/button';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1 },
    hidden: { opacity: 0 },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: { duration: 0.4, ease: 'linear' },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, isConnecting, start, end } = useSessionContext();
  const { state: agentState } = useAgent();
  const { resolvedTheme } = useTheme();

  const [hasEndedCall, setHasEndedCall] = useState(false);
  const [isMicErrorOpen, setIsMicErrorOpen] = useState(false);

  // Intercept call start to catch mic permission errors
  const handleStartCall = useCallback(async () => {
    setHasEndedCall(false);
    try {
      // Check microphone permission if available
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          // Stop temporary stream immediately after verification
          stream.getTracks().forEach((track) => track.stop());
        } catch (err: unknown) {
          if (
            err instanceof Error &&
            (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
          ) {
            setIsMicErrorOpen(true);
            return;
          }
        }
      }
      await start();
    } catch (error) {
      console.error('Failed to start session:', error);
      setIsMicErrorOpen(true);
    }
  }, [start]);

  const handleEndCall = useCallback(() => {
    end();
    setHasEndedCall(true);
  }, [end]);

  // Determine current display state for the status badge
  const currentDisplayState: AgentStateDisplay = (function () {
    if (isConnecting || agentState === 'initializing') return 'connecting';
    if (hasEndedCall && !isConnected) return 'ended';
    if (isConnected) {
      if (agentState === 'speaking') return 'speaking';
      if (agentState === 'thinking') return 'thinking';
      if (agentState === 'listening') return 'listening';
      return 'listening';
    }
    return 'ready';
  })();

  return (
    <>
      {/* Microphone Permission Modal */}
      <MicPermissionModal
        isOpen={isMicErrorOpen}
        onClose={() => setIsMicErrorOpen(false)}
        onRetry={() => {
          setIsMicErrorOpen(false);
          handleStartCall();
        }}
      />

      <AnimatePresence mode="wait">
        {/* State 5: Call Ended View */}
        {!isConnected && hasEndedCall && (
          <motion.div
            key="call-ended"
            {...VIEW_MOTION_PROPS}
            className="mx-auto flex w-full max-w-md flex-col items-center justify-center p-6 text-center"
          >
            <section className="flex w-full flex-col items-center justify-center rounded-3xl border border-zinc-800/50 bg-zinc-950/60 p-10 text-center shadow-2xl shadow-black/50 backdrop-blur-2xl">
              <div className="flex size-16 items-center justify-center rounded-full bg-white/10 text-white">
                <PhoneOff className="size-8" />
              </div>

              <div className="mt-4 mb-2">
                <AgentStatusBadge state="ended" />
              </div>

              <h2 className="mt-2 text-xl font-medium tracking-wide text-white">कॉल संपला</h2>
              <p className="mt-1 text-sm font-light text-zinc-300">Krushi Mitra session ended.</p>

              <Button
                size="lg"
                onClick={handleStartCall}
                className="mt-8 gap-2 rounded-full bg-emerald-700 text-sm font-medium text-white transition-transform hover:scale-105 hover:bg-emerald-600 active:scale-95"
              >
                <PhoneCall className="size-4" />
                नवा कॉल सुरू करा
              </Button>
            </section>
          </motion.div>
        )}

        {/* State 1 & 2: Welcome View (Ready / Connecting) */}
        {!isConnected && !hasEndedCall && (
          <MotionWelcomeView
            key="welcome"
            {...VIEW_MOTION_PROPS}
            startButtonText={
              isConnecting ? 'कॉल जोडत आहे... (Connecting...)' : appConfig.startButtonText
            }
            onStartCall={handleStartCall}
          />
        )}

        {/* State 3 & 4: Active Session View (Listening / Speaking / Thinking) */}
        {isConnected && (
          <div key="active-session" className="fixed inset-0 z-40">
            {/* Top Status Bar showing 5 Agent States clearly */}
            <div className="pointer-events-none absolute inset-x-0 top-4 z-50 flex justify-center">
              <div className="pointer-events-auto">
                <AgentStatusBadge state={currentDisplayState} onRestartCall={handleEndCall} />
              </div>
            </div>

            <MotionSessionView
              key="session-view"
              {...VIEW_MOTION_PROPS}
              supportsChatInput={appConfig.supportsChatInput}
              supportsVideoInput={appConfig.supportsVideoInput}
              supportsScreenShare={appConfig.supportsScreenShare}
              isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
              audioVisualizerType={appConfig.audioVisualizerType}
              audioVisualizerColor={
                resolvedTheme === 'dark'
                  ? appConfig.audioVisualizerColorDark
                  : appConfig.audioVisualizerColor
              }
              audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
              audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
              audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
              audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
              audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
              audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
              audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
              className="fixed inset-0"
            />
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
