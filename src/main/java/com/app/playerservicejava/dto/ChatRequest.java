package com.app.playerservicejava.dto;

public class ChatRequest {

    private String message;
    private String model;  // Optional: to allow model selection

    // Getters and Setters
    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }
}
