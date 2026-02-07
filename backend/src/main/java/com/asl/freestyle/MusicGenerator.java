package com.asl.freestyle;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.random.RandomGenerator;

/**
 * Generate short random music as WAV (no external ASL/vision).
 * Uses a simple pentatonic scale and random rhythm for a "freestyle" feel.
 */
public final class MusicGenerator {

    private static final int SAMPLE_RATE = 44100;
    private static final int CHANNELS = 2;

    // Pentatonic scale (C major) in Hz
    private static final double[] SCALE = {
        261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25
    };

    private final RandomGenerator rng = RandomGenerator.getDefault();

    /**
     * Generate random melody as WAV bytes.
     * Uses a pentatonic scale so it always sounds musical.
     */
    public byte[] generateRandomMusic(double durationSec) throws IOException {
        double[] scaleLow = new double[SCALE.length];
        for (int i = 0; i < SCALE.length; i++) {
            scaleLow[i] = SCALE[i] * 0.5;
        }
        double[] allNotes = new double[SCALE.length * 2];
        System.arraycopy(scaleLow, 0, allNotes, 0, SCALE.length);
        System.arraycopy(SCALE, 0, allNotes, SCALE.length, SCALE.length);

        int totalSamples = (int) (SAMPLE_RATE * durationSec);
        double[] samples = new double[totalSamples];

        double t = 0.0;
        while (t < durationSec) {
            double noteLen = 0.15 + rng.nextDouble() * 0.35; // 0.15 - 0.5
            double freq = allNotes[rng.nextInt(allNotes.length)];
            freq *= 0.98 + rng.nextDouble() * 0.04; // slight bend
            double end = Math.min(t + noteLen, durationSec);
            int n = (int) (SAMPLE_RATE * (end - t));
            for (int i = 0; i < n; i++) {
                int idx = (int) (t * SAMPLE_RATE) + i;
                if (idx < samples.length) {
                    double env = 0.3 * (1 - (double) i / n) + 0.7;
                    double phase = 2 * Math.PI * freq * (t + (double) i / SAMPLE_RATE);
                    samples[idx] += 0.25 * env * Math.sin(phase);
                }
            }
            t = end;
        }

        // Normalize
        double max = Arrays.stream(samples).map(Math::abs).max().orElse(1.0);
        for (int i = 0; i < samples.length; i++) {
            samples[i] = samples[i] / max * 0.85;
        }

        return writeWav(samples);
    }

    private byte[] writeWav(double[] samples) throws IOException {
        int numSamples = samples.length * CHANNELS;
        int dataSize = numSamples * 2; // 16-bit = 2 bytes per sample
        int headerSize = 44;

        ByteArrayOutputStream out = new ByteArrayOutputStream(headerSize + dataSize);

        // WAV header (44 bytes)
        out.write("RIFF".getBytes());
        writeInt(out, 36 + dataSize); // file size - 8
        out.write("WAVE".getBytes());
        out.write("fmt ".getBytes());
        writeInt(out, 16);           // subchunk1 size (PCM)
        writeShort(out, (short) 1);  // audio format (PCM)
        writeShort(out, (short) CHANNELS);
        writeInt(out, SAMPLE_RATE);
        writeInt(out, SAMPLE_RATE * CHANNELS * 2); // byte rate
        writeShort(out, (short) (CHANNELS * 2));   // block align
        writeShort(out, (short) 16);                // bits per sample
        out.write("data".getBytes());
        writeInt(out, dataSize);

        // PCM data: 16-bit stereo (L and R same)
        for (double s : samples) {
            short v = (short) Math.max(-32768, Math.min(32767, (int) (s * 32767)));
            writeShort(out, v);
            writeShort(out, v);
        }

        return out.toByteArray();
    }

    private static void writeInt(ByteArrayOutputStream out, int v) {
        out.write(v & 0xff);
        out.write((v >> 8) & 0xff);
        out.write((v >> 16) & 0xff);
        out.write((v >> 24) & 0xff);
    }

    private static void writeShort(ByteArrayOutputStream out, short v) {
        out.write(v & 0xff);
        out.write((v >> 8) & 0xff);
    }
}
