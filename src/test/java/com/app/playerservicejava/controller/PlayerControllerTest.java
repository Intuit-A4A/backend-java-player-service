package com.app.playerservicejava.controller;

import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.model.Players;
import com.app.playerservicejava.service.PlayerService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PlayerControllerTest {

    private MockMvc mockMvc;
    private StubPlayerService playerService;

    /**
     * Configures the controller with deterministic player data.
     */
    @BeforeEach
    void setUp() {
        playerService = new StubPlayerService();
        PlayerController playerController = new PlayerController();
        ReflectionTestUtils.setField(playerController, "playerService", playerService);
        mockMvc = MockMvcBuilders.standaloneSetup(playerController).build();
    }

    @Test
    void getPlayersReturnsEntirePlayersWhenIsAdminIsTrue() throws Exception {
        mockMvc.perform(get("/v1/players").param("isAdmin", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.players[0].playerId").value("player-1"))
                .andExpect(jsonPath("$.players[0].birthYear").value("1919"))
                .andExpect(jsonPath("$.players[0].firstName").value("Jackie"))
                .andExpect(jsonPath("$.players[0].lastName").value("Robinson"));

        assertTrue(playerService.lastIsAdmin);
    }

    @Test
    void getPlayersReturnsEntirePlayersWithoutLastNamesWhenIsAdminIsFalse() throws Exception {
        mockMvc.perform(get("/v1/players").param("isAdmin", "false"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.players[0].playerId").value("player-1"))
                .andExpect(jsonPath("$.players[0].birthYear").value("1919"))
                .andExpect(jsonPath("$.players[0].firstName").value("Jackie"))
                .andExpect(jsonPath("$.players[0].lastName").doesNotExist());

        assertFalse(playerService.lastIsAdmin);
    }

    @Test
    void getPlayerByIdReturnsEntirePlayerWhenIsAdminIsTrue() throws Exception {
        mockMvc.perform(get("/v1/players/player-1").param("isAdmin", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.playerId").value("player-1"))
                .andExpect(jsonPath("$.birthYear").value("1919"))
                .andExpect(jsonPath("$.firstName").value("Jackie"))
                .andExpect(jsonPath("$.lastName").value("Robinson"));

        assertEquals("player-1", playerService.lastPlayerId);
        assertTrue(playerService.lastIsAdmin);
    }

    @Test
    void getPlayerByIdReturnsEntirePlayerWithoutLastNameWhenIsAdminIsFalse() throws Exception {
        mockMvc.perform(get("/v1/players/player-1").param("isAdmin", "false"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.playerId").value("player-1"))
                .andExpect(jsonPath("$.birthYear").value("1919"))
                .andExpect(jsonPath("$.firstName").value("Jackie"))
                .andExpect(jsonPath("$.lastName").doesNotExist());

        assertEquals("player-1", playerService.lastPlayerId);
        assertFalse(playerService.lastIsAdmin);
    }

    /**
     * Creates a response containing one complete player for controller serialization tests.
     */
    private static Players playersWithDetails(String firstName, String lastName) {
        Players players = new Players();
        players.getPlayers().add(playerWithDetails(firstName, lastName));
        return players;
    }

    /**
     * Creates a stored player containing identifying, biographical, and name fields.
     */
    private static Player playerWithDetails(String firstName, String lastName) {
        Player player = new Player();
        player.setPlayerId("player-1");
        player.setBirthYear("1919");
        player.setFirstName(firstName);
        player.setLastName(lastName);
        return player;
    }

    /**
     * Supplies deterministic role-aware player responses.
     */
    private static class StubPlayerService extends PlayerService {
        private boolean lastIsAdmin;
        private String lastPlayerId;

        @Override
        public Players getPlayers(boolean isAdmin) {
            lastIsAdmin = isAdmin;
            return playersWithDetails("Jackie", isAdmin ? "Robinson" : null);
        }

        @Override
        public Optional<Player> getPlayerById(String playerId, boolean isAdmin) {
            lastPlayerId = playerId;
            lastIsAdmin = isAdmin;
            return Optional.of(playerWithDetails("Jackie", isAdmin ? "Robinson" : null));
        }
    }
}
