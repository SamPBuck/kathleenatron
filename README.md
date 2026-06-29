# MCL Template Builder — containerized (persistent, shared)

Packages the v2 scheduler app together with a tiny Flask + SQLite backend so the
schedule is stored **server-side** and shared by everyone who opens the page —
instead of living in each visitor's browser.

- **Auth:** none. One shared schedule. The port is **bound to localhost only**
  (`127.0.0.1:24601`), so it isn't exposed on the network — front it with a
  reverse proxy / VPN to publish it.
- **Storage:** a single JSON blob in SQLite at `/data/schedule.db`.

## Run it

```bash
docker compose up --build -d
```

Open <http://localhost:24601>. The badge next to the title shows **Synced** when
the server is the source of truth (or **Local only** if the API can't be reached,
in which case it behaves like the standalone file and uses browser storage).

Plain Docker (no compose):

```bash
docker build -t mcl-template-builder .
docker run -d -p 127.0.0.1:24601:8000 -v mcl-data:/data --name mcl mcl-template-builder
```

## How persistence works

- All schedule data is the one `data` object the app already uses, serialized to
  JSON and kept in `kv['schedule']` in SQLite.
- The DB file is at `/data/schedule.db`, and `/data` is a Docker **volume**
  (`mcl-data`). The schedule therefore survives:
  - container restarts,
  - `docker compose down` / `up`,
  - image rebuilds and upgrades.
- It is lost only if you explicitly delete the volume (`docker volume rm mcl-data`).

To keep the raw `.db` visible on the host instead of a named volume, change the
mount in `docker-compose.yml` to `- ./data:/data`.

## Backups

Two easy paths:

1. **In-app:** the **Save JSON** button still works and downloads the full blob
   (format documented in `DATA_FORMAT.md`).
2. **DB file:** copy it out of the volume, e.g.
   ```bash
   docker cp mcl-template-builder:/data/schedule.db ./schedule-backup.db
   ```

## API (single shared schedule)

| Method | Path             | Purpose                                  |
|--------|------------------|------------------------------------------|
| GET    | `/api/schedule`  | `{ "data": <blob|null>, "updated_at": <iso|null> }` |
| PUT    | `/api/schedule`  | Body = the full `data` object; replaces the stored blob |
| GET    | `/healthz`       | Liveness check                           |
| GET    | `/`              | The app                                  |

## Notes & limits

- **Last-write-wins.** Two people saving at the same time → the later save wins;
  there's no merge or locking. Fine for one scheduler; revisit if several people
  edit different scanners simultaneously.
- The frontend debounces saves (~0.6 s) so drags/resizes don't spam the server,
  and always writes to localStorage first, so an offline blip never loses edits.
- Schema is pinned to the v2 format; incoming data is run through the app's
  `migrate()` on load. Don't point an older (15-min `index.html`) client at this
  backend — see the slot-size caveat in `DATA_FORMAT.md`.
