// Background music: loops one bundled track at a gentle volume, with a visible
// on/off button (SVG speaker icon; a speaker-with-X when muted). Theme-aware via
// the game's CSS variables (works in dark and light mode).
// Swap frontend/audio/music/loop.mp3 to change the music (same filename/path).
const SRC = "./audio/music/loop.mp3";
const DEFAULT_VOLUME = 0.25; // gentle — must not distract from learning
const STORAGE_KEY = "asl_music_on";

const ICON_ON = `
<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor"
     stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M11 5 L6 9 H2 v6 h4 l5 4 Z" fill="currentColor" stroke="none"/>
  <path d="M15.5 8.5 a5 5 0 0 1 0 7"/>
  <path d="M18.8 6 a9 9 0 0 1 0 12"/>
</svg>`;

const ICON_OFF = `
<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor"
     stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M11 5 L6 9 H2 v6 h4 l5 4 Z" fill="currentColor" stroke="none"/>
  <line x1="16" y1="9" x2="22" y2="15"/>
  <line x1="22" y1="9" x2="16" y2="15"/>
</svg>`;

const STYLE = `
.aslm-music-btn {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  padding: 0;
  border-radius: 12px;
  border: 2px solid var(--border, #2d3f5e);
  background: var(--bg-card, #1f2b47);
  color: var(--accent, #4ade80);
  box-shadow: 0 4px 14px var(--shadow, rgba(0,0,0,0.4));
  cursor: pointer;
  transition: color .2s ease, border-color .2s ease, transform .1s ease, background .4s ease;
}
.aslm-music-btn:hover { border-color: var(--accent, #4ade80); }
.aslm-music-btn:active { transform: scale(0.92); }
.aslm-music-btn:focus-visible { outline: 2px solid var(--accent, #4ade80); outline-offset: 2px; }
.aslm-music-btn.muted { color: var(--text-secondary, #cbd5e1); }
@media (max-width: 600px) {
  .aslm-music-btn { top: 12px; right: 12px; width: 42px; height: 42px; }
}`;

export function initBackgroundMusic() {
  const audio = new Audio(SRC);
  audio.loop = true;
  audio.volume = DEFAULT_VOLUME;
  audio.preload = "auto";

  let on = true;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) on = saved === "1";
  } catch (e) {}

  const style = document.createElement("style");
  style.textContent = STYLE;
  document.head.appendChild(style);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "aslm-music-btn";

  function render() {
    btn.classList.toggle("muted", !on);
    btn.innerHTML = on ? ICON_ON : ICON_OFF;
    const label = on ? "Mute music" : "Play music";
    btn.setAttribute("aria-label", label);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.title = label;
  }
  render();

  // Vertically center the button on the theme toggle so the two controls line up.
  function alignToToggle() {
    const t = document.querySelector(".theme-toggle");
    if (!t) return; // fall back to the CSS `top` if the toggle isn't present
    const r = t.getBoundingClientRect();
    btn.style.top = Math.round(r.top + r.height / 2 - btn.offsetHeight / 2) + "px";
  }
  const mount = () => {
    document.body.appendChild(btn);
    alignToToggle();
    requestAnimationFrame(alignToToggle); // re-align after layout/fonts settle
  };
  if (document.body) mount();
  else window.addEventListener("DOMContentLoaded", mount);
  window.addEventListener("resize", alignToToggle);

  let started = false;
  function play() {
    audio.play().then(() => { started = true; }).catch(() => {});
  }

  // Autoplay policies require a user gesture; start on the first interaction.
  function onFirstGesture() {
    if (on) play();
    window.removeEventListener("pointerdown", onFirstGesture);
    window.removeEventListener("keydown", onFirstGesture);
  }
  window.addEventListener("pointerdown", onFirstGesture);
  window.addEventListener("keydown", onFirstGesture);

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    on = !on;
    try { localStorage.setItem(STORAGE_KEY, on ? "1" : "0"); } catch (e) {}
    if (on) play(); else audio.pause();
    render();
  });

  return { isOn: () => on };
}
