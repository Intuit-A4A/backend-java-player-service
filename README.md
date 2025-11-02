# ⚾ Player Service

Player Service is a backend application that serves baseball player data. In addition, Player service integrates with [Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md), which allows us to run the [tinyllama LLM]((https://ollama.com/library/tinyllama)) locally.

## Dependencies

- [Java 17](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html)
- [maven.apache.org](https://maven.apache.org/install.html)
- Spring Boot 3.3.4 (with Spring Web MVC, Spring Data JPA)
- [H2 Database](https://www.h2database.com/html/main.html)
- [Docker](https://www.docker.com/) or [Podman](https://podman.io/)

## 🛠️ Setup Instructions

1. Verify system dependencies
   1. Java 17
      - Verify installation: `java -version`
   2. Maven
      - Download and install from [maven.apache.org](https://maven.apache.org/install.html)
      - Verify installation, run: `mvn --version`
      - Verify java version linked to maven is Java 17 `Java version: 17.x.x`
   3. Container Manager
      - Download and install from [docker.com](https://www.docker.com/)(recommended) or [podman](https://podman.io/) (alternative)
      - Verify installation, run: `docker --version` for docker

2. Clone this repository or Download the code as zip
   - run `git clone https://github.com/Intuit-A4A/backend-java-player-service.git`

## Run the application

### Part 1: Application Dependencies

1. Install application dependencies
    - From the project's root directory, run: `mvn clean install -DskipTests`

### Part 2: Run Player Service (without LLM)

1. Start the Player service

   ```shell
   mvn spring-boot:run
   ./mvnw spring-boot:run
   ```

2. Verify the Player service is running
      1. Open your browser and visit `http://localhost:8080/v1/players`
      2. If the application is running successfully, you will see player data appear in the browser

### Part 3: Start LLM Docker Container

Player service integrates with Ollama 🦙, which allows us to run LLMs locally. This app runs [tinyllama](https://ollama.com/library/tinyllama) model.

- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama4J SDK](https://ollama4j.github.io/ollama4j/intro)

1. Pull and run Ollama docker image and download `tinyllama` model
   - Pull Ollama docker image

    ```shell
    docker pull ollama/ollama
    ```

2. Run Ollama docker image on port 11434 as a background process

    ```shell
    docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
    ```

3. Download and run `tinyllama` model

    ```shell
    docker exec -it ollama ollama run tinyllama
    ```

4. Test Ollama API server

    ```curl
    curl -v --location 'http://localhost:11434/api/generate' --header 'Content-Type: application/json' --data '{"model": "tinyllama","prompt": "why is the sky blue?", "stream": false}'
    ```
Having trouble with docker? Try using podman as an alternative. Instructions [here](https://github.com/Intuit-A4A/backend-java-player-service/wiki/Supplemental-Materials:-Set-up-help#alternative-set-up-instructions)


### Part 4: Verify Player Service and LLM Integration

1. Ensure Player Service is running from previous instructions. If not:

    ```shell
    mvn spring-boot:run
    ```

2. Open your browser and visit `http://localhost:8080/v1/chat/list-models`
   - If the application is running successfully, you will see a json response that include information about tinyllama





## JWT Authentication Request Flow (Step-by-Step)
### 1️⃣ User Logs In

User sends credentials:

```shell
POST /v1/auth/login
{
"username": "admin",
"password": "admin123"
}
```

### 2️⃣ Spring Security Authenticates

AuthController → AuthenticationManager → UserDetailsService

Flow:

* Spring extracts username & password from request
* Calls UserDetailsService.loadUserByUsername()
* Compares passwords using PasswordEncoder (BCrypt)
* If valid → authentication succeeds
* If invalid → throws 401 Unauthorized

### 3️⃣ Server Generates JWT

JwtService.generateToken() runs:

Sets subject (= username)
Sets issued time, expiry
Signs token with secret key (HS256)

Response returned to client:

```shell
{
"token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI..."
}
```

### ✅ Request Flow for Protected API

Now the user calls:

```shell
GET /v1/players/byPage?page=0&size=5
Authorization: Bearer eyJh...
```

### 4️⃣ Request hits Spring Security filter chain

Your SecurityFilterChain sees request is not anonymous → applies JWT filter before UsernamePasswordAuthenticationFilter.

### 5️⃣ JwtAuthenticationFilter runs

It:
```shell
Step	                  Action
Extract	                  Reads Authorization header
Validate format	          Must start with Bearer
Parse token	          jwtService.extractUsername()
Load user	          Calls userDetailsService.loadUserByUsername()
Validate token	          jwtService.isTokenValid(token, user)
```

If valid → creates an Authentication object:

```shell
UsernamePasswordAuthenticationToken
```

and puts it into:

```shell
SecurityContextHolder
```

So Spring Security now knows the user is authenticated.

### ✅ 6️⃣ Controller executes

Your controller method runs normally (user is authenticated).

Because SecurityContext has the username, you can retrieve current user anytime:

```shell
SecurityContextHolder.getContext().getAuthentication().getName();
```

### ✅ 7️⃣ No session is stored

Important point:

JWT = stateless

Server does not store authentication in memory or DB

Each request must send JWT

SessionCreationPolicy.STATELESS in config enforces this

🎯 Full Request Lifecycle Summary

```shell
Step	Description
1️⃣	Client sends username/password to /login
2️⃣	Spring validates credentials
3️⃣	Server issues signed JWT
4️⃣	Client sends JWT on each request
5️⃣	Filter verifies JWT validity
6️⃣	If valid → request reaches controller
7️⃣	If invalid/missing → 401 Unauthorized
```