package com.asl.freestyle;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@RestController
public class MusicController {

    private final MusicGenerator musicGenerator;
    private final Path generatedDir;

    public MusicController(MusicGenerator musicGenerator) {
        this.musicGenerator = musicGenerator;
        this.generatedDir = Path.of("generated");
    }

    @GetMapping("/api/random-music")
    public ResponseEntity<byte[]> randomMusic() throws IOException {
        byte[] wavBytes = musicGenerator.generateRandomMusic(20.0);

        Files.createDirectories(generatedDir);
        String name = "random_" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")) + ".wav";
        Path file = generatedDir.resolve(name);
        Files.write(file, wavBytes);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("audio/wav"));
        headers.setContentDispositionFormData("inline", "random.wav");
        return ResponseEntity.ok().headers(headers).body(wavBytes);
    }
}
