import time
from threading import Lock

from app.core.config import get_settings

SNOWFLAKE_EPOCH_MS = 1_704_067_200_000  # 2024-01-01T00:00:00Z
SNOWFLAKE_SEQUENCE_BITS = 12
SNOWFLAKE_WORKER_BITS = 10
SNOWFLAKE_MAX_SEQUENCE = (1 << SNOWFLAKE_SEQUENCE_BITS) - 1
SNOWFLAKE_MAX_WORKER_ID = (1 << SNOWFLAKE_WORKER_BITS) - 1
SNOWFLAKE_WORKER_SHIFT = SNOWFLAKE_SEQUENCE_BITS
SNOWFLAKE_TIMESTAMP_SHIFT = SNOWFLAKE_SEQUENCE_BITS + SNOWFLAKE_WORKER_BITS
MIN_PLAUSIBLE_SNOWFLAKE_ID = 1 << 52


class SnowflakeGenerator:
    """Thread-safe 64-bit Snowflake ID generator for one configured worker."""

    def __init__(self, worker_id: int):
        if not 0 <= worker_id <= SNOWFLAKE_MAX_WORKER_ID:
            raise ValueError(f"worker_id must be between 0 and {SNOWFLAKE_MAX_WORKER_ID}")
        self.worker_id = worker_id
        self._last_timestamp = -1
        self._sequence = 0
        self._lock = Lock()

    def next_id(self) -> int:
        with self._lock:
            timestamp = time.time_ns() // 1_000_000
            if timestamp < SNOWFLAKE_EPOCH_MS:
                raise RuntimeError("system clock is earlier than the Snowflake epoch")
            if timestamp < self._last_timestamp:
                timestamp = self._last_timestamp

            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & SNOWFLAKE_MAX_SEQUENCE
                if self._sequence == 0:
                    timestamp = self._wait_next_millisecond(self._last_timestamp)
            else:
                self._sequence = 0

            self._last_timestamp = timestamp
            return (
                ((timestamp - SNOWFLAKE_EPOCH_MS) << SNOWFLAKE_TIMESTAMP_SHIFT)
                | (self.worker_id << SNOWFLAKE_WORKER_SHIFT)
                | self._sequence
            )

    @staticmethod
    def _wait_next_millisecond(last_timestamp: int) -> int:
        timestamp = time.time_ns() // 1_000_000
        while timestamp <= last_timestamp:
            timestamp = time.time_ns() // 1_000_000
        return timestamp


_generator: SnowflakeGenerator | None = None
_generator_lock = Lock()


def generate_snowflake_id() -> int:
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                _generator = SnowflakeGenerator(get_settings().snowflake_worker_id)
    return _generator.next_id()
