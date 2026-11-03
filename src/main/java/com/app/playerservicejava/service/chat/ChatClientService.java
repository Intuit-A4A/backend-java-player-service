package com.app.playerservicejava.service.chat;

import io.github.ollama4j.OllamaAPI;
import io.github.ollama4j.exceptions.OllamaBaseException;
import io.github.ollama4j.models.response.Model;
import io.github.ollama4j.models.response.OllamaResult;
import io.github.ollama4j.utils.Options;
import io.github.ollama4j.types.OllamaModelType;
import io.github.ollama4j.utils.OptionsBuilder;
import io.github.ollama4j.utils.PromptBuilder;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URISyntaxException;
import java.util.List;

@Service
public class ChatClientService {

    private final OllamaAPI ollamaAPI;

    public ChatClientService(OllamaAPI ollamaAPI) {
        this.ollamaAPI = ollamaAPI;
    }

    public List<Model> listModels() throws OllamaBaseException, IOException, URISyntaxException, InterruptedException {
        return ollamaAPI.listModels();
    }

    public String chat() throws OllamaBaseException, IOException, InterruptedException {
        String model = OllamaModelType.TINYLLAMA;
        PromptBuilder promptBuilder = new PromptBuilder().addLine("Recite a haiku about recursion.");
        Options options = new OptionsBuilder().build();
        OllamaResult response = ollamaAPI.generate(model, promptBuilder.build(), false, options);
        return response.getResponse();
    }
}
