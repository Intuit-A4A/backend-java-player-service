package com.app.playerservicejava.reliability;

import com.app.playerservicejava.chat.ChatResilienceProperties;
import org.springframework.boot.actuate.info.Info;
import org.springframework.boot.actuate.info.InfoContributor;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class ServiceInfoContributor implements InfoContributor {

    private final ChatResilienceProperties chat;

    public ServiceInfoContributor(ChatResilienceProperties chat) {
        this.chat = chat;
    }

    @Override
    public void contribute(Info.Builder builder) {
        Map<String, Object> service = new LinkedHashMap<>();
        service.put("name", "player-service-java");
        service.put("stage", chat.getStage());
        service.put("availability", "player HTTP success only; chat responses are excluded");
        service.put("liveness", "process is running");
        service.put("readiness", "database accepts connections; Ollama is not included");
        builder.withDetail("service", service);
    }
}
