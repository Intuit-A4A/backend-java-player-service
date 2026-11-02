package com.app.playerservicejava.chat;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * Direct Ollama HTTP calls so connect timeout and read timeout are separate.
 * ollama4j 1.0.x only exposes one request timeout and builds HttpClient.newHttpClient()
 * (no connect timeout).
 *
 * <p>When {@code retry-budget-ms} is set, every attempt and the backoff between
 * attempts must finish inside that wall clock. An attempt is not started when
 * the time left is shorter than the connect timeout.
 */
@Component
public class OllamaTransport {

    private final ChatResilienceProperties properties;
    private final ChatCircuitBreaker circuitBreaker;
    private final HttpClient httpClient;

    public OllamaTransport(ChatResilienceProperties properties, ChatCircuitBreaker circuitBreaker) {
        this.properties = properties;
        this.circuitBreaker = circuitBreaker;
        HttpClient.Builder builder = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1);
        if (properties.getConnectTimeoutMs() > 0) {
            builder.connectTimeout(Duration.ofMillis(properties.getConnectTimeoutMs()));
        }
        this.httpClient = builder.build();
    }

    public String get(String path) {
        return circuitBreaker.call(() -> withRetry(readMs -> send("GET", path, null, readMs)));
    }

    public String post(String path, String json) {
        return circuitBreaker.call(() -> withRetry(readMs -> send("POST", path, json, readMs)));
    }

    private String withRetry(Attempt action) {
        int attempts = Math.max(1, properties.getRetries() + 1);
        long budgetMs = properties.getRetryBudgetMs();
        long deadlineNs = budgetMs > 0
                ? System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(budgetMs)
                : Long.MAX_VALUE;
        long backoffMs = Math.max(0, properties.getBackoffInitialMs());
        int multiplier = Math.max(1, properties.getBackoffMultiplier());
        int connectMs = Math.max(0, properties.getConnectTimeoutMs());
        RuntimeException last = null;

        for (int i = 1; i <= attempts; i++) {
            long remainingMs = millisUntil(deadlineNs);
            if (!attemptFits(budgetMs, remainingMs, connectMs)) {
                break;
            }
            long readMs = properties.getReadTimeoutMs();
            if (budgetMs > 0) {
                readMs = Math.min(readMs, remainingMs);
            }
            try {
                return action.run(readMs);
            } catch (RuntimeException exc) {
                last = exc;
                if (i == attempts || !backoffFits(budgetMs, millisUntil(deadlineNs), backoffMs, connectMs)) {
                    break;
                }
                sleepBackoff(backoffMs);
                backoffMs = Math.min(backoffMs * multiplier, 10_000L);
            }
        }
        if (last != null) {
            throw last;
        }
        throw new OllamaCallException("Ollama retry budget exhausted");
    }

    /** A black-hole connect waits the full connect timeout, so don't start one that would pass the budget. */
    private static boolean attemptFits(long budgetMs, long remainingMs, int connectMs) {
        if (budgetMs <= 0) {
            return true;
        }
        if (remainingMs <= 0) {
            return false;
        }
        return connectMs <= 0 || remainingMs >= connectMs;
    }

    private static boolean backoffFits(long budgetMs, long remainingMs, long backoffMs, int connectMs) {
        if (budgetMs <= 0) {
            return true;
        }
        long afterPause = remainingMs - backoffMs;
        if (afterPause <= 0) {
            return false;
        }
        return connectMs <= 0 || afterPause >= connectMs;
    }

    private String send(String method, String path, String json, long readTimeoutMs) {
        try {
            HttpRequest.Builder request = HttpRequest.newBuilder()
                    .uri(URI.create(trimSlash(properties.getOllamaBaseUrl()) + path))
                    .timeout(Duration.ofMillis(Math.max(1, readTimeoutMs)));
            if ("POST".equals(method)) {
                request.header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(json == null ? "{}" : json));
            } else {
                request.GET();
            }
            HttpResponse<String> response = httpClient.send(request.build(), HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 500) {
                throw new OllamaCallException("Ollama HTTP " + response.statusCode());
            }
            return response.body();
        } catch (HttpConnectTimeoutException exc) {
            throw new OllamaCallException(
                    "Ollama connect timed out after " + properties.getConnectTimeoutMs() + "ms", exc);
        } catch (HttpTimeoutException exc) {
            throw new OllamaCallException("Ollama read timed out after " + readTimeoutMs + "ms", exc);
        } catch (IOException exc) {
            throw new OllamaCallException("Ollama I/O failed: " + exc.getClass().getSimpleName(), exc);
        } catch (InterruptedException exc) {
            Thread.currentThread().interrupt();
            throw new OllamaCallException("Ollama call interrupted", exc);
        }
    }

    private static void sleepBackoff(long backoffMs) {
        try {
            Thread.sleep(backoffMs);
        } catch (InterruptedException exc) {
            Thread.currentThread().interrupt();
            throw new OllamaCallException("retry interrupted", exc);
        }
    }

    private static long millisUntil(long deadlineNs) {
        if (deadlineNs == Long.MAX_VALUE) {
            return Long.MAX_VALUE;
        }
        long nanos = deadlineNs - System.nanoTime();
        return nanos <= 0 ? 0 : TimeUnit.NANOSECONDS.toMillis(nanos);
    }

    private static String trimSlash(String base) {
        return base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
    }

    @FunctionalInterface
    private interface Attempt {
        String run(long readTimeoutMs);
    }

    public static class OllamaCallException extends RuntimeException {
        public OllamaCallException(String message) { super(message); }
        public OllamaCallException(String message, Throwable cause) { super(message, cause); }
    }
}
