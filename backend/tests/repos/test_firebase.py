"""Live Firestore contract tests — reuse the same contracts as the memory backend.

Skipped entirely unless FIREBASE_CREDENTIALS points at a real service account.
Each test gets its own randomly-named collection namespace so runs never
collide or leak into the real game data, and cleans up after itself.
"""

import os
import uuid

import pytest

from repos.firebase import (
    FirebaseCollectableRepository,
    FirebaseFriendLinkRepository,
    FirebaseMetaRepository,
    FirebaseReceptacleRepository,
    FirebaseTaskRepository,
    FirebaseTreasureRepository,
    FirebaseWalletRepository,
    get_firestore_client,
)
from tests.repos.contracts import (
    CollectableRepositoryContract,
    FriendLinkRepositoryContract,
    MetaRepositoryContract,
    ReceptacleRepositoryContract,
    TaskRepositoryContract,
    TreasureRepositoryContract,
    WalletRepositoryContract,
)

CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS", "")

pytestmark = pytest.mark.skipif(
    not CREDENTIALS_PATH,
    reason="FIREBASE_CREDENTIALS not set — skipping live Firestore contract tests",
)


def _namespace() -> str:
    return f"test_{uuid.uuid4().hex[:12]}_"


def _cleanup(db, namespace: str, collection_name: str) -> None:
    for doc in db.collection(f"{namespace}{collection_name}").stream():
        doc.reference.delete()


@pytest.fixture(scope="session")
def firestore_db():
    return get_firestore_client(CREDENTIALS_PATH)


class TestFirebaseTaskRepository(TaskRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseTaskRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "tasks")


class TestFirebaseCollectableRepository(CollectableRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseCollectableRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "collectables")


class TestFirebaseWalletRepository(WalletRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseWalletRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "wallet")


class TestFirebaseReceptacleRepository(ReceptacleRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseReceptacleRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "receptacles")


class TestFirebaseTreasureRepository(TreasureRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseTreasureRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "treasures")


class TestFirebaseFriendLinkRepository(FriendLinkRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseFriendLinkRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "friend_links")


class TestFirebaseMetaRepository(MetaRepositoryContract):
    @pytest.fixture
    def repo(self, firestore_db):
        namespace = _namespace()
        yield FirebaseMetaRepository(firestore_db, namespace=namespace)
        _cleanup(firestore_db, namespace, "meta")
