package com.app.playerservicejava.config;

import com.app.playerservicejava.chat.ChatResilienceProperties;
import io.github.ollama4j.OllamaAPI;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ChatClientConfiguration {

    @Bean
    public OllamaAPI ollamaAPI(ChatResilienceProperties properties) {
        String host = properties.getOllamaBaseUrl();
        if (!host.endsWith("/")) {
            host = host + "/";
        }
        OllamaAPI api = new OllamaAPI(host);
        int seconds = Math.max(1, properties.getReadTimeoutMs() / 1000);
        api.setRequestTimeoutSeconds(seconds);
        return api;
    }
}
