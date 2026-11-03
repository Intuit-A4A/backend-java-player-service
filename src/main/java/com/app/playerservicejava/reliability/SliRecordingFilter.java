package com.app.playerservicejava.reliability;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@Order(10)
public class SliRecordingFilter extends OncePerRequestFilter {

    private final SliTracker sliTracker;

    public SliRecordingFilter(SliTracker sliTracker) {
        this.sliTracker = sliTracker;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return !(path.startsWith("/v1/players") || path.startsWith("/v1/chat"));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            long latency = System.currentTimeMillis() - start;
            boolean success = response.getStatus() < 500;
            String path = request.getRequestURI();
            if (path.startsWith("/v1/players")) {
                sliTracker.recordPlayers(success, latency);
            } else if (path.startsWith("/v1/chat")) {
                sliTracker.recordChat(success, latency);
            }
        }
    }
}
