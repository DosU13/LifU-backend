import pytest

from repos.memory import (
    MemoryCollectableRepository,
    MemoryFriendLinkRepository,
    MemoryMetaRepository,
    MemoryReceptacleRepository,
    MemoryTaskRepository,
    MemoryTreasureRepository,
    MemoryWalletRepository,
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


class TestMemoryTaskRepository(TaskRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryTaskRepository()


class TestMemoryCollectableRepository(CollectableRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryCollectableRepository()


class TestMemoryWalletRepository(WalletRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryWalletRepository()


class TestMemoryReceptacleRepository(ReceptacleRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryReceptacleRepository()


class TestMemoryTreasureRepository(TreasureRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryTreasureRepository()


class TestMemoryFriendLinkRepository(FriendLinkRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryFriendLinkRepository()


class TestMemoryMetaRepository(MetaRepositoryContract):
    @pytest.fixture
    def repo(self):
        return MemoryMetaRepository()
