package com.app.playerservicejava.chat;

import org.springframework.stereotype.Component;

import java.util.function.Supplier;

@Component
public class ChatCircuitBreaker {

    public enum State { CLOSED, OPEN, HALF_OPEN }

    private final ChatResilienceProperties properties;
    private State state = State.CLOSED;
    private int consecutiveFailures;
    private long openedAtMs;

    public ChatCircuitBreaker(ChatResilienceProperties properties) {
        this.properties = properties;
    }

    public <T> T call(Supplier<T> action) {
        if (!properties.isCircuitBreakerEnabled()) {
            return action.get();
        }
        if (!allowAttempt()) {
            throw new CircuitOpenException("no call was sent to Ollama");
        }
        try {
            T value = action.get();
            onSuccess();
            return value;
        } catch (RuntimeException exc) {
            onFailure();
            throw exc;
        }
    }

    public synchronized State state() {
        transitionIfCooldownElapsed();
        return state;
    }

    private synchronized boolean allowAttempt() {
        transitionIfCooldownElapsed();
        if (state == State.OPEN) {
            return false;
        }
        if (state == State.HALF_OPEN) {
            state = State.OPEN; // one trial in flight; failure keeps it open
            return true;
        }
        return true;
    }

    private synchronized void onSuccess() {
        consecutiveFailures = 0;
        state = State.CLOSED;
    }

    private synchronized void onFailure() {
        consecutiveFailures++;
        if (consecutiveFailures >= properties.getCircuitFailureThreshold()) {
            state = State.OPEN;
            openedAtMs = System.currentTimeMillis();
        }
    }

    private void transitionIfCooldownElapsed() {
        if (state == State.OPEN && System.currentTimeMillis() - openedAtMs >= properties.getCircuitOpenMs()) {
            state = State.HALF_OPEN;
        }
    }

    public static class CircuitOpenException extends RuntimeException {
        public CircuitOpenException(String message) {
            super(message);
        }
    }
}
