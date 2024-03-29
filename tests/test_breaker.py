from short_circuit.breaker import CircuitBreaker
import pytest
from time import sleep

from short_circuit.error import CircuitBreakerError


class TestBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker(max_failures=3, reset_timeout=1)
        assert cb.tripped is False
        assert cb.current_failures == 0

    def test_breaker_trips_when_failure_threshold_is_reached(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.1)

        @cb
        def foo():
            raise Exception()

        with pytest.raises(Exception):
            foo()

        assert cb.tripped == True

    def test_keeps_track_of_current_failure_on_exception(self):
        cb = CircuitBreaker(max_failures=3, reset_timeout=0.1)

        @cb
        def foo():
            raise Exception()

        # breaker won't raise the underlying Exception here since it's still under the max_failure threshold
        foo()

        # this code is reachable due to the circuitbreaker implementation, but pylance thinks it isn't, lol
        assert cb.current_failures == 1

    def test_raises_circuit_breaker_error_when_tripped(self):
        cb = CircuitBreaker(max_failures=3, reset_timeout=0.1)
        # Trip the breaker
        cb.tripped = True

        @cb
        def foo():
            return True

        with pytest.raises(CircuitBreakerError):
            foo()

    def test_circuit_breaker_successful_call__ok(self):
        cb = CircuitBreaker(max_failures=3, reset_timeout=0.1)

        @cb
        def foo():
            return "Successful call to underlying service made"

        result = foo()

        assert cb.tripped == False
        assert cb.current_failures == 0
        assert result == "Successful call to underlying service made"

    def test_circuit_breaker_switches_to_half_open_state_after_timeout_expires(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.01)

        @cb
        def foo():
            raise Exception

        with pytest.raises(Exception):
            foo()

        assert cb.tripped == True
        assert cb.current_failures == 1
        # sleep for longer than the reset_timeout to force half-open state
        sleep(0.02)
        assert cb.tripped == False
        # assert current_failures hasn't been reset in the half-open state
        assert cb.current_failures == 1

    def test_circuit_breaker_closes_after_successful_call_and_timeout_expiry(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout=0.1)

        @cb
        def foo():
            raise Exception

        with pytest.raises(Exception):
            foo()

        assert cb.tripped == True

        @cb
        def bar():
            return True

        with pytest.raises(CircuitBreakerError):
            bar()

        assert cb.current_failures > 0

        sleep(0.2)

        bar()
        # assert breaker is closed and has been reset
        assert cb.tripped == False
        assert cb.current_failures == 0
