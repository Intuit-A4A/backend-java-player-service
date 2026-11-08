# DB query filters — high-level implementation answers

Reference for common questions about adding **filtered player queries** to this service. Answers match the code and `Player.csv` as they are today.

**Today**

- [`PlayerRepository`](../src/main/java/com/app/playerservicejava/repository/PlayerRepository.java) is a bare `JpaRepository<Player, String>`. No custom queries.
- [`PlayerService`](../src/main/java/com/app/playerservicejava/service/PlayerService.java) calls `findById` and `findAll()` only. List load copies every row into [`Players`](../src/main/java/com/app/playerservicejava/model/Players.java).
- [`PlayerController`](../src/main/java/com/app/playerservicejava/controller/PlayerController.java) exposes `GET /v1/players` and `GET /v1/players/{id}`. There is no query-param filter.
- Data: [`schema.sql`](../src/main/resources/schema.sql) does `CREATE TABLE PLAYERS AS SELECT * FROM CSVREAD('Player.csv')`. H2 uppercases unquoted names, so CSV header `birthCountry` becomes column `BIRTHCOUNTRY`. The entity maps that with `@Column`.
- Spring Data method names follow **Java fields**, not CSV headers. `lastName` is the field (`NAMELAST` / CSV `nameLast`). `throwStats` is the field (`THROWS` / CSV `throws`) because `throws` is a Java keyword.

`Player.csv` is about **19,370** rows and **56** birth-country values. The common ones are `USA` (16,879), `D.R.`, `Venezuela`, `P.R.`, `CAN`. **68** rows have a blank `birthCountry`, **126** have a blank `birthYear`, and bats/throws include blanks (`R` / `L` / `B` / empty, plus one `S` throw).

---

## 1. Players by birth country

**Question:** Add `GET /v1/players?birthCountry=USA`.

**Answer:**

Keep the filter on the existing collection URL. Do not use `GET /v1/players/USA`. That path is already `GET /v1/players/{id}` and would look up player id `USA`, then return **404**.

- **Repository:** `List<Player> findByBirthCountry(String birthCountry);`
  Spring Data emits `WHERE BIRTHCOUNTRY = ?` from the `birthCountry` field.
- **Controller:** `@RequestParam(required = false) String birthCountry` on the existing list method.
- **Service:**
  - Param **absent** → keep `findAll()` so current clients stay the same.
  - Param **blank after trim** → **400** `{"error":"birthCountry is blank"}`. Do this in the controller or service. Spring will not reject a blank string by itself.
  - Otherwise `trim()` and call `findByBirthCountry`. Put the list in the existing `Players` wrapper so the JSON stays `{ "players": [ ... ] }`.
- **Failures:** Do not catch `DataAccessException` and return an empty list. [`PlayerExceptionHandler`](../src/main/java/com/app/playerservicejava/controller/PlayerExceptionHandler.java) already maps that to **500** `"player data unavailable"`.

Exact match is case-sensitive. `USA` hits the data; `usa` does not unless you use `findByBirthCountryIgnoreCase` (see §7). `D.R.` and `P.R.` must be passed as stored, including the dots.

---

## 2. Multiple filters (AND)

**Question:** Country plus `bats=R` and `throws=R`.

**Answer:**

All provided params are **AND**. A missing param means “do not constrain that column.”

Derived methods work for a fixed pair:

```java
List<Player> findByBirthCountryAndBatsAndThrowStats(
        String birthCountry, String bats, String throwStats);
```

`throwStats` is required in the method name. `findBy...Throws...` does not compile against this entity.

That style does not scale. Three optional params need every subset (`country`, `country+bats`, `bats+throws`, and so on). Prefer one search method:

- `PlayerRepository extends JpaRepository<Player, String>, JpaSpecificationExecutor<Player>`
- A small `PlayerSearch` (country, bats, throws, last-name prefix, year range) built in the controller.
- `PlayerService` adds a predicate only for each non-blank field, combined with `and`, then `repository.findAll(spec)`.

Validate allowed bats (`R`, `L`, `B`) and throws (`R`, `L`, `S`) if you want **400** for garbage. The CSV also has blank bats/throws; those rows match only if the client does not send that param. Do not treat blank stored values as `R`.

---

## 3. Partial name search

**Question:** Filter by last name prefix or substring.

**Answer:**

Use the Java field `lastName`, not `nameLast`:

```java
List<Player> findByLastNameStartingWithIgnoreCase(String prefix);
```

Prefix (`Aaron` → Aaron, Aaronson, …) can use an index. Substring (`%ron%`) cannot, and on this table it scans all ~19k rows. That is fine for the demo; it is the wrong default for a public API.

If you write JPQL, bind the term. Do not concatenate it:

```java
@Query("SELECT p FROM Player p WHERE LOWER(p.lastName) LIKE LOWER(CONCAT(:prefix, '%'))")
List<Player> findByLastNamePrefix(@Param("prefix") String prefix);
```

`CONCAT(:prefix, '%')` keeps `%` and `_` inside the user value as literals only if you escape them first. Replace `\` `%` `_` in the service and add `ESCAPE '\\'` if clients may send those characters. Reject a prefix shorter than 2 characters so a single letter does not return thousands of rows.

`firstName` / `givenName` follow the same pattern (`findByFirstNameStartingWithIgnoreCase`). CSV header `nameFirst` is not the JPA property.

---

## 4. Pagination and sorting

**Question:** Return pages instead of the full roster.

**Answer:**

`GET /v1/players` currently serializes the full CSV on one Tomcat thread. A country filter for `USA` is still ~17k rows. Add paging with the filter, not after it.

```java
Page<Player> findByBirthCountry(String birthCountry, Pageable pageable);
```

API: `page` (0-based), `size`, optional `sort=lastName,asc`. Sort names are **entity fields** (`lastName`, `playerId`), not CSV names (`nameLast`). An unknown sort property is a **400** from Spring Data, not a DB error.

Cap `size` in the service (for example max 100). `@PageableDefault(size = 20, sort = "playerId")` gives a stable order when the client omits `sort`.

`Players` has only `players`. Either add `totalElements`, `totalPages`, `page`, and `size` to that type, or return a new page DTO. Do not drop totals: clients cannot tell a short page from the end of the data without them.

`playerId` is unique, so use it as a tie-break (`sort=lastName,asc&sort=playerId,asc`) or pages can skip or repeat rows when last names collide.

---

## 5. Empty list vs 404

**Question:** Unknown country with zero rows — 200 or 404?

**Answer:**

| Situation | Status | Body |
|-----------|--------|------|
| Filter matches nothing (`birthCountry=Atlantis`) | **200** | `{ "players": [] }` |
| `GET /v1/players/{id}` and the id is absent | **404** | empty (current controller) |
| Blank `birthCountry=` | **400** | validation error |
| Table missing, SQL error, timeout | **500** | `"player data unavailable"` |

**200** is correct for an empty filter because the collection exists; the predicate matched nothing. **404** is only for a single resource identified by the URL, which is what `getPlayerById` already does.

Do not copy the old `main` bug: catching every exception and returning `Optional.empty()` turned a dropped `PLAYERS` table into **404**. `getPlayerById` now lets `DataAccessException` propagate. Filtered queries must do the same. An empty list is a successful query, not a failure.

Blank `birthCountry` in the CSV (68 rows) is real data. `?birthCountry=` should be **400**, not “return those 68 rows,” unless you explicitly support a sentinel.

---

## 6. String-typed year / numeric fields

**Question:** Filter players with `birthYear` after 1990.

**Answer:**

`birthYear`, `weight`, and `height` are `String` on [`Player`](../src/main/java/com/app/playerservicejava/model/Player.java). Lexical compare is wrong: `"9" > "1990"` and `"200" < "75"` for weight.

API: `Integer birthYearFrom` and `birthYearTo`. Reject `from > to` with **400** before hitting the database.

Do not `CAST` every row blindly. **126** birth years are empty. `CAST('' AS int)` fails the whole query and becomes **500**, which looks like an outage. Exclude blanks in JPQL, for example `p.birthYear <> ''` and then cast, or filter in the database with a condition that skips non-numeric values.

Longer term, load numeric columns as integers (or a view) so the predicate is a normal range and bad CSV rows fail at startup instead of at request time. `debut` is `YYYY-MM-DD` text, so a debut-year filter can use `SUBSTRING(p.debut, 1, 4)` or a real date column; empty debut must be excluded the same way.

Weight and height have the same string problem if you add “taller than” filters.

---

## 7. Country normalization

**Question:** `USA` vs `usa` vs extra spaces.

**Answer:**

Always `trim()`. Then pick one match rule and document it.

Stored values are mixed: `USA`, `CAN`, `D.R.`, `P.R.`, `Venezuela`, `Mexico`, `Cuba`. Uppercasing the whole string is safe for `USA` and breaks nothing that is already upper, but `IgnoreCase` is the smaller behavior change:

```java
List<Player> findByBirthCountryIgnoreCase(String birthCountry);
```

`usa` and `USA` then match. `D.R.` still needs the punctuation; `DR` will not match. Do not add an alias map unless a product requirement lists aliases (`US` → `USA`, `Dominican Republic` → `D.R.`). Keep aliases in the service, applied before the query, so SQL stays a single bound parameter.

Do not rewrite the CSV on read. Normalization belongs on the request, not in an `UPDATE` during a GET.

---

## 8. SQL injection safety

**Question:** How do you keep dynamic filters safe?

**Answer:**

| Approach | Safe? |
|----------|--------|
| Derived query (`findByBirthCountry`) | Yes. Spring binds the argument. |
| `@Query` with `:birthCountry` and `@Param` | Yes. |
| `Specification` / Criteria `cb.equal(root.get("birthCountry"), value)` | Yes. The value is a bind parameter. |
| `"WHERE BIRTHCOUNTRY = '" + country + "'"` | No. |

Sort is the easy hole. If you accept a raw `ORDER BY` string from the client, a value like `name; drop table` is dangerous in native SQL. Use `Pageable` and allow only known properties (`lastName`, `playerId`, `birthYear`). Spring Data rejects unknown properties.

Native SQL is unnecessary for these filters. If you use it, only `?` / named parameters, never concatenated identifiers. Column names still cannot be parameters; whitelist those too.

---

## 9. H2, CSV load, and indexes

**Question:** Performance implications on this stack.

**Answer:**

`schema.sql` runs against the embedded H2 database (`jdbc:h2:mem:playerdb`, `ddl-auto: none`). Hibernate does not create `PLAYERS`; the CSV load does. `CSVREAD('Player.csv')` is resolved from the **process working directory** (the repo root when you start the app there). A different cwd fails startup, not the filter.

The table has **no indexes**. `findById` is a scan unless `PLAYERID` is a primary key. `CREATE TABLE AS SELECT` does not copy a PK from the CSV. Add indexes in `schema.sql` after the load:

```sql
ALTER TABLE PLAYERS ADD PRIMARY KEY (PLAYERID);
CREATE INDEX idx_players_birth_country ON PLAYERS (BIRTHCOUNTRY);
CREATE INDEX idx_players_last_name ON PLAYERS (NAMELAST);
```

Use the uppercased names H2 actually created. An index helps equality and prefix (`LIKE 'Aar%'`). It does not help `LIKE '%ron%'`.

`findAll()` materializes ~19k entities and holds the Hibernate session through JSON serialization (`open-in-view` default). Filtered pages avoid that. This CSV load is a demo bootstrap, not a migration path; production would use a real schema and a loader job.

The H2 database is **in-memory and per JVM**. SQL you run in another process does not see the app’s data.

---

## 10. Timeouts and slow filtered queries

**Question:** What happens when a filtered query hangs?

**Answer:**

There is no per-query timeout in the current player path. A stuck JDBC call holds the Tomcat worker until the driver or pool gives up. When it does surface as `QueryTimeoutException` or another `DataAccessException`, [`PlayerExceptionHandler`](../src/main/java/com/app/playerservicejava/controller/PlayerExceptionHandler.java) returns **500** with `"player data unavailable"` and the exception’s simple class name in `detail`.

That is the right mapping. A timeout is not “no such player.” **404** happens only after `findById` returns `Optional.empty()` with no exception. Filtered list endpoints should not return **404** on timeout or on zero rows.

`getPlayerById` sleeps 0–2s **after** a successful read. That sleep is not a DB timeout and must not be copied onto list or filter methods. An interrupt there becomes `IllegalStateException`, which this handler does **not** catch (only `DataAccessException`), so it falls through to Spring’s default error body. Filter code should not add that sleep.

If a later change adds a JDBC statement timeout or a retry guard, put `findAll`, `findById`, and every new filter through it. A guard only around `findById` leaves list filters unbounded.

---

## 11. Observability and SLI

**Question:** Do filtered list calls count toward player availability?

**Answer:**

Yes. [`SliRecordingFilter`](../src/main/java/com/app/playerservicejava/reliability/SliRecordingFilter.java) records any URI starting with `/v1/players`. Query strings are not part of that check. `?birthCountry=USA` is player traffic.

Success is `status < 500`:

- **200** empty list → available (correct).
- **400** bad param → available (the process and DB were fine; the client was not).
- **404** unknown id → available.
- **500** DB failure → unavailable.

No filter change is required unless the new route leaves the `/v1/players` prefix.

Micrometer’s `http.server.requests` uri tag should stay the **pattern** (`/v1/players`), not the raw query. Do not put `birthCountry` in a metric tag: 56 countries is bounded, but free-text last-name prefixes are not. Latency of the unpaged list will dominate the player SLI until paging exists, because one call serializes the whole table.

---

## 12. Load and Tomcat workers

**Question:** Filters vs returning the whole table under load.

**Answer:**

`server.tomcat.threads.max` is **40**. Each list or filter call occupies one worker for DB time plus JSON encoding. Chat on the request thread can occupy the rest (craft-demo). A filter does not add threads and does not shrink the pool.

What it does change:

- `GET /v1/players` sends ~19k players every time. That is the expensive call.
- `?birthCountry=CAN` (~249 rows) is much cheaper to serialize than `USA` (~17k) or an unfiltered list.
- Paging bounds the worst case. A filter without paging does not.

Do not add the by-id sleep to list/filter. Do not `findAll()` and then `stream().filter(...)` in the service: you still read and map every row, and you only save a little JSON. Push the predicate to SQL.

Chat saturation is a separate fix (async chat, shorter Ollama timeout). Player filters do not keep player calls runnable when all 40 workers are blocked in Ollama.

---

## 13. Country filter vs LLM nickname

**Question:** Nickname from a country vs players from that country.

**Answer:**

These are different reads. Keep them separate.

- **Roster:** `GET /v1/players?birthCountry=Japan` (or `Venezuela` — use a value that exists in the CSV). SQL filter in the repository. Response is `Players`.
- **Generated nickname:** a chat route that calls Ollama with the country string. It does not need H2. The tree does not currently expose a nickname endpoint; `POST /v1/chat` is a fixed prompt.

Do not implement “players from Japan” by loading every player and filtering in Java, and do not call the model once per row. If a later endpoint returns one nickname **and** a sample of matching players, do the DB query first (paged), then one Ollama call with the country. If Ollama fails, the player list can still be **200**; chat failure stays **503** on the chat call. Mixing them into one handler makes a model timeout look like a player-data outage in the player SLI only if that handler lives under `/v1/players`.

---

## 14. Verifying filters in H2 console

**Question:** How to test SQL before wiring the API?

**Answer:**

`spring.h2.console.enabled` is already `true`. Open `http://localhost:8080/h2-console` and connect to the **same JVM**:

- JDBC URL: `jdbc:h2:mem:playerdb`
- User: `sa`
- Password: empty

A console pointed at a new in-memory URL will show an empty database. Useful checks:

```sql
SELECT BIRTHCOUNTRY, COUNT(*) FROM PLAYERS GROUP BY BIRTHCOUNTRY ORDER BY COUNT(*) DESC;
SELECT * FROM PLAYERS WHERE BIRTHCOUNTRY = 'USA' LIMIT 10;
SELECT PLAYERID, NAMELAST FROM PLAYERS WHERE UPPER(NAMELAST) LIKE 'AAR%' LIMIT 10;
```

Column names in the console are the uppercased H2 names (`BIRTHCOUNTRY`, `NAMELAST`, `THROWS`), not the Java names.

Outage drill from the demo: `DROP TABLE PLAYERS`, then `GET /v1/players?birthCountry=USA`. Expect **500** from `PlayerExceptionHandler`, not **200** with `players: []` and not **404**. Restart the app to reload the CSV; the drop lasts until the process exits.

---

## Suggested layering

```text
GET /v1/players?birthCountry=&bats=&throws=&page=&size=
        -> PlayerController
             trim, blank -> 400, Pageable, sort whitelist
        -> PlayerService.search
             Specification (AND of present fields)
             no catch-and-return-empty
        -> PlayerRepository
        -> H2 PLAYERS
        -> DataAccessException -> PlayerExceptionHandler -> 500
```

`GET /v1/players/{id}` stays a separate method. Do not overload `{id}` for country codes.

---

## Minimal change set (one filter, end to end)

| Layer | Change |
|-------|--------|
| `PlayerRepository` | `findByBirthCountryIgnoreCase(String)` or `JpaSpecificationExecutor` if more params are coming in the same change |
| `PlayerService` | If param is null, `findAll()`; else repository filter. No try/catch that returns an empty `Players`. |
| `PlayerController` | Optional `@RequestParam String birthCountry`. Blank → **400**. |
| Response | Same `Players` JSON. Empty match → **200** and `[]`. |
| Tests | `@DataJpaTest`: `USA` returns rows, `Atlantis` returns empty, case fold if you chose ignore-case. `@WebMvcTest`: blank param → 400; repository exception → 500, not 404. |
| Schema | Optional index on `BIRTHCOUNTRY` if this leaves the demo. |
| Docs | One curl next to the existing player examples. |

No change to chat, Ollama, or `SliRecordingFilter` while the route stays under `/v1/players`.
