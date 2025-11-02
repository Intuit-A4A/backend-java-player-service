package com.app.playerservicejava.service;

import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.model.Players;
import com.app.playerservicejava.repository.PlayerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.JpaSort;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class PlayerService {
    private static final Logger LOGGER = LoggerFactory.getLogger(PlayerService.class);

    @Autowired
    private PlayerRepository playerRepository;

    public Players getPlayers() {
        Players players = new Players();
        playerRepository.findAll()
                .forEach(players.getPlayers()::add);
        return players;
    }

    public Optional<Player> getPlayerById(String playerId) {
        Optional<Player> player = null;

        /* simulated network delay */
        try {
            player = playerRepository.findById(playerId);
            Thread.sleep((long)(Math.random() * 2000));
        } catch (Exception e) {
            LOGGER.error("message=Exception in getPlayerById; exception={}", e.toString());
            return Optional.empty();
        }
        return player;
    }

    public Page<Player> getPlayers(int page, int size, String sortBy, String direction) {

        //input guardrails
        if (page < 0) page = 0;
        if (size <= 0) size = 10;
        if (size > 50) size = 50;

        //whitelist sort fields - based on Player entity fields
        List<String> validSortFields = List.of("playerId", "firstName", "lastName", "weight", "height", "birthYear");
        if(validSortFields.contains(sortBy)) {
            sortBy = "playerId";
        }

        Sort sort = "DESC".equalsIgnoreCase(direction)
                ? Sort.by(sortBy).descending()
                : Sort.by(sortBy).ascending();


        //Build pageable request object
        Pageable pageable = PageRequest.of(page, size, sort);

        //fetch paginated result
        return playerRepository.findAll(pageable);
    }

}
