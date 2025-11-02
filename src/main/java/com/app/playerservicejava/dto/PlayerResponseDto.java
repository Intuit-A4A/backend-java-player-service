package com.app.playerservicejava.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class PlayerResponseDto {

    private String playerId;

    private String birthYear;
    /*private String birthMonth;
    private String birthDay;
    private String birthCountry;
    private String birthState;
    private String birthCity;

    private String deathYear;
    private String deathMonth;
    private String deathDay;
    private String deathCountry;
    private String deathState;
    private String deathCity;*/

    private String firstName;
    private String lastName;
    private String givenName;

    private String weight;
    /*private String height;

    private String bats;
    private String throwStats;

    private String debut;
    private String finalGame;

    private String retroId;
    private String bbrefId;*/
}
