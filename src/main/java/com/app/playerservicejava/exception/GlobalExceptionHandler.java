package com.app.playerservicejava.exception;

import io.github.ollama4j.exceptions.OllamaBaseException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(Exception.class)
    public ResponseEntity<String> handleException(Exception ex) {
        LOGGER.error("An error occurred: ", ex);
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("An error occurred: " + ex.getMessage());
    }

    @ExceptionHandler(OllamaBaseException.class)
    public ResponseEntity<String> handleOllamaException(OllamaBaseException ex) {
        LOGGER.error("Ollama error occurred: ", ex);
        return ResponseEntity
                .status(HttpStatus.BAD_GATEWAY)
                .body("Ollama service error: " + ex.getMessage());
    }
}
