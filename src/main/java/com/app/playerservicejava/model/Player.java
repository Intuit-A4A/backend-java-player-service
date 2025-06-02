package com.app.playerservicejava.model;

import jakarta.persistence.*;

@Entity
@Table(name="PLAYERS")
public class Player {

    @Id
    @Column(name = "PLAYERID")
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long playerId;

    @Column(name = "BIRTHYEAR")
    private String birthYear;

    @Column(name = "BIRTHMONTH")
    private String birthMonth;

    @Column(name = "BIRTHDAY")
    private String birthDay;

    @Column(name = "BIRTHCOUNTRY")
    private String birthCountry;

    @Column(name = "BIRTHSTATE")
    private String birthState;

    @Column(name = "BIRTHCITY")
    private String birthCity;

    @Column(name = "DEATHYEAR")
    private String deathYear;

    @Column(name = "DEATHMONTH")
    private String deathMonth;

    @Column(name = "DEATHDAY")
    private String deathDay;

    @Column(name = "DEATHCOUNTRY")
    private String deathCountry;

    @Column(name = "DEATHSTATE")
    private String deathState;

    @Column(name = "DEATHCITY")
    private String deathCity;

    @Column(name = "NAMEFIRST")
    private String firstName;

    @Column(name = "NAMELAST")
    private String lastName;

    @Column(name = "NAMEGIVEN")
    private String givenName;

    @Column(name = "WEIGHT")
    private String weight;

    @Column(name = "HEIGHT")
    private String height;

    @Column(name = "BATS")
    private String bats;

    @Column(name = "THROWS")
    private String throwStats;

    @Column(name = "DEBUT")
    private String debut;

    @Column(name = "FINALGAME")
    private String finalGame;

    @Column(name = "RETROID")
    private String retroId;

    @Column(name = "BBREFID")
    private String bbrefId;

    public Player() {}

    public Long getPlayerId() {
        return playerId;
    }

    public void setPlayerId(Long playerId) {
        this.playerId = playerId;
    }

    public String getBirthYear() {
        return birthYear;
    }

    public void setBirthYear(String birthYear) {
        this.birthYear = birthYear;
    }

    public String getBirthMonth() {
        return birthMonth;
    }

    public void setBirthMonth(String birthMonth) {
        this.birthMonth = birthMonth;
    }

    public String getBirthDay() {
        return birthDay;
    }

    public void setBirthDay(String birthDay) {
        this.birthDay = birthDay;
    }

    public String getBirthCountry() {
        return birthCountry;
    }

    public void setBirthCountry(String birthCountry) {
        this.birthCountry = birthCountry;
    }

    public String getBirthState() {
        return birthState;
    }

    public void setBirthState(String birthState) {
        this.birthState = birthState;
    }

    public String getBirthCity() {
        return birthCity;
    }

    public void setBirthCity(String birthCity) {
        this.birthCity = birthCity;
    }

    public String getDeathYear() {
        return deathYear;
    }

    public void setDeathYear(String deathYear) {
        this.deathYear = deathYear;
    }

    public String getDeathMonth() {
        return deathMonth;
    }

    public void setDeathMonth(String deathMonth) {
        this.deathMonth = deathMonth;
    }

    public String getDeathDay() {
        return deathDay;
    }

    public void setDeathDay(String deathDay) {
        this.deathDay = deathDay;
    }

    public String getDeathCountry() {
        return deathCountry;
    }

    public void setDeathCountry(String deathCountry) {
        this.deathCountry = deathCountry;
    }

    public String getDeathState() {
        return deathState;
    }

    public void setDeathState(String deathState) {
        this.deathState = deathState;
    }

    public String getDeathCity() {
        return deathCity;
    }

    public void setDeathCity(String deathCity) {
        this.deathCity = deathCity;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public String getGivenName() {
        return givenName;
    }

    public void setGivenName(String givenName) {
        this.givenName = givenName;
    }

    public String getWeight() {
        return weight;
    }

    public void setWeight(String weight) {
        this.weight = weight;
    }

    public String getHeight() {
        return height;
    }

    public void setHeight(String height) {
        this.height = height;
    }

    public String getBats() {
        return bats;
    }

    public void setBats(String bats) {
        this.bats = bats;
    }

    public String getThrowStats() {
        return throwStats;
    }

    public void setThrowStats(String throwStats) {
        this.throwStats = throwStats;
    }

    public String getDebut() {
        return debut;
    }

    public void setDebut(String debut) {
        this.debut = debut;
    }

    public String getFinalGame() {
        return finalGame;
    }

    public void setFinalGame(String finalGame) {
        this.finalGame = finalGame;
    }

    public String getRetroId() {
        return retroId;
    }

    public void setRetroId(String retroId) {
        this.retroId = retroId;
    }

    public String getBbrefId() {
        return bbrefId;
    }

    public void setBbrefId(String bbrefId) {
        this.bbrefId = bbrefId;
    }
}
