"""SQLite implementations of the seven repositories.

Chosen over Firestore for the owner's real game because the app has exactly one
writer and a tiny dataset, and because Firestore round trips measured 450-1900ms
from this machine against ~70ms of network RTT — a page load spent ~9.7s in
seven sequential round trips. Local SQLite makes the same reads sub-millisecond
and removes the network from the picture entirely.

Nothing outside this module knows SQLite exists: the repositories satisfy the
same interfaces (and the same contract tests) as the memory and Firebase ones.

Storage conventions, all decided once here:
  - datetimes are ISO-8601 strings, always timezone-aware, always stored as UTC
  - dicts and lists are JSON text
  - enums are stored by the same name/value the Firestore layer uses, so the
    two backends stay readable against each other
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from core.entities import (
    CollectableStock,
    FriendLink,
    GeneratedContent,
    Receptacle,
    Task,
    Treasure,
    empty_collectable_stock,
)
from core.enums import (
    CollectableRarity,
    Element,
    GeneratedKind,
    ReceptacleRarity,
    ReceptacleState,
    TaskVirtue,
    Virtue,
)
from core.errors import AlreadyExists, InsufficientCoins, InsufficientCollectables, NotFound
from repos.interfaces import (
    CollectableRepository,
    FriendLinkRepository,
    MetaRepository,
    ReceptacleRepository,
    TaskRepository,
    TreasureRepository,
    WalletRepository,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id                TEXT PRIMARY KEY,
    text              TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    value             INTEGER NOT NULL,
    virtues           TEXT NOT NULL,
    fragments_awarded TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

CREATE TABLE IF NOT EXISTS collectables (
    element TEXT NOT NULL,
    rarity  TEXT NOT NULL,
    count   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (element, rarity)
);

-- Single row, pinned by the CHECK so a second wallet cannot be created.
CREATE TABLE IF NOT EXISTS wallet (
    id    INTEGER PRIMARY KEY CHECK (id = 1),
    coins INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS receptacles (
    id           TEXT PRIMARY KEY,
    state        TEXT NOT NULL,
    virtue       TEXT NOT NULL,
    rarity       INTEGER NOT NULL,
    value        INTEGER NOT NULL,
    is_generated INTEGER NOT NULL,
    is_secret    INTEGER NOT NULL,
    friend_name  TEXT,
    reward_text  TEXT,
    content      TEXT,
    treasure_id  TEXT,
    created_at   TEXT NOT NULL,
    opened_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_receptacles_state ON receptacles(state);
CREATE INDEX IF NOT EXISTS idx_receptacles_generated ON receptacles(is_generated);

CREATE TABLE IF NOT EXISTS treasures (
    id             TEXT PRIMARY KEY,
    slot           INTEGER NOT NULL,
    receptacle_ids TEXT NOT NULL,
    pity           TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    price          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS friend_links (
    name       TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _new_id() -> str:
    return uuid.uuid4().hex


def _dt_out(value: datetime | None) -> str | None:
    """Store timezone-aware UTC. A naive datetime is assumed to already be UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _dt_in(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class SQLiteDatabase:
    """Owns the file, the schema, and one connection per thread.

    Django's dev server serves requests on multiple threads and a sqlite3
    connection may not be shared between them, so each thread gets its own.
    WAL lets those threads read while one writes; the lock below serializes
    the writers, which is free here because there is only ever one player.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.RLock()
        # :memory: databases are per-connection, so a shared one must be held
        # open and reused rather than reconnected per thread.
        self._shared: sqlite3.Connection | None = None
        if path == ":memory:":
            self._shared = self._new_connection()
        # Not via write(): executescript() issues its own COMMIT first, which
        # would leave the surrounding transaction with nothing to commit.
        with self._write_lock:
            self.conn.executescript(SCHEMA)

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            isolation_level=None,  # explicit transactions, no implicit BEGIN
        )
        conn.row_factory = sqlite3.Row
        if self.path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._new_connection()
            self._local.conn = conn
        return conn

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """A serialized, all-or-nothing write transaction."""
        with self._write_lock:
            conn = self.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except Exception:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")


# --- tasks ---


class SQLiteTaskRepository(TaskRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def add(self, task: Task) -> Task:
        task_id = task.id or _new_id()
        with self._db.write() as conn:
            conn.execute(
                "INSERT INTO tasks (id, text, created_at, value, virtues, fragments_awarded)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    task.text,
                    _dt_out(task.created_at),
                    task.value,
                    json.dumps({k.value: v for k, v in task.virtues.items()}),
                    json.dumps({k.value: v for k, v in task.fragments_awarded.items()}),
                ),
            )
        return Task(
            id=task_id,
            text=task.text,
            created_at=task.created_at,
            value=task.value,
            virtues=dict(task.virtues),
            fragments_awarded=dict(task.fragments_awarded),
        )

    def list_since(self, since: datetime) -> list[Task]:
        rows = self._db.conn.execute(
            "SELECT * FROM tasks WHERE created_at >= ? ORDER BY created_at",
            (_dt_out(since),),
        ).fetchall()
        return [_row_to_task(r) for r in rows]


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        text=row["text"],
        created_at=_dt_in(row["created_at"]),
        value=row["value"],
        virtues={TaskVirtue(k): v for k, v in json.loads(row["virtues"]).items()},
        fragments_awarded={Element(k): v for k, v in json.loads(row["fragments_awarded"]).items()},
    )


# --- collectables ---


class SQLiteCollectableRepository(CollectableRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def get_all(self) -> CollectableStock:
        stock = empty_collectable_stock()
        for row in self._db.conn.execute("SELECT element, rarity, count FROM collectables"):
            stock[(Element(row["element"]), CollectableRarity[row["rarity"]])] = row["count"]
        return stock

    def adjust(self, deltas: dict[tuple[Element, CollectableRarity], int]) -> None:
        """All-or-nothing: if any single counter would go negative, nothing moves."""
        with self._db.write() as conn:
            for (element, rarity), delta in deltas.items():
                row = conn.execute(
                    "SELECT count FROM collectables WHERE element = ? AND rarity = ?",
                    (element.value, rarity.name),
                ).fetchone()
                current = row["count"] if row else 0
                if current + delta < 0:
                    raise InsufficientCollectables(
                        f"cannot take {-delta} {element.value} {rarity.name}: only {current} held"
                    )
            for (element, rarity), delta in deltas.items():
                conn.execute(
                    "INSERT INTO collectables (element, rarity, count) VALUES (?, ?, ?)"
                    " ON CONFLICT(element, rarity) DO UPDATE SET count = count + ?",
                    (element.value, rarity.name, max(delta, 0), delta),
                )


# --- wallet ---


class SQLiteWalletRepository(WalletRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def get_coins(self) -> int:
        row = self._db.conn.execute("SELECT coins FROM wallet WHERE id = 1").fetchone()
        return row["coins"] if row else 0

    def adjust(self, delta: int) -> int:
        with self._db.write() as conn:
            row = conn.execute("SELECT coins FROM wallet WHERE id = 1").fetchone()
            current = row["coins"] if row else 0
            new_balance = current + delta
            if new_balance < 0:
                raise InsufficientCoins(f"cannot spend {-delta} coins: only {current} held")
            conn.execute(
                "INSERT INTO wallet (id, coins) VALUES (1, ?)"
                " ON CONFLICT(id) DO UPDATE SET coins = ?",
                (new_balance, new_balance),
            )
            return new_balance


# --- receptacles ---


def _content_out(content: GeneratedContent | None) -> str | None:
    if content is None:
        return None
    return json.dumps(
        {
            "kind": content.kind.value,
            "title": content.title,
            "url": content.url,
            "author": content.author,
            "text": content.text,
        }
    )


def _content_in(raw: str | None) -> GeneratedContent | None:
    if not raw:
        return None
    d = json.loads(raw)
    return GeneratedContent(
        kind=GeneratedKind(d["kind"]),
        title=d["title"],
        url=d["url"],
        author=d["author"],
        text=d["text"],
    )


def _row_to_receptacle(row: sqlite3.Row) -> Receptacle:
    return Receptacle(
        id=row["id"],
        state=ReceptacleState(row["state"]),
        virtue=Virtue(row["virtue"]),
        rarity=ReceptacleRarity(row["rarity"]),
        value=row["value"],
        is_generated=bool(row["is_generated"]),
        is_secret=bool(row["is_secret"]),
        friend_name=row["friend_name"],
        reward_text=row["reward_text"],
        content=_content_in(row["content"]),
        treasure_id=row["treasure_id"],
        created_at=_dt_in(row["created_at"]),
        opened_at=_dt_in(row["opened_at"]),
    )


_RECEPTACLE_COLUMNS = (
    "id, state, virtue, rarity, value, is_generated, is_secret, friend_name,"
    " reward_text, content, treasure_id, created_at, opened_at"
)


def _receptacle_params(r: Receptacle, receptacle_id: str) -> tuple:
    return (
        receptacle_id,
        r.state.value,
        r.virtue.value,
        r.rarity.value,
        r.value,
        int(r.is_generated),
        int(r.is_secret),
        r.friend_name,
        r.reward_text,
        _content_out(r.content),
        r.treasure_id,
        _dt_out(r.created_at),
        _dt_out(r.opened_at),
    )


class SQLiteReceptacleRepository(ReceptacleRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def add(self, receptacle: Receptacle) -> Receptacle:
        receptacle_id = receptacle.id or _new_id()
        with self._db.write() as conn:
            conn.execute(
                f"INSERT INTO receptacles ({_RECEPTACLE_COLUMNS})"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                _receptacle_params(receptacle, receptacle_id),
            )
        stored = self.get(receptacle_id)
        return stored

    def get(self, receptacle_id: str) -> Receptacle:
        row = self._db.conn.execute(
            "SELECT * FROM receptacles WHERE id = ?", (receptacle_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"no receptacle with id {receptacle_id}")
        return _row_to_receptacle(row)

    def get_many(self, receptacle_ids: list[str]) -> list[Receptacle]:
        """One query for the whole batch, returned in the order asked for."""
        if not receptacle_ids:
            return []
        placeholders = ",".join("?" * len(receptacle_ids))
        rows = self._db.conn.execute(
            f"SELECT * FROM receptacles WHERE id IN ({placeholders})", tuple(receptacle_ids)
        ).fetchall()
        by_id = {r["id"]: _row_to_receptacle(r) for r in rows}
        return [by_id[i] for i in receptacle_ids if i in by_id]

    def update(self, receptacle: Receptacle) -> None:
        with self._db.write() as conn:
            cur = conn.execute(
                "UPDATE receptacles SET state = ?, virtue = ?, rarity = ?, value = ?,"
                " is_generated = ?, is_secret = ?, friend_name = ?, reward_text = ?,"
                " content = ?, treasure_id = ?, created_at = ?, opened_at = ? WHERE id = ?",
                (*_receptacle_params(receptacle, receptacle.id)[1:], receptacle.id),
            )
            if cur.rowcount == 0:
                raise NotFound(f"no receptacle with id {receptacle.id}")

    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]:
        rows = self._db.conn.execute(
            "SELECT * FROM receptacles WHERE state = ?", (state.value,)
        ).fetchall()
        return [_row_to_receptacle(r) for r in rows]

    def list_non_generated(self) -> list[Receptacle]:
        rows = self._db.conn.execute("SELECT * FROM receptacles WHERE is_generated = 0").fetchall()
        return [_row_to_receptacle(r) for r in rows]


# --- treasures ---


class SQLiteTreasureRepository(TreasureRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def get_all(self) -> list[Treasure]:
        rows = self._db.conn.execute("SELECT * FROM treasures ORDER BY slot").fetchall()
        return [
            Treasure(
                id=r["id"],
                slot=r["slot"],
                receptacle_ids=json.loads(r["receptacle_ids"]),
                pity={ReceptacleRarity[k]: v for k, v in json.loads(r["pity"]).items()},
                created_at=_dt_in(r["created_at"]),
                price=r["price"],
            )
            for r in rows
        ]

    def save(self, treasure: Treasure) -> None:
        with self._db.write() as conn:
            conn.execute(
                "INSERT INTO treasures (id, slot, receptacle_ids, pity, created_at, price)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET slot = excluded.slot,"
                " receptacle_ids = excluded.receptacle_ids, pity = excluded.pity,"
                " created_at = excluded.created_at, price = excluded.price",
                (
                    treasure.id,
                    treasure.slot,
                    json.dumps(list(treasure.receptacle_ids)),
                    json.dumps({k.name: v for k, v in treasure.pity.items()}),
                    _dt_out(treasure.created_at),
                    treasure.price,
                ),
            )

    def delete(self, treasure_id: str) -> None:
        with self._db.write() as conn:
            conn.execute("DELETE FROM treasures WHERE id = ?", (treasure_id,))


# --- friend links ---


class SQLiteFriendLinkRepository(FriendLinkRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def add(self, name: str) -> FriendLink:
        created_at = datetime.now(timezone.utc)
        with self._db.write() as conn:
            existing = conn.execute("SELECT 1 FROM friend_links WHERE name = ?", (name,)).fetchone()
            if existing is not None:
                raise AlreadyExists(f"friend link {name!r} already exists")
            conn.execute(
                "INSERT INTO friend_links (name, created_at) VALUES (?, ?)",
                (name, _dt_out(created_at)),
            )
        return FriendLink(name=name, created_at=created_at)

    def get(self, name: str) -> FriendLink | None:
        row = self._db.conn.execute("SELECT * FROM friend_links WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return FriendLink(name=row["name"], created_at=_dt_in(row["created_at"]))

    def list_all(self) -> list[FriendLink]:
        rows = self._db.conn.execute("SELECT * FROM friend_links ORDER BY created_at").fetchall()
        return [FriendLink(name=r["name"], created_at=_dt_in(r["created_at"])) for r in rows]


# --- meta ---

_LAST_DISCARD_KEY = "last_discard_date"


class SQLiteMetaRepository(MetaRepository):
    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    def get_last_discard_date(self) -> date | None:
        row = self._db.conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_LAST_DISCARD_KEY,)
        ).fetchone()
        if row is None:
            return None
        return date.fromisoformat(row["value"])

    def set_last_discard_date(self, d: date) -> None:
        with self._db.write() as conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (_LAST_DISCARD_KEY, d.isoformat()),
            )
