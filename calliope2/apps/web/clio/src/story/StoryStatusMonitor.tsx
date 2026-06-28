/**
 * Silent realtime watcher over a story's generation tasks (Firestore via
 * `watchTasksForStory`). Fires `onCompleted` when a task finishes (so the viewer
 * refetches + advances) and `onFailed` on error. While a task runs it shows an
 * inline corner spinner + one-line status — it never blocks reading existing
 * frames.
 *
 * The subscription depends only on `userId`/`storyId`. The callbacks are read
 * through refs so that a parent re-render (e.g. `onCompleted` → `setStory` →
 * a new `onCompleted` identity) does NOT tear down and re-create the
 * subscription. Re-subscribing would reset the dedup set and, because Firestore
 * re-delivers the current snapshot on subscribe and the completed task doc
 * persists in the query, would re-fire `onCompleted` in an unbounded loop.
 */

import React, { useEffect, useRef, useState } from 'react';

import Loader from '../components/Loader';
import { watchTasksForStory } from '../services/firebase';
import { TaskStatus } from './storyTypes';

import './StoryStatusMonitor.css';

export default function StoryStatusMonitor({
  userId,
  storyId,
  onCompleted,
  onFailed,
}: {
  userId: string;
  storyId: number;
  onCompleted: () => void;
  onFailed: (message: string) => void;
}) {
  const [active, setActive] = useState(false);
  const [label, setLabel] = useState('Imagining…');
  // Fire each terminal transition exactly once (per story subscription).
  const handled = useRef<Set<string>>(new Set());

  // Latest callbacks, read inside the snapshot handler without re-subscribing.
  const onCompletedRef = useRef(onCompleted);
  const onFailedRef = useRef(onFailed);
  onCompletedRef.current = onCompleted;
  onFailedRef.current = onFailed;

  useEffect(() => {
    handled.current = new Set();
    const unsub = watchTasksForStory(userId, storyId, (tasks: TaskStatus[]) => {
      const running = tasks.some(
        t => t.status === 'pending' || t.status === 'running'
      );
      setActive(running);
      if (running) {
        const t = tasks.find(x => x.status === 'running') ?? tasks[0];
        setLabel(
          t?.type === 'create_story'
            ? 'Beginning the story…'
            : 'Imagining the next frame…'
        );
      }
      for (const t of tasks) {
        const key = t.task_id ?? `${t.story_id}-${t.started_at}`;
        if (handled.current.has(key)) continue;
        if (t.status === 'completed') {
          handled.current.add(key);
          onCompletedRef.current();
        } else if (t.status === 'failed') {
          handled.current.add(key);
          onFailedRef.current(t.error || 'Generation failed.');
        }
      }
    });
    return () => unsub();
  }, [userId, storyId]);

  if (!active) return null;
  return (
    <div className="status-monitor" role="status" aria-live="polite">
      <Loader size="inline" />
      <span className="type-meta status-monitor__label">{label}</span>
    </div>
  );
}
