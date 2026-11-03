package com.app.playerservicejava.reliability;

import com.app.playerservicejava.chat.ChatCircuitBreaker;
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
    private final ChatCircuitBreaker circuitBreaker;

    public ReliabilityController(SliTracker sliTracker,
                                 ChatResilienceProperties chat,
                                 ChatCircuitBreaker circuitBreaker) {
        this.sliTracker = sliTracker;
        this.chat = chat;
        this.circuitBreaker = circuitBreaker;
    }

    @GetMapping("/mode")
    public Map<String, Object> mode() {
        Map<String, Object> mode = new LinkedHashMap<>();
        mode.put("stage", chat.getStage());
        mode.put("asyncEnabled", chat.isAsyncEnabled());
        mode.put("poolSize", chat.getPoolSize());
        mode.put("connectTimeoutMs", chat.getConnectTimeoutMs());
        mode.put("readTimeoutMs", chat.getReadTimeoutMs());
        mode.put("retries", chat.getRetries());
        mode.put("retryBudgetMs", chat.getRetryBudgetMs());
        mode.put("backoffInitialMs", chat.getBackoffInitialMs());
        mode.put("backoffMultiplier", chat.getBackoffMultiplier());
        mode.put("circuitBreakerEnabled", chat.isCircuitBreakerEnabled());
        mode.put("circuitState", circuitBreaker.state().name());
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
