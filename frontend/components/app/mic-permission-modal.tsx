'use client';

import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MicOff, RefreshCw, AlertTriangle, Lock, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MicPermissionModalProps {
  isOpen: boolean;
  onRetry: () => void;
  onClose: () => void;
}

export function MicPermissionModal({
  isOpen,
  onRetry,
  onClose,
}: MicPermissionModalProps) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 10 }}
          className="w-full max-w-md overflow-hidden rounded-2xl border border-red-500/20 bg-background shadow-2xl"
        >
          {/* Header Banner */}
          <div className="bg-red-500/10 px-6 py-4 border-b border-red-500/10 flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-full bg-red-500/20 text-red-600 dark:text-red-400">
              <MicOff className="size-5" />
            </div>
            <div>
              <h3 className="font-semibold text-base text-foreground">
                मायक्रोफोनची परवानगी आवश्यक आहे
              </h3>
              <p className="text-xs text-muted-foreground">
                Microphone Access Blocked or Required
              </p>
            </div>
          </div>

          {/* Content Body */}
          <div className="p-6 space-y-4 text-sm">
            <div className="flex items-start gap-2.5 rounded-lg bg-amber-500/10 p-3 text-amber-900 dark:text-amber-200 text-xs">
              <AlertTriangle className="size-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
              <span>
                कृषि मित्राशी बोलण्यासाठी आपल्या ब्राऊझरमध्ये मायक्रोफोनची परवानगी द्यावी लागेल.
                (Krushi Mitra needs microphone access to converse with you.)
              </span>
            </div>

            <div className="space-y-2">
              <p className="font-medium text-xs text-muted-foreground uppercase tracking-wider">
                परवानगी कशी द्यावी? (How to allow microphone?):
              </p>

              <ol className="space-y-2 text-xs text-foreground">
                <li className="flex items-center gap-2">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold">
                    1
                  </span>
                  <Lock className="size-3.5 text-muted-foreground shrink-0" />
                  <span>
                    ब्राऊझरच्या ॲड्रेस बारमधील **लॉक (🔒)** आयकॉनवर क्लिक करा.
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold">
                    2
                  </span>
                  <Settings className="size-3.5 text-muted-foreground shrink-0" />
                  <span>
                    **मायक्रोफोन (Microphone)** परवानगी "Allow" करा.
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold">
                    3
                  </span>
                  <RefreshCw className="size-3.5 text-muted-foreground shrink-0" />
                  <span>
                    पुन्हा प्रयत्न करा बटण दाबा किंवा पेज रीफ्रेश करा.
                  </span>
                </li>
              </ol>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="bg-muted/40 px-6 py-3.5 border-t flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="text-xs"
            >
              रद्द करा (Cancel)
            </Button>
            <Button
              size="sm"
              onClick={onRetry}
              className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs gap-1.5"
            >
              <RefreshCw className="size-3.5" />
              पुन्हा प्रयत्न करा (Try Again)
            </Button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
