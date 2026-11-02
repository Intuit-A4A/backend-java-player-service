package com.app.playerservicejava.chat;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.chat")
public class ChatResilienceProperties {

    private String stage = "baseline";
    private String ollamaBaseUrl = "http://127.0.0.1:11434";
    /** When false, LLM calls run on the Tomcat request thread (stock behavior). */
    private boolean asyncEnabled = false;
    private int poolSize = 8;
    /** 0 = JDK default (no connect timeout). */
    private int connectTimeoutMs = 0;
    private int readTimeoutMs = 120_000;
    /** Extra attempts after the first. 0 = no retry. */
    private int retries = 0;
    /**
     * Wall-clock cap for every attempt and the backoff between them.
     * 0 = no shared budget (each attempt may use the full read timeout).
     */
    private long retryBudgetMs = 0;
    /** First pause after a failed attempt. Later pauses multiply by {@link #backoffMultiplier}. */
    private int backoffInitialMs = 200;
    private int backoffMultiplier = 2;
    private boolean circuitBreakerEnabled = false;
    private int circuitFailureThreshold = 3;
    private long circuitOpenMs = 15_000;

    public String getStage() { return stage; }
    public void setStage(String stage) { this.stage = stage; }
    public String getOllamaBaseUrl() { return ollamaBaseUrl; }
    public void setOllamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; }
    public boolean isAsyncEnabled() { return asyncEnabled; }
    public void setAsyncEnabled(boolean asyncEnabled) { this.asyncEnabled = asyncEnabled; }
    public int getPoolSize() { return poolSize; }
    public void setPoolSize(int poolSize) { this.poolSize = poolSize; }
    public int getConnectTimeoutMs() { return connectTimeoutMs; }
    public void setConnectTimeoutMs(int connectTimeoutMs) { this.connectTimeoutMs = connectTimeoutMs; }
    public int getReadTimeoutMs() { return readTimeoutMs; }
    public void setReadTimeoutMs(int readTimeoutMs) { this.readTimeoutMs = readTimeoutMs; }
    public int getRetries() { return retries; }
    public void setRetries(int retries) { this.retries = retries; }
    public long getRetryBudgetMs() { return retryBudgetMs; }
    public void setRetryBudgetMs(long retryBudgetMs) { this.retryBudgetMs = retryBudgetMs; }
    public int getBackoffInitialMs() { return backoffInitialMs; }
    public void setBackoffInitialMs(int backoffInitialMs) { this.backoffInitialMs = backoffInitialMs; }
    public int getBackoffMultiplier() { return backoffMultiplier; }
    public void setBackoffMultiplier(int backoffMultiplier) { this.backoffMultiplier = backoffMultiplier; }
    public boolean isCircuitBreakerEnabled() { return circuitBreakerEnabled; }
    public void setCircuitBreakerEnabled(boolean circuitBreakerEnabled) { this.circuitBreakerEnabled = circuitBreakerEnabled; }
    public int getCircuitFailureThreshold() { return circuitFailureThreshold; }
    public void setCircuitFailureThreshold(int circuitFailureThreshold) { this.circuitFailureThreshold = circuitFailureThreshold; }
    public long getCircuitOpenMs() { return circuitOpenMs; }
    public void setCircuitOpenMs(long circuitOpenMs) { this.circuitOpenMs = circuitOpenMs; }
}
