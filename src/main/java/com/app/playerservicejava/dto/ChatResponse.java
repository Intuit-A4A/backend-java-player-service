package com.app.playerservicejava.dto;

public class ChatResponse {

    private String response;
    private String model;

    public ChatResponse(String response, String model) {
        this.response = response;
        this.model = model;
    }

    // Getters
    public String getResponse() {
        return response;
    }

    public String getModel() {
        return model;
    }
}
