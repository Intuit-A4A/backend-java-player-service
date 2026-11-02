package com.app.playerservicejava.service;

import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.model.Players;
import com.app.playerservicejava.repository.PlayerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Proxy;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.tuple;

class PlayerServiceTest {

    private PlayerService playerService;

    private Player player;

    /**
     * Configures the service with deterministic repository results.
     */
    @BeforeEach
    void setUp() {
        player = new Player();
        player.setPlayerId("player-1");
        player.setBirthYear("1919");
        player.setFirstName("Jackie");
        player.setLastName("Robinson");

        playerService = new PlayerService();
        ReflectionTestUtils.setField(
                playerService,
                "playerRepository",
                repositoryReturning(player));
    }

    @Test
    void getPlayersIncludesCompletePlayersForAdminUsers() {
        Players players = playerService.getPlayers(true);

        assertThat(players.getPlayers())
                .extracting(Player::getPlayerId, Player::getBirthYear, Player::getFirstName, Player::getLastName)
                .containsExactly(tuple("player-1", "1919", "Jackie", "Robinson"));
    }

    @Test
    void getPlayersIncludesCompletePlayersWithoutLastNamesForRegularUsers() {
        Players players = playerService.getPlayers(false);

        assertThat(players.getPlayers())
                .extracting(Player::getPlayerId, Player::getBirthYear, Player::getFirstName, Player::getLastName)
                .containsExactly(tuple("player-1", "1919", "Jackie", null));

        // Confirm response filtering does not erase the last name from the repository entity.
        assertThat(player.getLastName()).isEqualTo("Robinson");
    }

    @Test
    void getPlayerByIdIncludesCompletePlayerForAdminUser() {
        Optional<Player> visiblePlayer = playerService.getPlayerById("player-1", true);

        assertThat(visiblePlayer)
                .get()
                .extracting(Player::getPlayerId, Player::getBirthYear, Player::getFirstName, Player::getLastName)
                .containsExactly("player-1", "1919", "Jackie", "Robinson");
    }

    @Test
    void getPlayerByIdIncludesCompletePlayerWithoutLastNameForRegularUser() {
        Optional<Player> visiblePlayer = playerService.getPlayerById("player-1", false);

        assertThat(visiblePlayer)
                .get()
                .extracting(Player::getPlayerId, Player::getBirthYear, Player::getFirstName, Player::getLastName)
                .containsExactly("player-1", "1919", "Jackie", null);

        // Confirm response filtering does not erase the last name from the repository entity.
        assertThat(player.getLastName()).isEqualTo("Robinson");
    }

    /**
     * Creates a repository proxy that supports the reads exercised by the service.
     */
    private PlayerRepository repositoryReturning(Player storedPlayer) {
        return (PlayerRepository) Proxy.newProxyInstance(
                PlayerRepository.class.getClassLoader(),
                new Class<?>[]{PlayerRepository.class},
                (proxy, method, arguments) -> switch (method.getName()) {
                    case "findAll" -> List.of(storedPlayer);
                    case "findById" -> Optional.of(storedPlayer);
                    default -> throw new UnsupportedOperationException(
                            "Unexpected repository method: " + method.getName());
                });
    }
}
