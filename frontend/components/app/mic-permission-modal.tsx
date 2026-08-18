'use client';

import React from 'react';
import { AlertTriangle, Lock, MicOff, RefreshCw, Settings } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { Button } from '@/components/ui/button';

interface MicPermissionModalProps {
  isOpen: boolean;
  onRetry: () => void;
  onClose: () => void;
}

export function MicPermissionModal({ isOpen, onRetry, onClose }: MicPermissionModalProps) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 10 }}
          className="bg-background w-full max-w-md overflow-hidden rounded-2xl border border-red-500/20 shadow-2xl"
        >
          {/* Header Banner */}
          <div className="flex items-center gap-3 border-b border-red-500/10 bg-red-500/10 px-6 py-4">
            <div className="flex size-10 items-center justify-center rounded-full bg-red-500/20 text-red-600 dark:text-red-400">
              <MicOff className="size-5" />
            </div>
            <div>
              <h3 className="text-foreground text-base font-semibold">
                मायक्रोफोनची परवानगी आवश्यक आहे
              </h3>
              <p className="text-muted-foreground text-xs">Microphone Access Blocked or Required</p>
            </div>
          </div>

          {/* Content Body */}
          <div className="space-y-4 p-6 text-sm">
            <div className="flex items-start gap-2.5 rounded-lg bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
              <span>
                कृषि मित्राशी बोलण्यासाठी आपल्या ब्राऊझरमध्ये मायक्रोफोनची परवानगी द्यावी लागेल.
                (Krushi Mitra needs microphone access to converse with you.)
              </span>
            </div>

            <div className="space-y-2">
              <p className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                परवानगी कशी द्यावी? (How to allow microphone?):
              </p>

              <ol className="text-foreground space-y-2 text-xs">
                <li className="flex items-center gap-2">
                  <span className="bg-muted flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">
                    1
                  </span>
                  <Lock className="text-muted-foreground size-3.5 shrink-0" />
                  <span>ब्राऊझरच्या ॲड्रेस बारमधील **लॉक (🔒)** आयकॉनवर क्लिक करा.</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="bg-muted flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">
                    2
                  </span>
                  <Settings className="text-muted-foreground size-3.5 shrink-0" />
                  <span>**मायक्रोफोन (Microphone)** परवानगी &quot;Allow&quot; करा.</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="bg-muted flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">
                    3
                  </span>
                  <RefreshCw className="text-muted-foreground size-3.5 shrink-0" />
                  <span>पुन्हा प्रयत्न करा बटण दाबा किंवा पेज रीफ्रेश करा.</span>
                </li>
              </ol>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="bg-muted/40 flex items-center justify-end gap-2 border-t px-6 py-3.5">
            <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
              रद्द करा (Cancel)
            </Button>
            <Button
              size="sm"
              onClick={onRetry}
              className="gap-1.5 bg-emerald-700 text-xs text-white hover:bg-emerald-800"
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
