package com.app.playerservicejava;

import com.app.playerservicejava.controller.PlayerController;
import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.repository.PlayerRepository;
import com.app.playerservicejava.service.PlayerService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Availability for the list is HTTP 200 within a deadline. Each row costs a fixed read time.
 * The full table misses that deadline. One page of the same rows returns 200 inside it.
 */
class PlayerListPaginationTest {

    private static final int ALL_ROWS = 20;
    private static final long PER_ROW_MS = 30;
    private static final long DEADLINE_MS = 200;
    private static final ObjectMapper JSON = new ObjectMapper();

    @Test
    void fullListMissesDeadlineWhilePageSucceeds() throws Exception {
        PlayerRepository repository = mock(PlayerRepository.class);
        when(repository.findAll()).thenAnswer(invocation -> readRows(ALL_ROWS));
        when(repository.findAll(any(Pageable.class))).thenAnswer(invocation -> {
            Pageable pageable = invocation.getArgument(0);
            List<Player> page = readRows(pageable.getPageSize());
            return new PageImpl<>(page, pageable, ALL_ROWS);
        });

        PlayerController controller = new PlayerController();
        ReflectionTestUtils.setField(controller, "playerService",
                new PlayerService(repository));
        MockMvc mockMvc = MockMvcBuilders.standaloneSetup(controller).build();

        ExecutorService calls = Executors.newCachedThreadPool(runnable -> {
            Thread thread = new Thread(runnable);
            thread.setDaemon(true);
            return thread;
        });
        try {
            Future<MvcResult> fullList = calls.submit(() -> mockMvc.perform(get("/v1/players")).andReturn());
            assertThrows(TimeoutException.class, () -> fullList.get(DEADLINE_MS, TimeUnit.MILLISECONDS));
            fullList.cancel(true);

            long started = System.nanoTime();
            Future<MvcResult> page = calls.submit(() ->
                    mockMvc.perform(get("/v1/players").param("limit", "2")).andReturn());
            MvcResult result = page.get(DEADLINE_MS, TimeUnit.MILLISECONDS);
            long elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

            assertEquals(200, result.getResponse().getStatus());
            assertTrue(elapsedMs < DEADLINE_MS, "page took " + elapsedMs + "ms");
            JsonNode players = JSON.readTree(result.getResponse().getContentAsString()).get("players");
            assertEquals(2, players.size());
            assertEquals("row-0", players.get(0).get("playerId").asText());
            assertEquals("row-1", players.get(1).get("playerId").asText());
        } finally {
            calls.shutdownNow();
        }
    }

    private static List<Player> readRows(int count) {
        List<Player> players = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            try {
                Thread.sleep(PER_ROW_MS);
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("row read interrupted", interrupted);
            }
            Player player = new Player();
            player.setPlayerId("row-" + i);
            players.add(player);
        }
        return players;
    }
}
