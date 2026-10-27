from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Configuration for Financial Analyst Agent.
    Supports local .env loading and Kubernetes environment variable injection.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Environment & Service Endpoints
    # --------------------------------------------------------------------------
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    APP_NAME: str = "Financial & Market Analyst Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False)

    # Microservice Port Allocations (Internal container ports)
    STREAMLIT_PORT: int = Field(default=8501, description="Streamlit UI container port")
    AGENT_PORT: int = Field(default=8000, description="FastAPI Agent container port")
    MARKET_GATEWAY_PORT: int = Field(default=8004, description="Market Gateway container port")

    # Service-to-Service URLs (defaults for local dev, overridden in K8s)
    MARKET_GATEWAY_URL: str = Field(
        default="http://localhost:8004",
        description="Market Gateway microservice URL"
    )
    AGENT_SERVICE_URL: str = Field(
        default="http://localhost:8000",
        description="FastAPI Agent Ingress URL"
    )

    # --------------------------------------------------------------------------
    # Cloud LLM & Shield Providers (100% Free APIs)
    # --------------------------------------------------------------------------
    # Groq Cloud LPU
    GROQ_API_KEY: str = Field(default="", description="Groq Cloud API Key")
    GROQ_REASONING_MODEL: str = Field(
        default="qwen/qwen3.8-27b",
        description="Qwen 27B on Groq LPU for ReAct reasoning & tool synthesis"
    )
    GROQ_ROUTER_MODEL: str = Field(
        default="qwen/qwen3.8-27b",
        description="Qwen 27B on Groq LPU for sub-150ms query intent classification"
    )
    GROQ_GUARD_MODEL: str = Field(
        default="llama-guard-3-8b",
        description="Llama Guard 3 8B for output safety & factual audit"
    )

    # Hugging Face Serverless
    HF_TOKEN: str = Field(default="", description="Hugging Face API Token")
    HF_SHIELD_MODEL: str = Field(
        default="meta-llama/Prompt-Guard-86M",
        description="Prompt Guard 86M for prompt injection & jailbreak detection"
    )
    HF_EMBEDDING_MODEL: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="384-dimensional dense embedding model for SEC 10-K RAG"
    )

    # --------------------------------------------------------------------------
    # Upstash Serverless Data Platform (Dual Purpose)
    # --------------------------------------------------------------------------
    # 1. Upstash Redis (Session Context, ReAct Checkpoints & Security Audit Logs)
    UPSTASH_REDIS_REST_URL: str = Field(default="", description="Upstash Redis REST URL")
    UPSTASH_REDIS_REST_TOKEN: str = Field(default="", description="Upstash Redis REST Token")
    SESSION_TTL_SECONDS: int = Field(default=86400, description="24-hour TTL for session state")

    # 2. Upstash Vector (SEC 10-K RAG Knowledge Base)
    UPSTASH_VECTOR_REST_URL: str = Field(default="", description="Upstash Vector Index REST URL")
    UPSTASH_VECTOR_REST_TOKEN: str = Field(default="", description="Upstash Vector Index REST Token")
    VECTOR_TOP_K: int = Field(default=4, description="Top-k SEC 10-K chunks to retrieve")

    # --------------------------------------------------------------------------
    # Observability & LLMOps Quality Gate (Langfuse)
    # --------------------------------------------------------------------------
    LANGFUSE_PUBLIC_KEY: str = Field(default="", description="Langfuse Public Key")
    LANGFUSE_SECRET_KEY: str = Field(default="", description="Langfuse Secret Key")
    LANGFUSE_HOST: str = Field(
        default="http://localhost:8092",
        description="Langfuse Server URL (LoadBalancer port :8092)"
    )
    DEEPEVAL_THRESHOLD: float = Field(
        default=0.90,
        description="Minimum score threshold for CI/CD DeepEval quality gate"
    )

    # --------------------------------------------------------------------------
    # Agent Guardrails & Runtime Thresholds
    # --------------------------------------------------------------------------
    MAX_REACT_LOOPS: int = Field(default=5, description="Max Thought-Action-Observation loops")
    INJECTION_THRESHOLD: float = Field(default=0.85, description="Prompt Guard injection rejection score")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, description="Client HTTP timeout")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


# Global instance for clean import across modules: from config.settings import settings
settings = get_settings()
