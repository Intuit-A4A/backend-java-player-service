package com.app.playerservicejava.controller.chat;

import com.app.playerservicejava.chat.ChatResilienceProperties;
import com.app.playerservicejava.service.chat.ChatClientService;
import io.github.ollama4j.exceptions.OllamaBaseException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.io.IOException;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.URISyntaxException;
import java.net.http.HttpTimeoutException;
import java.util.List;
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
        return dispatch(() -> ResponseEntity.ok(chatClientService.chat()));
    }

    @GetMapping("/list-models")
    public Object listModels() {
        return dispatch(() -> ResponseEntity.ok((Object) chatClientService.listModels()));
    }

    private Object dispatch(OllamaCall call) {
        if (!properties.isAsyncEnabled()) {
            return invoke(call);
        }
        Callable<ResponseEntity<?>> task = () -> invoke(call);
        return task;
    }

    private ResponseEntity<?> invoke(OllamaCall call) {
        try {
            return call.run();
        } catch (ConnectException exc) {
            return unavailable("Ollama is unavailable", exc);
        } catch (RejectedExecutionException exc) {
            return unavailable("Chat worker pool is full", exc);
        } catch (OllamaBaseException | IOException | URISyntaxException | InterruptedException exc) {
            if (isTimeout(exc)) {
                return unavailable("Ollama call timed out", exc);
            }
            return unavailable("Ollama call failed", exc);
        }
    }

    private static boolean isTimeout(Throwable exc) {
        for (Throwable current = exc; current != null; current = current.getCause()) {
            if (current instanceof SocketTimeoutException
                    || current instanceof HttpTimeoutException
                    || current instanceof InterruptedException) {
                return true;
            }
            String message = current.getMessage();
            if (message != null && message.toLowerCase().contains("timeout")) {
                return true;
            }
        }
        return false;
    }

    private ResponseEntity<Map<String, String>> unavailable(String error, Exception exc) {
        LOGGER.error("message={}; exception={}", error, exc.toString());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", error, "detail", String.valueOf(exc.getMessage())));
    }

    @FunctionalInterface
    private interface OllamaCall {
        ResponseEntity<?> run() throws OllamaBaseException, IOException, URISyntaxException, InterruptedException;
    }
}
