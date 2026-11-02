package com.app.playerservicejava.config;

import com.app.playerservicejava.chat.ChatResilienceProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(ChatResilienceProperties.class)
public class ReliabilityConfiguration {
}
