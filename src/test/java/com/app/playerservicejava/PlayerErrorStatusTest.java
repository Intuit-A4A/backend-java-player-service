package com.app.playerservicejava;

import com.app.playerservicejava.controller.PlayerController;
import com.app.playerservicejava.controller.PlayerExceptionHandler;
import com.app.playerservicejava.service.PlayerService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PlayerErrorStatusTest {

    private PlayerService playerService;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        playerService = mock(PlayerService.class);
        PlayerController controller = new PlayerController();
        ReflectionTestUtils.setField(controller, "playerService", playerService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new PlayerExceptionHandler())
                .build();
    }

    @Test
    void missingPlayerIs404() throws Exception {
        when(playerService.getPlayerById("missing")).thenReturn(java.util.Optional.empty());
        mockMvc.perform(get("/v1/players/missing")).andExpect(status().isNotFound());
    }

    @Test
    void databaseFailureIs500() throws Exception {
        when(playerService.getPlayerById("aardsda01"))
                .thenThrow(new DataAccessResourceFailureException("db down"));
        mockMvc.perform(get("/v1/players/aardsda01")).andExpect(status().isInternalServerError());
    }
}
