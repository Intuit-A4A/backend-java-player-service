package com.app.playerservicejava.reliability;

import com.app.playerservicejava.chat.ChatResilienceProperties;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping(value = "v1/reliability", produces = MediaType.APPLICATION_JSON_VALUE)
public class ReliabilityController {

    private final SliTracker sliTracker;
    private final ChatResilienceProperties chat;

    public ReliabilityController(SliTracker sliTracker, ChatResilienceProperties chat) {
        this.sliTracker = sliTracker;
        this.chat = chat;
    }

    @GetMapping("/mode")
    public Map<String, Object> mode() {
        Map<String, Object> mode = new LinkedHashMap<>();
        mode.put("stage", chat.getStage());
        mode.put("asyncEnabled", chat.isAsyncEnabled());
        mode.put("poolSize", chat.getPoolSize());
        mode.put("readTimeoutMs", chat.getReadTimeoutMs());
        mode.put("ollamaBaseUrl", chat.getOllamaBaseUrl());
        return mode;
    }

    @GetMapping("/sli")
    public Map<String, Object> sli() {
        return sliTracker.snapshot();
    }

    @PostMapping("/sli/reset")
    public ResponseEntity<Map<String, Object>> reset() {
        sliTracker.reset();
        return ResponseEntity.ok(sliTracker.snapshot());
    }
}
