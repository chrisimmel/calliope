/**
 * Top-center toast pill (spec §6.8). Used for share confirmations ("Link
 * copied") and non-blocking errors. Auto-dismisses; an error toast can carry a
 * retry action. Chrome element.
 */

import React, { useEffect } from 'react';

import './Toast.css';

export type ToastState = {
  message: string;
  kind?: 'info' | 'error';
  /** Optional retry affordance (e.g. re-run a failed generation). */
  onRetry?: () => void;
};

export default function Toast({
  toast,
  onDismiss,
  durationMs = 2200,
}: {
  toast: ToastState | null;
  onDismiss: () => void;
  durationMs?: number;
}) {
  useEffect(() => {
    if (!toast) return;
    // Errors with a retry stay until dismissed; everything else auto-hides.
    if (toast.kind === 'error' && toast.onRetry) return;
    const t = window.setTimeout(onDismiss, durationMs);
    return () => window.clearTimeout(t);
  }, [toast, durationMs, onDismiss]);

  if (!toast) return null;
  return (
    <div
      className={`toast toast--${toast.kind ?? 'info'}`}
      role={toast.kind === 'error' ? 'alert' : 'status'}
      aria-live="polite"
    >
      <span className="toast__message">{toast.message}</span>
      {toast.onRetry && (
        <button
          className="toast__action"
          onClick={() => {
            toast.onRetry?.();
            onDismiss();
          }}
        >
          Retry
        </button>
      )}
      <button className="toast__close" onClick={onDismiss} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
