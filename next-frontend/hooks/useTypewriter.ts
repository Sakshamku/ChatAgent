"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function useTypewriter() {
  const [displayed, setDisplayed] = useState("");
  const queueRef = useRef("");
  const rafRef = useRef(0);
  const lastTimeRef = useRef(0);

  const tick = useCallback((time: number) => {
    if (queueRef.current.length === 0) {
      rafRef.current = 0;
      return;
    }

    const elapsed = time - lastTimeRef.current;
    if (elapsed >= 12) {
      const step = elapsed >= 36 ? 3 : elapsed >= 24 ? 2 : 1;
      const chars = queueRef.current.slice(0, step);
      queueRef.current = queueRef.current.slice(step);
      setDisplayed((current) => current + chars);
      lastTimeRef.current = time;
    }

    rafRef.current = requestAnimationFrame(tick);
  }, []);

  const append = useCallback(
    (text: string) => {
      if (!text) return;
      queueRef.current += text;
      if (!rafRef.current) {
        lastTimeRef.current = performance.now();
        rafRef.current = requestAnimationFrame(tick);
      }
    },
    [tick]
  );

  const reset = useCallback(() => {
    queueRef.current = "";
    setDisplayed("");
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = 0;
    lastTimeRef.current = 0;
  }, []);

  const flush = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = 0;
    setDisplayed((current) => current + queueRef.current);
    queueRef.current = "";
  }, []);

  const waitUntilDone = useCallback(async () => {
    flush();
    await new Promise<void>((resolve) => {
      const check = () => {
        if (queueRef.current.length === 0 && !rafRef.current) {
          resolve();
          return;
        }
        requestAnimationFrame(check);
      };
      check();
    });
  }, [flush]);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return { displayed, append, reset, flush, waitUntilDone };
}
