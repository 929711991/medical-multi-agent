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
    """为单个工作节点提供线程安全的 64 位雪花 ID。"""

    def __init__(self, worker_id: int):
        """使用 10 位范围内的工作节点编号初始化生成器状态。"""
        if not 0 <= worker_id <= SNOWFLAKE_MAX_WORKER_ID:
            raise ValueError(f"worker_id must be between 0 and {SNOWFLAKE_MAX_WORKER_ID}")
        self.worker_id = worker_id
        self._last_timestamp = -1
        self._sequence = 0
        self._lock = Lock()

    def next_id(self) -> int:
        """生成当前工作节点内单调递增且唯一的雪花 ID。"""
        with self._lock:
            timestamp = time.time_ns() // 1_000_000
            if timestamp < SNOWFLAKE_EPOCH_MS:
                raise RuntimeError("system clock is earlier than the Snowflake epoch")
            if timestamp < self._last_timestamp:
                # 遇到短暂时钟回拨时沿用上次毫秒值，并通过序列位继续保证唯一性。
                timestamp = self._last_timestamp

            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & SNOWFLAKE_MAX_SEQUENCE
                if self._sequence == 0:
                    # 当前毫秒内的 4096 个序列号已用完，等待时间戳进入下一毫秒。
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
        """等待系统毫秒值超过上一次生成 ID 时使用的时间。"""
        timestamp = time.time_ns() // 1_000_000
        while timestamp <= last_timestamp:
            timestamp = time.time_ns() // 1_000_000
        return timestamp


_generator: SnowflakeGenerator | None = None
_generator_lock = Lock()


def generate_snowflake_id() -> int:
    """使用 `.env` 配置的进程级工作节点生成雪花 ID。"""
    global _generator
    # 双重检查锁既避免每次插入都获取初始化锁，也防止首次并发调用创建多个生成器。
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                _generator = SnowflakeGenerator(get_settings().snowflake_worker_id)
    return _generator.next_id()
