package com.app.playerservicejava.controller.chat;

import com.app.playerservicejava.service.chat.ChatClientService;
import io.github.ollama4j.exceptions.OllamaException;
import io.github.ollama4j.models.response.Model;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;

import java.util.List;

@Controller
@RequestMapping(value = "v1/chat", produces = { MediaType.APPLICATION_JSON_VALUE })
public class ChatController {

    private static final Logger LOGGER = LoggerFactory.getLogger(ChatController.class);

    @Autowired
    private ChatClientService chatClientService;

    @PostMapping
    public @ResponseBody String chat() throws OllamaException {
        return chatClientService.chat();
    }

    @GetMapping("/list-models")
    public ResponseEntity<List<Model>> listModels() throws OllamaException {
        List<Model> models = chatClientService.listModels();
        return ResponseEntity.ok(models);
    }
}
