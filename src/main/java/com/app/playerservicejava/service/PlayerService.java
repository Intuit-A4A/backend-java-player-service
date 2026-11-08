package com.app.playerservicejava.service;

import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.model.Players;
import com.app.playerservicejava.repository.PlayerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class PlayerService {

    public static final int MAX_PAGE_SIZE = 100;

    private static final Logger LOGGER = LoggerFactory.getLogger(PlayerService.class);

    private final PlayerRepository playerRepository;

    public PlayerService(PlayerRepository playerRepository) {
        this.playerRepository = playerRepository;
    }

    public Players getPlayers(Pageable pageable) {
        Page<Player> page = playerRepository.findAll(pageable);
        Players players = new Players();
        players.setPlayers(page.getContent());
        players.setPage(page.getNumber());
        players.setSize(page.getSize());
        players.setTotalElements(page.getTotalElements());
        players.setTotalPages(page.getTotalPages());
        return players;
    }

    public Optional<Player> getPlayerById(String playerId) {
        // Database failures propagate as DataAccessException and are mapped to HTTP 500.
        // Returning Optional.empty() would become 404 and hide the outage.
        // The 0–2s sleep is the demo latency and runs once, after a successful read.
        Optional<Player> player = playerRepository.findById(playerId);
        try {
            /* simulated network delay — intentional */
            Thread.sleep((long) (Math.random() * 2000));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            LOGGER.error("message=Interrupted while simulating latency; playerId={}", playerId);
            throw new IllegalStateException("Interrupted while simulating player latency", e);
        }
        return player;
    }
}
