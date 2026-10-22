"""Limitador de tentativas de login em memória por email normalizado.

Nota arquitetural:
Esta proteção é estritamente em memória por processo (single-process in-memory).
Múltiplos workers independentes mantêm contadores locais. O rate limiting distribuído
e global completo (via Redis / SlowAPI) está planejado para a Fase 7.
"""

import threading
import time
from collections.abc import Callable


class LoginRateLimiter:
    """Controlador de taxa de tentativas falhas de autenticação com relógio injetável."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        time_func: Callable[[], float] | None = None,
        max_keys: int = 10_000,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._time_func = time_func or time.time
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}

    def _get_now(self) -> float:
        return self._time_func()

    def _normalize(self, email: str | None) -> str:
        if not email or not isinstance(email, str):
            return ""
        return email.strip().lower()

    def is_blocked(self, email: str) -> tuple[bool, int]:
        """Verifica se o email excedeu o limite de falhas na janela temporal.

        Retorna (bloqueado: bool, segundos_restantes: int).
        """
        key = self._normalize(email)
        if not key:
            return False, 0

        now = self._get_now()
        threshold = now - self.window_seconds

        with self._lock:
            attempts = self._failures.get(key, [])
            # Purga tentativas fora da janela atual
            valid_attempts = [ts for ts in attempts if ts > threshold]
            if valid_attempts:
                self._failures[key] = valid_attempts
            else:
                self._failures.pop(key, None)

            if len(valid_attempts) >= self.max_attempts:
                oldest_in_window = valid_attempts[0]
                remaining_seconds = max(1, int(self.window_seconds - (now - oldest_in_window)))
                return True, remaining_seconds

            return False, 0

    def record_failure(self, email: str) -> None:
        """Registra uma falha de autenticação para o email fornecido."""
        key = self._normalize(email)
        if not key:
            return

        now = self._get_now()
        threshold = now - self.window_seconds

        with self._lock:
            attempts = self._failures.get(key, [])
            valid_attempts = [ts for ts in attempts if ts > threshold]
            valid_attempts.append(now)
            self._failures[key] = valid_attempts
            if len(self._failures) > self.max_keys:
                oldest_key = min(self._failures, key=lambda item: self._failures[item][-1])
                self._failures.pop(oldest_key, None)

    def record_success(self, email: str) -> None:
        """Zera o histórico de falhas após uma autenticação bem-sucedida."""
        key = self._normalize(email)
        if not key:
            return

        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        """Limpa todo o estado do limitador (útil em testes)."""
        with self._lock:
            self._failures.clear()


# Instância global compartilhada na aplicação
def build_login_rate_limiter() -> LoginRateLimiter:
    from app.core.config import get_settings

    settings = get_settings()
    return LoginRateLimiter(
        max_attempts=settings.login_rate_limit_max_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )


global_login_rate_limiter = build_login_rate_limiter()
