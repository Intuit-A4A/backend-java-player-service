package com.app.playerservicejava.chat;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.chat")
public class ChatResilienceProperties {

    private String stage = "baseline";
    private String ollamaBaseUrl = "http://127.0.0.1:11434";
    /** When false, LLM calls run on the Tomcat request thread (stock behavior). */
    private boolean asyncEnabled = false;
    private int poolSize = 8;
    /** ollama4j request timeout (read); baseline 120s, timeouts profile 2s. */
    private int readTimeoutMs = 120_000;

    public String getStage() { return stage; }
    public void setStage(String stage) { this.stage = stage; }
    public String getOllamaBaseUrl() { return ollamaBaseUrl; }
    public void setOllamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; }
    public boolean isAsyncEnabled() { return asyncEnabled; }
    public void setAsyncEnabled(boolean asyncEnabled) { this.asyncEnabled = asyncEnabled; }
    public int getPoolSize() { return poolSize; }
    public void setPoolSize(int poolSize) { this.poolSize = poolSize; }
    public int getReadTimeoutMs() { return readTimeoutMs; }
    public void setReadTimeoutMs(int readTimeoutMs) { this.readTimeoutMs = readTimeoutMs; }
}
