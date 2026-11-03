package com.app.playerservicejava.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;
import java.util.concurrent.RejectedExecutionException;

@RestControllerAdvice
public class PlayerExceptionHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(PlayerExceptionHandler.class);

    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<Map<String, String>> databaseFailure(DataAccessException exc) {
        LOGGER.error("message=Player database failure; exception={}", exc.toString());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of(
                        "error", "player data unavailable",
                        "detail", exc.getClass().getSimpleName()));
    }

    @ExceptionHandler(RejectedExecutionException.class)
    public ResponseEntity<Map<String, String>> chatPoolFull(RejectedExecutionException exc) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", "Chat worker pool is full", "detail", "rejected"));
    }
}
