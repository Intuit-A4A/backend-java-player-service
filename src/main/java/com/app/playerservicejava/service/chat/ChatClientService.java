package com.app.playerservicejava.service.chat;

import com.app.playerservicejava.chat.OllamaTransport;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

@Service
public class ChatClientService {

    private final OllamaTransport ollamaTransport;
    private final ObjectMapper objectMapper;

    public ChatClientService(OllamaTransport ollamaTransport, ObjectMapper objectMapper) {
        this.ollamaTransport = ollamaTransport;
        this.objectMapper = objectMapper;
    }

    public String listModels() {
        return ollamaTransport.get("/api/tags");
    }

    public String chat() {
        String raw = ollamaTransport.post("/api/generate",
                "{\"model\":\"tinyllama\",\"prompt\":\"Recite a haiku about recursion.\",\"stream\":false}");
        try {
            JsonNode node = objectMapper.readTree(raw);
            JsonNode text = node.get("response");
            return text == null ? raw : text.asText();
        } catch (Exception exc) {
            return raw;
        }
    }
}
