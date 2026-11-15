from app.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_max_attempts_then_blocks():
    limiter = RateLimiter(max_attempts=3, window_seconds=60, clock=FakeClock())
    assert [limiter.hit("1.2.3.4") for _ in range(4)] == [True, True, True, False]


def test_keys_are_independent():
    limiter = RateLimiter(max_attempts=1, window_seconds=60, clock=FakeClock())
    assert limiter.hit("a") and limiter.hit("b")
    assert not limiter.hit("a")


def test_window_slides():
    clock = FakeClock()
    limiter = RateLimiter(max_attempts=2, window_seconds=60, clock=clock)
    limiter.hit("ip")
    clock.now = 30
    limiter.hit("ip")
    assert not limiter.hit("ip")
    clock.now = 60  # el primer intento sale de la ventana
    assert limiter.hit("ip")
    assert not limiter.hit("ip")
