"""The SQLite repositories against the shared contract suite.

Unlike the Firebase bindings these need no credentials and hit no network, so
they run on every `pytest` invocation — the local backend is the one the owner
actually plays on, so it gets checked every time.
"""

import pytest

from repos.sqlite import (
    SQLiteCollectableRepository,
    SQLiteDatabase,
    SQLiteFriendLinkRepository,
    SQLiteMetaRepository,
    SQLiteReceptacleRepository,
    SQLiteTaskRepository,
    SQLiteTreasureRepository,
    SQLiteWalletRepository,
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


@pytest.fixture
def db(tmp_path):
    """A real file per test — exercises the same code path as the live game."""
    return SQLiteDatabase(str(tmp_path / "test.db"))


class TestSQLiteTaskRepository(TaskRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteTaskRepository(db)


class TestSQLiteCollectableRepository(CollectableRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteCollectableRepository(db)


class TestSQLiteWalletRepository(WalletRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteWalletRepository(db)


class TestSQLiteReceptacleRepository(ReceptacleRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteReceptacleRepository(db)


class TestSQLiteTreasureRepository(TreasureRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteTreasureRepository(db)


class TestSQLiteFriendLinkRepository(FriendLinkRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteFriendLinkRepository(db)


class TestSQLiteMetaRepository(MetaRepositoryContract):
    @pytest.fixture
    def repo(self, db):
        return SQLiteMetaRepository(db)


# --- behaviour specific to a real, persistent database ---


def test_data_survives_reopening_the_file(tmp_path):
    """The whole point of the backend: state outlives the process."""
    path = str(tmp_path / "persist.db")

    first = SQLiteDatabase(path)
    SQLiteWalletRepository(first).adjust(250)
    SQLiteFriendLinkRepository(first).add("alex")

    second = SQLiteDatabase(path)
    assert SQLiteWalletRepository(second).get_coins() == 250
    assert SQLiteFriendLinkRepository(second).get("alex") is not None


def test_schema_is_idempotent(tmp_path):
    """Opening an existing database must not wipe or fail on its tables."""
    path = str(tmp_path / "reopen.db")
    SQLiteWalletRepository(SQLiteDatabase(path)).adjust(7)
    for _ in range(3):
        assert SQLiteWalletRepository(SQLiteDatabase(path)).get_coins() == 7


def test_failed_adjust_rolls_back_every_counter(db):
    """A partial write here would silently invent or destroy collectables."""
    from core.enums import CollectableRarity, Element
    from core.errors import InsufficientCollectables

    repo = SQLiteCollectableRepository(db)
    repo.adjust({(Element.FIRE, CollectableRarity.FRAGMENT): 5})

    with pytest.raises(InsufficientCollectables):
        repo.adjust(
            {
                (Element.FIRE, CollectableRarity.FRAGMENT): -2,
                (Element.WATER, CollectableRarity.FRAGMENT): -1,  # nothing held
            }
        )

    stock = repo.get_all()
    assert stock[(Element.FIRE, CollectableRarity.FRAGMENT)] == 5
    assert stock[(Element.WATER, CollectableRarity.FRAGMENT)] == 0
