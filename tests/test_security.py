"""Testes unitários para o módulo de segurança e hashing (app/core/security.py)."""

import pytest

from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    validate_password_policy,
    verify_password,
)


def test_password_policy_validation():
    """Valida a política de senhas (12 a 128 caracteres, sem regras de composição)."""
    # Menor que 12
    valid, err = validate_password_policy("curta123456")
    assert valid is False
    assert "no mínimo 12" in err

    # Maior que 128
    valid, err = validate_password_policy("a" * 129)
    assert valid is False
    assert "no máximo 128" in err

    # Limite inferior válido (12)
    valid, err = validate_password_policy("senhaexata12")
    assert valid is True
    assert err is None

    # Limite superior válido (128)
    valid, err = validate_password_policy("a" * 128)
    assert valid is True
    assert err is None


def test_hash_password_and_verify():
    """Garante que o hashing Argon2id é determinístico na verificação e não expõe a senha."""
    plain = "minha_senha_super_segura_123"
    h = hash_password(plain)

    # O hash não contém a senha em texto claro
    assert plain not in h
    assert h.startswith("$argon2id$")

    # Verificação correta
    assert verify_password(h, plain) is True

    # Senha incorreta retorna False e nunca levanta exceção
    assert verify_password(h, "senha_errada_com_tamanho_suficiente") is False
    assert verify_password(h, "") is False
    assert verify_password("", plain) is False
    assert verify_password("hash_invalido_corrompido", plain) is False


def test_needs_rehash_on_fresh_hash():
    """Um hash recém-gerado com os parâmetros padrão não deve requerer re-hash."""
    h = hash_password("senha_valida_12345")
    assert needs_rehash(h) is False


def test_session_token_generation_and_hashing():
    """Valida geração de tokens de 32 bytes e hashing SHA-256 (64 hex)."""
    t1 = generate_session_token()
    t2 = generate_session_token()

    assert t1 != t2
    assert len(t1) >= 40  # URL-safe de 32 bytes tem pelo menos 43 caracteres

    h1 = hash_session_token(t1)
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)
