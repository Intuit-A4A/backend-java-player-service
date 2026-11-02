package com.app.playerservicejava.controller.chat;

import com.app.playerservicejava.chat.ChatCircuitBreaker;
import com.app.playerservicejava.chat.ChatResilienceProperties;
import com.app.playerservicejava.chat.OllamaTransport;
import com.app.playerservicejava.service.chat.ChatClientService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.RejectedExecutionException;

@Controller
@RequestMapping(value = "v1/chat", produces = { MediaType.APPLICATION_JSON_VALUE })
public class ChatController {

    private static final Logger LOGGER = LoggerFactory.getLogger(ChatController.class);

    private final ChatClientService chatClientService;
    private final ChatResilienceProperties properties;

    public ChatController(ChatClientService chatClientService, ChatResilienceProperties properties) {
        this.chatClientService = chatClientService;
        this.properties = properties;
    }

    @PostMapping
    public Object chat() {
        return dispatch(chatClientService::chat);
    }

    @GetMapping("/list-models")
    public Object listModels() {
        return dispatch(chatClientService::listModels);
    }

    private Object dispatch(java.util.function.Supplier<String> call) {
        if (!properties.isAsyncEnabled()) {
            return invoke(call);
        }
        Callable<ResponseEntity<?>> task = () -> invoke(call);
        return task;
    }

    private ResponseEntity<?> invoke(java.util.function.Supplier<String> call) {
        try {
            return ResponseEntity.ok(call.get());
        } catch (ChatCircuitBreaker.CircuitOpenException exc) {
            return unavailable("Ollama circuit is open", exc);
        } catch (RejectedExecutionException exc) {
            return unavailable("Chat worker pool is full", exc);
        } catch (OllamaTransport.OllamaCallException exc) {
            return unavailable("Ollama call failed", exc);
        }
    }

    private ResponseEntity<Map<String, String>> unavailable(String error, Exception exc) {
        LOGGER.error("message={}; exception={}", error, exc.toString());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", error, "detail", String.valueOf(exc.getMessage())));
    }
}
