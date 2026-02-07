package com.asl.freestyle;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class MusicControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void randomMusic_returns200AndWav() throws Exception {
        mockMvc.perform(get("/api/random-music"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.parseMediaType("audio/wav")));
    }

    @Test
    void randomMusic_returnsNonEmptyBody() throws Exception {
        byte[] body = mockMvc.perform(get("/api/random-music"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsByteArray();
        assertTrue(body != null && body.length > 1000);
    }
}
