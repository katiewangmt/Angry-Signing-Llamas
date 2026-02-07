package com.asl.freestyle;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        ensureGeneratedDir();
        SpringApplication.run(Application.class, args);
    }

    private static void ensureGeneratedDir() {
        try {
            Files.createDirectories(Path.of("generated"));
        } catch (IOException e) {
            // ignore
        }
    }

    @Bean
    public MusicGenerator musicGenerator() {
        return new MusicGenerator();
    }
}
