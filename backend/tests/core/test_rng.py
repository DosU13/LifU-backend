from core.rng import Rng, SeededRng, SystemRng


def test_system_and_seeded_rng_satisfy_the_rng_protocol():
    assert isinstance(SystemRng(), Rng)
    assert isinstance(SeededRng(1), Rng)


def test_seeded_rng_is_deterministic():
    a = SeededRng(42)
    b = SeededRng(42)
    seq_a = [a.random() for _ in range(10)]
    seq_b = [b.random() for _ in range(10)]
    assert seq_a == seq_b

    a2 = SeededRng(42)
    b2 = SeededRng(42)
    assert [a2.randint(1, 100) for _ in range(10)] == [b2.randint(1, 100) for _ in range(10)]
    assert a2.choice(["x", "y", "z"]) == b2.choice(["x", "y", "z"])


def test_different_seeds_diverge():
    a = SeededRng(1)
    b = SeededRng(2)
    assert [a.random() for _ in range(20)] != [b.random() for _ in range(20)]


def test_randint_and_choice_stay_in_range():
    rng = SeededRng(7)
    for _ in range(50):
        n = rng.randint(5, 10)
        assert 5 <= n <= 10
    seq = [1, 2, 3]
    for _ in range(20):
        assert rng.choice(seq) in seq


def test_shuffle_preserves_elements():
    rng = SeededRng(3)
    items = [1, 2, 3, 4, 5]
    shuffled = list(items)
    rng.shuffle(shuffled)
    assert sorted(shuffled) == items


def test_system_rng_produces_valid_values():
    rng = SystemRng()
    assert 0.0 <= rng.random() < 1.0
    assert 1 <= rng.randint(1, 5) <= 5
    assert rng.choice([1, 2, 3]) in (1, 2, 3)
