"""Generate a calm, license-free ambient background loop for the game.

Self-authored (procedurally synthesized) — no third-party samples, so it is
free to bundle and redistribute (treat as CC0 / public domain).
Output: frontend/audio/music/loop.mp3. Re-run: `python3 build/generate_music.py`.

The music is intentionally CALM and quiet — this game teaches ASL to children,
so the loop must stay gentle and never distract from learning. It is soft sine
"pad" chords that slowly swell in and out over a soothing C–G–Am–F progression,
with a sparse, quiet high melody.

TO CHANGE THE MUSIC LATER:
  - Easiest: replace frontend/audio/music/loop.mp3 with any track you like
    (keep the same path/filename; the game just loops that file).
  - Or tweak the parameters below (TEMPO/PROGRESSION/MELODY/volumes) and re-run
    this script to regenerate loop.mp3.
"""
import os
import subprocess
import numpy as np

# ── Tweakable parameters ───────────────────────────────────────────
SR = 44100
BPM = 66                       # slow + calming
CHORD_BEATS = 4                # each chord swells over 4 beats (~3.6s)
PROGRESSION = ["C", "G", "Am", "F"]   # soothing I–V–vi–IV
PAD_LEVEL = 0.45               # chord pad loudness (kept gentle)
MELODY_LEVEL = 0.16            # sparse melody, quieter than the pad
MASTER_PEAK = 0.55             # final normalization target (quiet overall)
# ───────────────────────────────────────────────────────────────────

_SEMITONE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
             "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi(name, octave):
    return 12 * (octave + 1) + _SEMITONE[name]


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# Chord -> (root name, root octave, triad-tone offsets)
CHORDS = {
    "C":  ("C", 4, [0, 4, 7]),   # C E G
    "G":  ("G", 3, [0, 4, 7]),   # G B D
    "Am": ("A", 3, [0, 3, 7]),   # A C E
    "F":  ("F", 3, [0, 4, 7]),   # F A C
}


def sine(f, n):
    return np.sin(2 * np.pi * f * (np.arange(n) / SR))


def swell_env(n, attack=0.45, release=0.55):
    """Slow swell in/out; returns to 0 at both ends (seamless, no clicks)."""
    e = np.ones(n)
    a = min(int(attack * SR), n // 2)
    r = min(int(release * SR), n // 2)
    # smooth (raised-cosine) fades for a soft, calming attack/release
    if a > 0:
        e[:a] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if r > 0:
        e[-r:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return e


def note_env(n, attack=0.06, release=0.4):
    e = np.ones(n)
    a = min(int(attack * SR), n // 2)
    r = min(int(release * SR), n // 2)
    if a > 0:
        e[:a] = np.linspace(0, 1, a)
    if r > 0:
        e[-r:] = np.linspace(1, 0, r)
    return e


def main():
    beat = 60.0 / BPM
    chord_n = int(CHORD_BEATS * beat * SR)
    total_n = chord_n * len(PROGRESSION)
    buf = np.zeros(total_n, dtype=np.float64)

    pad_env = swell_env(chord_n)

    for i, chord in enumerate(PROGRESSION):
        root_name, root_oct, offsets = CHORDS[chord]
        root_m = midi(root_name, root_oct)
        start = i * chord_n

        # Soft pad: triad tones as sines, each swelling in/out over the chord
        pad = np.zeros(chord_n)
        for o in offsets:
            pad += sine(freq(root_m + o), chord_n)
        pad += 0.6 * sine(freq(root_m - 12), chord_n)   # gentle low root
        pad = (pad / (len(offsets) + 0.6)) * pad_env * PAD_LEVEL
        buf[start:start + chord_n] += pad

        # Sparse, quiet melody: two long soft notes from the chord's upper tones
        half = chord_n // 2
        mel_notes = [root_m + 12 + offsets[2], root_m + 12 + offsets[1]]  # 5th, 3rd up an octave
        for j, m in enumerate(mel_notes):
            s = start + j * half
            buf[s:s + half] += sine(freq(m), half) * note_env(half) * MELODY_LEVEL

    # Normalize to a quiet master level (calm, non-intrusive)
    peak = np.max(np.abs(buf)) or 1.0
    buf = (buf / peak) * MASTER_PEAK

    pcm16 = (buf * 32767).astype("<i2")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "audio", "music")
    os.makedirs(out_dir, exist_ok=True)
    mp3_path = os.path.join(out_dir, "loop.mp3")

    proc = subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1",
         "-i", "pipe:0", "-b:a", "128k", mp3_path],
        input=pcm16.tobytes(),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed to encode loop.mp3")

    print(f"wrote {mp3_path} — {total_n / SR:.1f}s, {os.path.getsize(mp3_path)} bytes")


if __name__ == "__main__":
    main()
