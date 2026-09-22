// Background music: loops one bundled track at a gentle volume.
// Swap frontend/audio/music/loop.mp3 to change the music (same filename/path).
const SRC = "./audio/music/loop.mp3";
const DEFAULT_VOLUME = 0.25; // gentle — must not distract from learning
const STORAGE_KEY = "asl_music_on";

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

  const btn = document.createElement("button");
  btn.type = "button";
  btn.setAttribute("aria-label", "Toggle background music");
  Object.assign(btn.style, {
    position: "fixed", bottom: "12px", right: "12px", zIndex: "9999",
    width: "40px", height: "40px", borderRadius: "8px", cursor: "pointer",
    border: "2px solid rgba(255,255,255,0.5)", background: "rgba(0,0,0,0.55)",
    color: "#fff", font: "16px monospace", lineHeight: "1", padding: "0",
  });
  function render() {
    btn.textContent = on ? "♪" : "🔇"; // musical note / muted speaker
    btn.style.opacity = on ? "1" : "0.6";
  }
  render();
  const mount = () => document.body.appendChild(btn);
  if (document.body) mount(); else window.addEventListener("DOMContentLoaded", mount);

  let started = false;
  function play() { audio.play().then(() => { started = true; }).catch(() => {}); }

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
