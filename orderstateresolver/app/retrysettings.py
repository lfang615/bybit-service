from tenacity import retry, stop_after_attempt, wait_fixed
from circuitbreaker import CircuitBreaker
import httpx

# Retries and circuit breakers decorators
redis_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30, expected_exception=Exception)
kafka_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30, expected_exception=Exception)
bybit_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30, expected_exception=[httpx.HTTPError])

retry_decorator = retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
