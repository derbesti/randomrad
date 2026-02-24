import pytest
import randomrad as rr


def test_public_api_exports():
    # Required subset
    required = [
        "random",
        "randbytes",
        "randrange",
        "randint",
        "choice",
        "choices",
        "shuffle",
        "sample",
        "get_bytes",
        "NotEnoughEntropy",
    ]
    for name in required:
        assert hasattr(rr, name), f"missing export: {name}"


def test_no_seed_or_systemrandom_exposed():
    # We do not want to drift toward seed/reproducibility concepts
    forbidden = ["seed", "SystemRandom", "Random"]
    for name in forbidden:
        assert not hasattr(rr, name)


def test_randbytes_length():
    b = rr.randbytes(64)
    assert isinstance(b, (bytes, bytearray))
    assert len(b) == 64


def test_random_bounds():
    for _ in range(2000):
        x = rr.random()
        assert 0.0 <= x < 1.0


@pytest.mark.parametrize("a,b", [(0, 0), (0, 1), (-5, 5), (10, 20)])
def test_randint_range(a, b):
    for _ in range(2000):
        x = rr.randint(a, b)
        assert a <= x <= b


def test_randrange_forms():
    # randrange(stop)
    for _ in range(1000):
        x = rr.randrange(10)
        assert 0 <= x < 10

    # randrange(start, stop)
    for _ in range(1000):
        x = rr.randrange(10, 20)
        assert 10 <= x < 20


def test_randrange_step():
    for _ in range(1000):
        x = rr.randrange(1, 20, 3)
        assert 1 <= x < 20
        assert (x - 1) % 3 == 0


def test_choice_and_errors():
    data = [1, 2, 3, 4]
    for _ in range(500):
        assert rr.choice(data) in data

    with pytest.raises(IndexError):
        rr.choice([])


def test_choices_k_default_and_len():
    data = [1, 2, 3]
    assert len(rr.choices(data)) == 1
    assert len(rr.choices(data, 5)) == 5

    with pytest.raises(ValueError):
        rr.choices(data, -1)


def test_sample_default_and_unique():
    data = list(range(10))
    out = rr.sample(data)  # default k=1
    assert len(out) == 1
    out2 = rr.sample(data, 5)
    assert len(out2) == 5
    assert len(set(out2)) == 5

    with pytest.raises(ValueError):
        rr.sample(data, 11)


def test_shuffle_preserves_elements():
    data = [1, 2, 2, 3, 4, 4, 5]
    rr.shuffle(data)
    assert sorted(data) == [1, 2, 2, 3, 4, 4, 5]