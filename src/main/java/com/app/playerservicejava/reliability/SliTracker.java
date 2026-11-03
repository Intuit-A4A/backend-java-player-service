package com.app.playerservicejava.reliability;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

@Component
public class SliTracker {

    private final LongAdder playersTotal = new LongAdder();
    private final LongAdder playersSuccess = new LongAdder();
    private final LongAdder playersErrors = new LongAdder();
    private final LongAdder chatTotal = new LongAdder();
    private final LongAdder chatSuccess = new LongAdder();
    private final LongAdder chatErrors = new LongAdder();
    private final AtomicLong windowStartedAtMs = new AtomicLong(System.currentTimeMillis());

    public void recordPlayers(boolean success, long latencyMs) {
        playersTotal.increment();
        if (success) {
            playersSuccess.increment();
        } else {
            playersErrors.increment();
        }
    }

    public void recordChat(boolean success, long latencyMs) {
        chatTotal.increment();
        if (success) {
            chatSuccess.increment();
        } else {
            chatErrors.increment();
        }
    }

    public synchronized void reset() {
        playersTotal.reset();
        playersSuccess.reset();
        playersErrors.reset();
        chatTotal.reset();
        chatSuccess.reset();
        chatErrors.reset();
        windowStartedAtMs.set(System.currentTimeMillis());
    }

    public Map<String, Object> snapshot() {
        long total = playersTotal.sum();
        long success = playersSuccess.sum();
        long errors = playersErrors.sum();
        double availability = total == 0 ? 1.0 : (double) success / (double) total;

        Map<String, Object> players = new LinkedHashMap<>();
        players.put("total", total);
        players.put("success", success);
        players.put("errors", errors);
        players.put("availability", round5(availability));

        Map<String, Object> chat = new LinkedHashMap<>();
        chat.put("total", chatTotal.sum());
        chat.put("completedBelow500", chatSuccess.sum());
        chat.put("errors", chatErrors.sum());
        chat.put("includedInAvailability", false);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("windowStartedAt", Instant.ofEpochMilli(windowStartedAtMs.get()).toString());
        out.put("availability", players.get("availability"));
        out.put("players", players);
        out.put("chat", chat);
        out.put("formula", "availability = player successes / player requests that reached the app; success = player HTTP < 500. Chat is excluded.");
        return out;
    }

    private static double round5(double availability) {
        return Math.round(availability * 100000.0) / 100000.0;
    }
}
