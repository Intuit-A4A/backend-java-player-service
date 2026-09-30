package com.app.playerservicejava.service.chat;

import io.github.ollama4j.Ollama;
import io.github.ollama4j.exceptions.OllamaException;
import io.github.ollama4j.models.generate.OllamaGenerateRequest;
import io.github.ollama4j.models.request.ThinkMode;
import io.github.ollama4j.models.response.Model;
import io.github.ollama4j.models.response.OllamaResult;
import io.github.ollama4j.utils.OptionsBuilder;
import io.github.ollama4j.utils.PromptBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ChatClientService {
    private static final Logger LOGGER = LoggerFactory.getLogger(ChatClientService.class);

    private static final String MODEL = "tinyllama";

    @Autowired
    private Ollama ollama;

    public List<Model> listModels() throws OllamaException {
        List<Model> models = ollama.listModels();
        return models;
    }

    public String chat() throws OllamaException {
        // https://ollama4j.github.io/ollama4j/intro
        PromptBuilder promptBuilder =
                new PromptBuilder()
                        .addLine("Recite a haiku about recursion.");

        OllamaGenerateRequest request = OllamaGenerateRequest.builder()
                .withModel(MODEL)
                .withPrompt(promptBuilder.build())
                .withRaw(false)
                .withThink(ThinkMode.DISABLED)
                .withOptions(new OptionsBuilder().build())
                .build();

        // No stream handlers: wait for the full (non-streamed) response
        OllamaResult response = ollama.generate(request, null);
        return response.getResponse();
    }

}
