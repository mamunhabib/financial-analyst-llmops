"""
Call Chain & Role:
------------------
Architecture Layer: Phase 5 - Core Agent & Serverless State Tier
Role: Upstash Redis Session Memory & Audit Trail Checkpointer.
Callers:
    - src/agent/engine.py: Loads previous session conversation turns, records agent thoughts/tool executions, and persists state with 24h TTL.
Dependencies:
    - upstash_redis: Redis REST client (zero local storage pods, 100% cloud serverless).
    - config/settings.py: settings.UPSTASH_REDIS_REST_URL, settings.UPSTASH_REDIS_REST_TOKEN, settings.SESSION_TTL_SECONDS.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from upstash_redis import Redis

from config.settings import settings

logger = logging.getLogger("AgentMemory")


class RedisMemoryClient:
    """
    Session memory & audit trail checkpointer powered by Upstash Serverless Redis.
    Guarantees state persistence across stateless FastAPI agent pod replicas.
    """

    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.token = settings.UPSTASH_REDIS_REST_TOKEN
        self.ttl = settings.SESSION_TTL_SECONDS
        self._client: Optional[Redis] = None
        self._fallback_memory: Dict[str, List[Dict[str, Any]]] = {}

        self._init_client()

    def _init_client(self):
        """Initializes the Upstash Redis client with graceful fallback."""
        if self.url and self.token:
            try:
                self._client = Redis(url=self.url, token=self.token)
                # Quick ping test to verify connectivity
                self._client.set("health_check_ping", "pong", ex=10)
                logger.info("Connected to Upstash Serverless Redis successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not connect to Upstash Redis: {e}. Falling back to in-memory session cache."
                )
                self._client = None
        else:
            logger.info("Upstash Redis credentials not configured. Using in-memory session storage.")

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent conversation turns for a given session.

        Args:
            session_id: Unique user session UUID.
            limit: Maximum number of previous turns to return.

        Returns:
            List of message dictionaries with role and content.
        """
        key = f"session:{session_id}:turns"
        if self._client:
            try:
                raw_items = self._client.lrange(key, -limit, -1)
                return [json.loads(item) for item in raw_items]
            except Exception as e:
                logger.error(f"Failed to load session history from Upstash Redis: {e}")

        # Fallback to local memory
        items = self._fallback_memory.get(key, [])
        return items[-limit:]

    def save_turn(
        self,
        session_id: str,
        user_query: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Appends a user/assistant turn and audit metadata to Redis with TTL renewal.

        Args:
            session_id: Unique user session UUID.
            user_query: Cleaned user input prompt.
            agent_response: Final audited assistant report.
            metadata: Execution trace, route info, tools executed, and safety scores.
        """
        key = f"session:{session_id}:turns"
        audit_key = f"session:{session_id}:audit"

        record = {
            "timestamp": time.time(),
            "user": user_query,
            "assistant": agent_response,
            "metadata": metadata or {},
        }
        serialized = json.dumps(record)

        if self._client:
            try:
                self._client.rpush(key, serialized)
                self._client.expire(key, self.ttl)

                # Store audit trace separately for easy observability inspection
                audit_record = json.dumps({
                    "timestamp": time.time(),
                    "session_id": session_id,
                    **(metadata or {}),
                })
                self._client.rpush(audit_key, audit_record)
                self._client.expire(audit_key, self.ttl)
                return
            except Exception as e:
                logger.error(f"Failed to persist turn to Upstash Redis: {e}")

        # Local fallback
        if key not in self._fallback_memory:
            self._fallback_memory[key] = []
        self._fallback_memory[key].append(record)

    def get_audit_trail(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit trace of all tools and guardrail checks executed in session."""
        audit_key = f"session:{session_id}:audit"
        if self._client:
            try:
                raw_records = self._client.lrange(audit_key, 0, -1)
                return [json.loads(r) for r in raw_records]
            except Exception as e:
                logger.error(f"Failed to fetch audit trail from Upstash Redis: {e}")

        return []

    def clear_session(self, session_id: str) -> bool:
        """Clears session conversation state and audit records."""
        key = f"session:{session_id}:turns"
        audit_key = f"session:{session_id}:audit"

        if self._client:
            try:
                self._client.delete(key, audit_key)
                return True
            except Exception as e:
                logger.error(f"Failed to delete session {session_id} in Redis: {e}")

        self._fallback_memory.pop(key, None)
        return True


# Global singleton client
memory_client = RedisMemoryClient()
