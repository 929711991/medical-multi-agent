from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "医疗辅助多智能体 V1.1"
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
    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    milvus_collection: str = "medical_knowledge_v1"
    embedding_model: str | None = None
    embedding_base_url: str | None = None
    embedding_api_key: str | None = Field(default=None, repr=False)
    rag_top_k: int = 8
    rag_return_k: int = 5
    rag_score_threshold: float | None = None
    rag_chunk_size: int = 1600
    rag_chunk_overlap: int = 200

    model_call_limit: int = 8
    tool_call_limit: int = 20
    log_level: str = "INFO"
    auth_secret: str = Field(default="development-only-change-me", repr=False)
    demo_login_password: str = Field(default="demo-clinical", repr=False)
    auth_cookie_secure: bool = False
    auth_session_hours: int = 12

    @property
    def database_url(self) -> str:
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+asyncmy://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def checkpoint_url(self) -> str:
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+asyncmy://{self.mysql_user}:{password}@{self.mysql_host}:"
            f"{self.mysql_port}/{self.mysql_graph_database}?charset=utf8mb4"
        )

    @property
    def milvus_uri(self) -> str:
        return f"http://{self.milvus_host}:{self.milvus_port}"

    def validate_llm(self) -> None:
        if not self.aliyun_llm_api_key:
            raise RuntimeError("执行真实诊断流程必须配置 ALIYUN_LLM_API_KEY")

    def validate_rag(self) -> None:
        if not self.rag_enabled:
            if self.rag_required:
                raise RuntimeError("RAG_REQUIRED=true 时不允许关闭 RAG")
            return
        if not self.embedding_model or not self.embedding_api_key:
            raise RuntimeError("启用正式 RAG 必须配置 EMBEDDING_MODEL 和 EMBEDDING_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
