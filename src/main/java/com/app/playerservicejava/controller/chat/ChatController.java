package com.app.playerservicejava.controller.chat;

import com.app.playerservicejava.dto.ChatRequest;
import com.app.playerservicejava.dto.ChatResponse;
import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.service.PlayerService;
import com.app.playerservicejava.service.chat.ChatClientService;
import io.github.ollama4j.exceptions.OllamaBaseException;
import io.github.ollama4j.models.Model;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.URISyntaxException;
import java.util.List;

@RestController
@RequestMapping(value = "v1/chat", produces = { MediaType.APPLICATION_JSON_VALUE })
public class ChatController {

    private static final Logger LOGGER = LoggerFactory.getLogger(ChatController.class);

    @Autowired
    private ChatClientService chatClientService;

    @Autowired
    private PlayerService playerService;

    @RequestMapping(method = RequestMethod.POST)
    public String chat() throws OllamaBaseException, IOException, InterruptedException {
        return chatClientService.chat();
    }

    @PostMapping("/message")
    public ResponseEntity<ChatResponse> chat(@RequestBody ChatRequest request) {
        try {
            LOGGER.info("Received chat request with message: {}", request.getMessage());
            String response = chatClientService.chat(
                    request.getMessage(),
                    request.getModel()
            );
            return ResponseEntity.ok(new ChatResponse(response, request.getModel()));
        } catch (OllamaBaseException | IOException | InterruptedException e) {
            LOGGER.error("Error processing chat request", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/list-models")
    public ResponseEntity<List<Model>> listModels() throws OllamaBaseException, IOException, URISyntaxException, InterruptedException {
        List<Model> models = chatClientService.listModels();
        return ResponseEntity.ok(models);
    }


    @GetMapping("/summarize-player/{id}")
    public ResponseEntity<String> summarizePlayer(@PathVariable String id) throws OllamaBaseException, IOException, InterruptedException {
        Player player = playerService.getPlayerById(id).get();
        String prompt = buildSummaryPrompt(player);
        String summary = chatClientService.sendPromptToOllama(prompt);
        return ResponseEntity.ok(summary);
    }

    @GetMapping("/test")
    public String test() {
        return "Test endpoint is working!";
    }

    @GetMapping("/test-error")
    public String testError() {
        throw new RuntimeException("This is a test error");
    }

    @GetMapping("/test-ollama-error")
    public String testOllamaError() throws OllamaBaseException {
        // Simulate an OllamaBaseException
        throw new OllamaBaseException("Simulated Ollama service error: Model not found");
    }

    private String buildSummaryPrompt(Player player) {
        return String.format("Summarize this baseball player in brief :\nName: %s %s\nBorn: %s-%s-%s in %s, %s\nWeight: %slbs",
                player.getFirstName(), player.getLastName(),
                player.getBirthYear(), player.getBirthMonth(), player.getBirthDay(),
                player.getBirthCity(), player.getBirthCountry(),
                player.getWeight());
    }
}
