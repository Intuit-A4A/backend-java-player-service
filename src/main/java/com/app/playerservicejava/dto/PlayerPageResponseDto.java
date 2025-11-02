package com.app.playerservicejava.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class PlayerPageResponseDto {
    private List<PlayerResponseDto> players;
    private int page;
    private int size;
    private long totalElements;
    private int totalPages;

}
