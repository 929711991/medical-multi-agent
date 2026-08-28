from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "医疗辅助多智能体 V1.2"
    api_prefix: str = "/api/v1"
    aliyun_llm_api_key: str | None = Field(default=None, repr=False)
    aliyun_llm_base_url: str = (
        "https://llm-gu39ltmv26zjb2y7.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )
    aliyun_llm_model: str = "qwen3.5-omni-plus-2026-03-15"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "medical"
    mysql_password: str = Field(default="change_me", repr=False)
    mysql_database: str = "medical_ai"
    mysql_graph_database: str = "medical_ai_graph"

    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    mcp_connect_timeout_seconds: float = 10.0

    rag_enabled: bool = True
    rag_required: bool = True
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str | None = Field(default="change_redis_me", repr=False)
    redis_database: int = 0
    redis_vector_index: str = "medical_knowledge_v1"
    redis_key_prefix: str = "medical:knowledge:chunk:"
    embedding_model: str | None = None
    embedding_base_url: str | None = None
    embedding_api_key: str | None = Field(default=None, repr=False)
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 10
    rag_top_k: int = 8
    rag_return_k: int = 5
    rag_score_threshold: float | None = None
    rag_chunk_size: int = 1600
    rag_chunk_overlap: int = 200

    model_call_limit: int = 8
    tool_call_limit: int = 20
    log_level: str = "INFO"
    auth_secret: str = Field(default="development-only-change-me", repr=False)
    login_account: str = "admin"
    login_doctor_id: int = 100000000000000001
    login_password: str = Field(default="111111", repr=False)
    auth_cookie_secure: bool = False
    auth_session_hours: int = 12
    wechat_app_id: str | None = None
    wechat_app_secret: str | None = Field(default=None, repr=False)
    h5_consumer_login_enabled: bool = False
    h5_consumer_account: str | None = None
    h5_consumer_password: str | None = Field(default=None, repr=False)
    consumer_auth_secret: str | None = Field(default=None, repr=False)
    consumer_token_hours: int = Field(default=168, ge=1, le=720)
    consumer_message_max_length: int = Field(default=4000, ge=100, le=20000)
    rate_limit_user_per_minute: int = Field(default=30, ge=1)
    rate_limit_ip_per_minute: int = Field(default=60, ge=1)
    rate_limit_consultation_per_minute: int = Field(default=20, ge=1)
    rate_limit_llm_per_hour: int = Field(default=20, ge=1)
    max_concurrent_ai_analyses: int = Field(default=2, ge=1, le=20)
    snowflake_worker_id: int = Field(default=1, ge=0, le=1023)

    def validate_consumer_auth(self) -> None:
        if not self.consumer_auth_secret:
            raise RuntimeError("CONSUMER_AUTH_SECRET_UNAVAILABLE")

    def validate_wechat(self) -> None:
        if not self.wechat_app_id or not self.wechat_app_secret:
            raise RuntimeError("WECHAT_CREDENTIALS_UNAVAILABLE")

    def validate_h5_consumer_login(self) -> None:
        """仅在明确开启且配置验收账号时允许 H5 登录。"""
        if (
            not self.h5_consumer_login_enabled
            or not self.h5_consumer_account
            or not self.h5_consumer_password
        ):
            raise RuntimeError("H5_CONSUMER_LOGIN_UNAVAILABLE")

    @property
    def database_url(self) -> str:
        """生成已转义密码的业务数据库 SQLAlchemy 地址。"""
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+asyncmy://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def checkpoint_url(self) -> str:
        """生成已转义密码的 LangGraph 检查点数据库地址。"""
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+asyncmy://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_graph_database}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        """生成向量检索使用的带认证 Redis 地址。"""
        password = f":{quote_plus(self.redis_password)}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_database}"

    def validate_llm(self) -> None:
        """真实大模型调用缺少凭据时抛出配置错误。"""
        if not self.aliyun_llm_api_key:
            raise RuntimeError("执行真实诊断流程必须配置 ALIYUN_LLM_API_KEY")

    def validate_rag(self) -> None:
        """校验当前运行模式所需的向量模型与 RAG 配置。"""
        if not self.rag_enabled:
            if self.rag_required:
                raise RuntimeError("RAG_REQUIRED=true 时不允许关闭 RAG")
            return
        if not self.embedding_model or not self.embedding_base_url or not self.embedding_api_key:
            raise RuntimeError(
                "启用正式 RAG 必须配置 EMBEDDING_MODEL、EMBEDDING_BASE_URL 和 EMBEDDING_API_KEY"
            )


@lru_cache
def get_settings() -> Settings:
    """加载并缓存由环境变量驱动的应用配置。"""
    return Settings()
