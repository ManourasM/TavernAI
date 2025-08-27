// src/utils/sounds.js
import { useEffect, useRef, useState } from "react";

/**
 * useSounds hook
 * - persistent mute via localStorage key "tavern_sounds_muted"
 * - playNewOrderSound() : for station when new items arrive
 * - playDoneSound() : for waiter when items become ready
 */
const LOCAL_KEY = "tavern_sounds_muted_v1";

export function useSounds() {
  const audioCtxRef = useRef(null);
  const lastPlayedRef = useRef(0);
  const [muted, setMuted] = useState(() => {
    try {
      const v = localStorage.getItem(LOCAL_KEY);
      return v === "1";
    } catch {
      return false;
    }
  });

  // create/resume AudioContext
  function ensureAudio() {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtxRef.current;
  }

  // resume on user interaction (some mobile browsers require it)
  useEffect(() => {
    function resume() {
      try {
        const ctx = audioCtxRef.current;
        if (ctx && ctx.state === "suspended") {
          ctx.resume().catch(() => {});
        }
      } catch (e) {}
      window.removeEventListener("pointerdown", resume);
    }
    window.addEventListener("pointerdown", resume);
    return () => window.removeEventListener("pointerdown", resume);
  }, []);

  function saveMuted(v) {
    try {
      localStorage.setItem(LOCAL_KEY, v ? "1" : "0");
    } catch {}
  }

  function toggleMute() {
    setMuted(prev => {
      const n = !prev;
      saveMuted(n);
      return n;
    });
  }

  function playTone(freq, duration = 0.18, type = "sine", vol = 0.09) {
    if (muted) return;
    const ctx = ensureAudio();
    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      // ramp the volume down exponentially so it sounds natural
      gain.gain.value = vol;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      gain.gain.setValueAtTime(vol, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.stop(now + duration + 0.04);
    } catch (e) {
      // degrade silently if audio API fails
      // console.warn("playTone failed", e);
    }
  }

  // small rate limiter to avoid multiple quick duplicates
  function playWithRateLimit(fn, minInterval = 220) {
    const now = Date.now();
    if (now - lastPlayedRef.current < minInterval) return;
    lastPlayedRef.current = now;
    fn();
  }

  // Station: new order sound (slightly ascending pair)
  function playNewOrderSound() {
    if (muted) return;
    playWithRateLimit(() => {
      playTone(740, 0.16, "sine", 0.11);
      setTimeout(() => playTone(1040, 0.16, "sine", 0.09), 140);
    }, 200);
  }

  // Waiter: item done — also longer and more noticeable
function playDoneSound() {
  if (muted) return;
  playWithRateLimit(() => {
    playTone(660, 0.4, "triangle", 0.25);
    setTimeout(() => playTone(440, 0.5, "triangle", 0.22), 300);
    setTimeout(() => playTone(550, 0.5, "triangle", 0.20), 650);
  }, 500);
}

  return {
    muted,
    toggleMute,
    ensureAudio,
    playNewOrderSound,
    playDoneSound,
  };
}
