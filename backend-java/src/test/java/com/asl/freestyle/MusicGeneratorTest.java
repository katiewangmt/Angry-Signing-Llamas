package com.asl.freestyle;

import org.junit.jupiter.api.Test;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;

class MusicGeneratorTest {

    @Test
    void generateRandomMusic_returnsNonEmptyWav() throws IOException {
        MusicGenerator gen = new MusicGenerator();
        byte[] wav = gen.generateRandomMusic(1.0); // 1 second
        assertNotNull(wav);
        assertTrue(wav.length > 1000, "WAV should be at least a few KB");
    }

    @Test
    void generateRandomMusic_hasValidWavHeader() throws IOException {
        MusicGenerator gen = new MusicGenerator();
        byte[] wav = gen.generateRandomMusic(0.5);
        // WAV files start with "RIFF"
        assertTrue(wav.length >= 44, "WAV has at least 44-byte header");
        assertEquals('R', wav[0]);
        assertEquals('I', wav[1]);
        assertEquals('F', wav[2]);
        assertEquals('F', wav[3]);
    }

    @Test
    void generateRandomMusic_differentCallsProduceDifferentBytes() throws IOException {
        MusicGenerator gen = new MusicGenerator();
        byte[] a = gen.generateRandomMusic(0.3);
        byte[] b = gen.generateRandomMusic(0.3);
        assertNotNull(a);
        assertNotNull(b);
        assertFalse(java.util.Arrays.equals(a, b), "Random music should differ between calls");
    }
}
