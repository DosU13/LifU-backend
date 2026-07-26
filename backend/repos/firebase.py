import threading
from datetime import date, datetime, timezone

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as fa_firestore
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from core.entities import (
    CollectableStock,
    FriendLink,
    GeneratedContent,
    Receptacle,
    Task,
    Treasure,
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

_app: firebase_admin.App | None = None
_app_lock = threading.Lock()


def get_firestore_client(credentials_path: str) -> firestore.Client:
    """Lazily initialize the (single, process-wide) Firebase app and return its Firestore client."""
    global _app
    with _app_lock:
        if _app is None:
            _app = firebase_admin.initialize_app(credentials.Certificate(credentials_path))
    return fa_firestore.client(_app)


def _stock_key(element: Element, rarity: CollectableRarity) -> str:
    return f"{element.value}_{rarity.name}"


def _task_to_doc(task: Task) -> dict:
    return {
        "text": task.text,
        "created_at": task.created_at,
        "value": task.value,
        "virtues": {k.value: v for k, v in task.virtues.items()},
        "fragments_awarded": {k.value: v for k, v in task.fragments_awarded.items()},
    }


def _doc_to_task(doc_id: str, data: dict) -> Task:
    return Task(
        id=doc_id,
        text=data["text"],
        created_at=data["created_at"],
        value=data["value"],
        virtues={TaskVirtue(k): v for k, v in data.get("virtues", {}).items()},
        fragments_awarded={Element(k): v for k, v in data.get("fragments_awarded", {}).items()},
    )


def _content_to_doc(content: GeneratedContent) -> dict:
    return {
        "kind": content.kind.value,
        "title": content.title,
        "url": content.url,
        "author": content.author,
        "text": content.text,
    }


def _doc_to_content(data: dict | None) -> GeneratedContent | None:
    if not data:
        return None
    return GeneratedContent(
        kind=GeneratedKind(data["kind"]),
        title=data["title"],
        url=data["url"],
        author=data["author"],
        text=data["text"],
    )


def _receptacle_to_doc(r: Receptacle) -> dict:
    return {
        "state": r.state.value,
        "virtue": r.virtue.value,
        "rarity": r.rarity.value,
        "value": r.value,
        "is_generated": r.is_generated,
        "is_secret": r.is_secret,
        "friend_name": r.friend_name,
        "reward_text": r.reward_text,
        "content": _content_to_doc(r.content) if r.content else None,
        "treasure_id": r.treasure_id,
        "created_at": r.created_at,
        "opened_at": r.opened_at,
    }


def _doc_to_receptacle(doc_id: str, data: dict) -> Receptacle:
    return Receptacle(
        id=doc_id,
        state=ReceptacleState(data["state"]),
        virtue=Virtue(data["virtue"]),
        rarity=ReceptacleRarity(data["rarity"]),
        value=data["value"],
        is_generated=data["is_generated"],
        is_secret=data["is_secret"],
        friend_name=data.get("friend_name"),
        reward_text=data.get("reward_text"),
        content=_doc_to_content(data.get("content")),
        treasure_id=data.get("treasure_id"),
        created_at=data["created_at"],
        opened_at=data.get("opened_at"),
    )


def _treasure_to_doc(t: Treasure) -> dict:
    return {
        "slot": t.slot,
        "receptacle_ids": list(t.receptacle_ids),
        "pity": {k.name: v for k, v in t.pity.items()},
        "created_at": t.created_at,
        "price": t.price,
    }


def _doc_to_treasure(doc_id: str, data: dict) -> Treasure:
    return Treasure(
        id=doc_id,
        slot=data["slot"],
        receptacle_ids=list(data.get("receptacle_ids", [])),
        pity={ReceptacleRarity[k]: v for k, v in data.get("pity", {}).items()},
        created_at=data["created_at"],
        price=data.get("price", 1),
    )


class FirebaseTaskRepository(TaskRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._collection = db.collection(f"{namespace}tasks")

    def add(self, task: Task) -> Task:
        data = _task_to_doc(task)
        if task.id:
            self._collection.document(task.id).set(data)
            doc_id = task.id
        else:
            _, doc_ref = self._collection.add(data)
            doc_id = doc_ref.id
        return _doc_to_task(doc_id, data)

    def list_since(self, since: datetime) -> list[Task]:
        query = self._collection.where(filter=FieldFilter("created_at", ">=", since)).order_by(
            "created_at"
        )
        return [_doc_to_task(doc.id, doc.to_dict()) for doc in query.stream()]


class FirebaseCollectableRepository(CollectableRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._db = db
        self._doc_ref = db.collection(f"{namespace}collectables").document("main")

    def get_all(self) -> CollectableStock:
        data = self._doc_ref.get().to_dict() or {}
        return {
            (e, r): data.get(_stock_key(e, r), 0) for e in Element for r in CollectableRarity
        }

    def adjust(self, deltas: dict[tuple[Element, CollectableRarity], int]) -> None:
        transaction = self._db.transaction()
        doc_ref = self._doc_ref

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> None:
            snapshot = doc_ref.get(transaction=transaction)
            proposed = dict(snapshot.to_dict() or {})
            for key, delta in deltas.items():
                stock_key = _stock_key(*key)
                proposed[stock_key] = proposed.get(stock_key, 0) + delta
            negative = sorted(k for k, v in proposed.items() if v < 0)
            if negative:
                raise InsufficientCollectables(f"insufficient stock for: {', '.join(negative)}")
            transaction.set(doc_ref, proposed)

        _run(transaction)


class FirebaseWalletRepository(WalletRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._db = db
        self._doc_ref = db.collection(f"{namespace}wallet").document("main")

    def get_coins(self) -> int:
        data = self._doc_ref.get().to_dict() or {}
        return data.get("coins", 0)

    def adjust(self, delta: int) -> int:
        transaction = self._db.transaction()
        doc_ref = self._doc_ref

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> int:
            snapshot = doc_ref.get(transaction=transaction)
            current = (snapshot.to_dict() or {}).get("coins", 0)
            new_balance = current + delta
            if new_balance < 0:
                raise InsufficientCoins(
                    f"cannot adjust coins by {delta}: balance would go negative"
                )
            transaction.set(doc_ref, {"coins": new_balance})
            return new_balance

        return _run(transaction)


class FirebaseReceptacleRepository(ReceptacleRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._collection = db.collection(f"{namespace}receptacles")

    def add(self, receptacle: Receptacle) -> Receptacle:
        data = _receptacle_to_doc(receptacle)
        if receptacle.id:
            self._collection.document(receptacle.id).set(data)
            doc_id = receptacle.id
        else:
            _, doc_ref = self._collection.add(data)
            doc_id = doc_ref.id
        return _doc_to_receptacle(doc_id, data)

    def get(self, receptacle_id: str) -> Receptacle:
        snapshot = self._collection.document(receptacle_id).get()
        if not snapshot.exists:
            raise NotFound(f"no receptacle with id {receptacle_id}")
        return _doc_to_receptacle(snapshot.id, snapshot.to_dict())

    def update(self, receptacle: Receptacle) -> None:
        doc_ref = self._collection.document(receptacle.id)
        if not doc_ref.get().exists:
            raise NotFound(f"no receptacle with id {receptacle.id}")
        doc_ref.set(_receptacle_to_doc(receptacle))

    def list_by_state(self, state: ReceptacleState) -> list[Receptacle]:
        query = self._collection.where(filter=FieldFilter("state", "==", state.value))
        return [_doc_to_receptacle(doc.id, doc.to_dict()) for doc in query.stream()]

    def list_non_generated(self) -> list[Receptacle]:
        query = self._collection.where(filter=FieldFilter("is_generated", "==", False))
        return [_doc_to_receptacle(doc.id, doc.to_dict()) for doc in query.stream()]


class FirebaseTreasureRepository(TreasureRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._collection = db.collection(f"{namespace}treasures")

    def get_all(self) -> list[Treasure]:
        return [_doc_to_treasure(doc.id, doc.to_dict()) for doc in self._collection.stream()]

    def save(self, treasure: Treasure) -> None:
        self._collection.document(treasure.id).set(_treasure_to_doc(treasure))

    def delete(self, treasure_id: str) -> None:
        self._collection.document(treasure_id).delete()


class FirebaseFriendLinkRepository(FriendLinkRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._db = db
        self._collection = db.collection(f"{namespace}friend_links")

    def add(self, name: str) -> FriendLink:
        transaction = self._db.transaction()
        doc_ref = self._collection.document(name)

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> datetime:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                raise AlreadyExists(f"friend link '{name}' already exists")
            created_at = datetime.now(timezone.utc)
            transaction.set(doc_ref, {"created_at": created_at})
            return created_at

        created_at = _run(transaction)
        return FriendLink(name=name, created_at=created_at)

    def get(self, name: str) -> FriendLink | None:
        snapshot = self._collection.document(name).get()
        if not snapshot.exists:
            return None
        return FriendLink(name=name, created_at=snapshot.to_dict()["created_at"])

    def list_all(self) -> list[FriendLink]:
        return [
            FriendLink(name=doc.id, created_at=doc.to_dict()["created_at"])
            for doc in self._collection.stream()
        ]


class FirebaseMetaRepository(MetaRepository):
    def __init__(self, db: firestore.Client, namespace: str = "") -> None:
        self._doc_ref = db.collection(f"{namespace}meta").document("main")

    def get_last_discard_date(self) -> date | None:
        data = self._doc_ref.get().to_dict() or {}
        value = data.get("last_discard_date")
        return date.fromisoformat(value) if value else None

    def set_last_discard_date(self, d: date) -> None:
        self._doc_ref.set({"last_discard_date": d.isoformat()})
