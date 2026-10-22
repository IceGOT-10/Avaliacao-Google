"""Utilitários para geração de tokens e identificadores públicos seguros."""

import secrets


def generate_link_code(nbytes: int = 6) -> str:
    """Gera um código aleatório não-sequencial para identificação pública do link."""
    return secrets.token_urlsafe(nbytes)