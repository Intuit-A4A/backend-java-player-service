package com.app.playerservicejava.controller;

import com.app.playerservicejava.dto.PlayerPageResponseDto;
import com.app.playerservicejava.dto.PlayerResponseDto;
import com.app.playerservicejava.model.Player;
import com.app.playerservicejava.model.Players;
import com.app.playerservicejava.service.PlayerService;
import jakarta.annotation.Resource;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

import static org.springframework.http.ResponseEntity.ok;

@RestController
@RequestMapping(value = "v1/players", produces = { MediaType.APPLICATION_JSON_VALUE })
public class PlayerController {
    @Resource
    private PlayerService playerService;

    @RequestMapping(method = RequestMethod.GET)
    public ResponseEntity<Players> getPlayers() {
        Players players = playerService.getPlayers();
        return ok(players);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Player> getPlayerById(@PathVariable("id") String id) {
        Optional<Player> player = playerService.getPlayerById(id);

        if (player.isPresent()) {
            return new ResponseEntity<>(player.get(), HttpStatus.OK);
        } else {
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        }
    }

    @GetMapping("/byPage")
    public ResponseEntity<PlayerPageResponseDto> getPlayersPage(@RequestParam(defaultValue = "0") int page,
                                                                @RequestParam(defaultValue = "10") int size,
                                                                @RequestParam(defaultValue = "playerId") String sortBy,
                                                                @RequestParam(defaultValue = "ASC") String direction) {
        Page<Player> playersPage = playerService.getPlayers(page, size, sortBy, direction);

        List<PlayerResponseDto> players = playersPage.getContent()
                .stream()
                .map(this::toPlayerResponseDto)
                .collect(Collectors.toList());

        PlayerPageResponseDto response = new PlayerPageResponseDto(
                players,
                playersPage.getNumber(),
                playersPage.getSize(),
                playersPage.getTotalElements(),
                playersPage.getTotalPages()
        );

        PlayerPageResponseDto responseDto = new PlayerPageResponseDto(players,
                playersPage.getNumber(),
                playersPage.getSize(),
                playersPage.getTotalElements(),
                playersPage.getTotalPages());

        return ResponseEntity.ok(responseDto);
    }

    public PlayerResponseDto toPlayerResponseDto(Player player) {
        if (player == null) {
            return null;
        }

        PlayerResponseDto dto = new PlayerResponseDto();

        dto.setPlayerId(player.getPlayerId());
        dto.setBirthYear(player.getBirthYear());
        /*dto.setBirthMonth(player.getBirthMonth());
        dto.setBirthDay(player.getBirthDay());
        dto.setBirthCountry(player.getBirthCountry());
        dto.setBirthState(player.getBirthState());
        dto.setBirthCity(player.getBirthCity());
        dto.setDeathYear(player.getDeathYear());
        dto.setDeathMonth(player.getDeathMonth());
        dto.setDeathDay(player.getDeathDay());
        dto.setDeathCountry(player.getDeathCountry());
        dto.setDeathState(player.getDeathState());
        dto.setDeathCity(player.getDeathCity());*/
        dto.setFirstName(player.getFirstName());
        dto.setLastName(player.getLastName());
        dto.setGivenName(player.getGivenName());
        dto.setWeight(player.getWeight());
        /*dto.setHeight(player.getHeight());
        dto.setBats(player.getBats());
        dto.setThrowStats(player.getThrowStats());
        dto.setDebut(player.getDebut());
        dto.setFinalGame(player.getFinalGame());
        dto.setRetroId(player.getRetroId());
        dto.setBbrefId(player.getBbrefId());*/

        return dto;
    }

}
