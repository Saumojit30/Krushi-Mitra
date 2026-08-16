'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { AgentStatusBadge, type AgentStateDisplay } from '@/components/app/agent-status-badge';
import { MicPermissionModal } from '@/components/app/mic-permission-modal';
import { Button } from '@/components/ui/button';
import { PhoneCall, PhoneOff } from 'lucide-react';

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
            className="flex flex-col items-center justify-center p-6 text-center mx-auto w-full max-w-md"
          >
            <section className="flex flex-col items-center justify-center text-center rounded-3xl bg-zinc-950/60 backdrop-blur-2xl border border-zinc-800/50 p-10 shadow-2xl shadow-black/50 w-full">
              <div className="flex size-16 items-center justify-center rounded-full bg-white/10 text-white">
                <PhoneOff className="size-8" />
              </div>

              <div className="mt-4 mb-2">
                <AgentStatusBadge state="ended" />
              </div>

              <h2 className="mt-2 text-xl font-medium text-white tracking-wide">
                कॉल संपला
              </h2>
              <p className="mt-1 text-sm text-zinc-300 font-light">
                Krushi Mitra session ended.
              </p>

              <Button
                size="lg"
                onClick={handleStartCall}
                className="mt-8 rounded-full bg-emerald-700 hover:bg-emerald-600 text-white font-medium text-sm gap-2 transition-transform hover:scale-105 active:scale-95"
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
            <div className="absolute top-4 inset-x-0 z-50 flex justify-center pointer-events-none">
              <div className="pointer-events-auto">
                <AgentStatusBadge
                  state={currentDisplayState}
                  onRestartCall={handleEndCall}
                />
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
