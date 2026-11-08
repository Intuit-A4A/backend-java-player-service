# Demo capture (branch craft-demo/availability, app as-is)
Captured: 2026-11-08T08:48:52-08:00

## 3.2 missing id → 404
```
HTTP/1.1 404 
Content-Length: 0
Date: Sun, 08 Nov 2026 16:48:53 GMT

```

## 3.3 page size 10 (metadata)
```
{"players":[{"playerId":"aardsda01","birthYear":"1981","birthMonth":"12","birthDay":"27","birthCountry":"USA","birthState":"CO","birthCity":"Denver","deathYear":null,"deathMonth":null,"deathDay":null,"deathCountry":null,"deathState":null,"deathCity":null,"firstName":"David","lastName":"Aardsma","givenName":"David Allan","weight":"215","height":"75","bats":"R","throwStats":"R","debut":"2004-04-06","finalGame":"2015-08-23","retroId":"aardd001","bbrefId":"aardsda01"},{"playerId":"aaronha01","birthYear":"1934","birthMonth":"2","birthDay":"5","birthCountry":"USA","birthState":"AL","birthCity":"Mobile","deathYear":null,"deathMonth":null,"deathDay":null,"deathCountry":null,"deathState":null,"deathCity":null,"firstName":"Hank","lastName":"Aaron","givenName":"Henry Louis","weight":"180","height":"72","bats":"R","throwStats":"R","debut":"1954-04-13","finalGame":"1976-10-03","retroId":"aaroh101","bbrefId":"aaronha01"},{"playerId":"aaronto01","birthYear":"1939","birthMonth":"8","birthDay":"5","birthCountry":"USA","birthState":"AL","birthCity":"Mobile","deathYear":"1984","deathMonth":"8","deathDay":"16","deathCountry":"USA","deathState":"GA","deathCity":"Atlanta","firstName":"Tommie","lastName":"Aaron","givenName":"Tommie Lee","weight":"190","height":"75","bats":"R","throwStats":"R","debut":"1962-04-10","finalGame":"1971-09-26","retroId":"aarot101","bbrefId":"aaronto01"},{"playerId":"aasedo01","birthYear":"1954","birthMonth":"9","birthDay":"8","birthCountry":"USA","birthState":"CA","birthCity":"Orange","deathYear":null,"deathMonth":null,"deathDay":null,"deathCountry":null,"deathState":null,"deathCity":null,"firstName":"Don","lastName":"Aase","givenName":"Donald William","weight":"190","height":"75","bats":"R","throwStats":"R","debut":"1977-07-26","finalGame":"1990-10-03","retroId":"aased001","bbrefId":"aasedo01"},{"playerId":"abadan01","birthYear":"1972","birthMonth":"8","birthDay":"25","birthCountry":"USA","birthState":"FL","birthCity":"Palm Beach","deathYear":null,"deathMonth":null,"deathDay":null,"deathCountry":null,"deathState":null,"deathCity":null,"firstName":"Andy","lastName":"Abad","givenName":"Fausto Andres","weight":"184","height":"73","bats":"L","throwStats":"L","debut":"2001-09-10","finalGame":"2006-04-13","retroId":"abada001","bbrefId":"abadan01"},{"playerId":"abadfe01","birthYear":"1985","birthMonth":"12","birthDay":"17","birthCountry":"D.R.","birthState":"La Romana","birthCity":"La Romana","deathYear":null,"deathMonth":null,"deathDay":null,"deathCountry":null,"deathState":null,"deathCity":null,"firstName":"Fernando","lastName":"Abad","givenName":"Fernando Antonio","weight":"220","height":"73","bats":"L","throwStats":"L","debut":"2010-07-28","finalGame":"2017-10-01","retroId":"abadf001","bbrefId":"abadfe01"},{"playerId":"abadijo01","birthYear":"1850","birthMonth":"11","birthDay":"4","birthCountry":"USA","birthState":"PA","birthCity":"Philadelphia","deathYear":"1905","deathMonth":"5","deathDay":"17","deathCountry":"USA","deathState":"NJ","deathCity":"Pemberton","firstName":"John","lastName":"Abadie","givenName":"John W.","weight":"192","height":"72","bats":"R","throwStats":"R","debut":"1875-04-26","finalGame":"1875-06-10","retroId":"abadj101","bbrefId":"abadijo01"},{"playerId":"abbated01","birthYear":"1877","birthMonth":"4","birthDay":"15","birthCountry":"USA","birthState":"PA","birthCity":"Latrobe","deathYear":"1957","deathMonth":"1","deathDay":"6","deathCountry":"USA","deathState":"FL","deathCity":"Fort Lauderdale","firstName":"Ed","lastName":"Abbaticchio","givenName":"Edward James","weight":"170","height":"71","bats":"R","throwStats":"R","debut":"1897-09-04","finalGame":"1910-09-15","retroId":"abbae101","bbrefId":"abbated01"},{"playerId":"abbeybe01","birthYear":"1869","birthMonth":"11","birthDay":"11","birthCountry":"USA","birthState":"VT","birthCity":"Essex","deathYear":"1962","deathMonth":"6","deathDay":"11","deathCountry":"USA","deathState":"VT","deathCity":"Colchester","firstName":"Bert","lastName":"Abbey","givenName":"```

## 3.3 size 101 → 400
```
HTTP/1.1 400 
Content-Type: application/json
Transfer-Encoding: chunked
Date: Sun, 08 Nov 2026 16:48:54 GMT
Connection: close

{"error":"size must not exceed 100"}```

## 3.3 bounded vs default page bytes
```
default_page size_download=23332 time=0.022060s
page0_size10 size_download=4691 time=0.017786s
```

## 3.1 readiness (8081)
```
{"status":"UP","components":{"db":{"status":"UP","details":{"database":"H2","validationQuery":"isValid()"}},"readinessState":{"status":"UP"}}}```

## 3.1 liveness (8081)
```
{"status":"UP","components":{"livenessState":{"status":"UP"}}}```

## 3.1 prometheus tomcat
```
tomcat_threads_busy_threads{name="http-nio-8080"} 0.0
tomcat_threads_config_max_threads{name="http-nio-8080"} 40.0
```

## 3.1 reliability mode
```
{"stage":"baseline","asyncEnabled":false,"poolSize":8,"readTimeoutMs":120000,"ollamaBaseUrl":"http://127.0.0.1:11434"}```

## 3.1 SLI reset + sample
```
{
    "windowStartedAt": "2026-11-08T16:48:54.396Z",
    "availability": 1.0,
    "players": {
        "total": 1,
        "success": 1,
        "errors": 0,
        "availability": 1.0
    },
    "chat": {
        "total": 0,
        "completedBelow500": 0,
        "errors": 0,
        "includedInAvailability": false
    },
    "formula": "availability = player successes / player requests that reached the app; success = player HTTP < 500. Chat is excluded."
}
```

## 3.2 DROP TABLE then by-id (expect 500)
```
HTTP/1.1 500 
Content-Type: application/json
Transfer-Encoding: chunked
Date: Sun, 08 Nov 2026 16:48:55 GMT
Connection: close

{"error":"player data unavailable","detail":"InvalidDataAccessResourceUsageException"}```

