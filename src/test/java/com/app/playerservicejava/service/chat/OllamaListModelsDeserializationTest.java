package com.app.playerservicejava.service.chat;

import io.github.ollama4j.models.response.ListModelsResponse;
import io.github.ollama4j.utils.Utils;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class OllamaListModelsDeserializationTest {

    @Test
    void deserializesModelsWithCapabilitiesField() throws Exception {
        String json = """
                {
                  "models": [
                    {
                      "name": "tinyllama:latest",
                      "model": "tinyllama:latest",
                      "modified_at": "2026-03-19T12:00:00Z",
                      "size": 637700138,
                      "digest": "abc123",
                      "details": {
                        "parent_model": "",
                        "format": "gguf",
                        "family": "llama",
                        "families": ["llama"],
                        "parameter_size": "1B",
                        "quantization_level": "Q4_0"
                      },
                      "capabilities": ["completion", "tools"]
                    }
                  ]
                }
                """;

        ListModelsResponse response = Utils.getObjectMapper().readValue(json, ListModelsResponse.class);

        assertNotNull(response.getModels());
        assertEquals(1, response.getModels().size());
        assertEquals("tinyllama:latest", response.getModels().get(0).getName());
    }
}
