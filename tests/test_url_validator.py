"""Testes unitários rigorosos para o validador anti-open-redirect (validate_destination_url)."""

import pytest

from app.services.url_validator import validate_destination_url


@pytest.mark.parametrize(
    "valid_url",
    [
        "https://g.page/r/Cb_8Kxyz123",
        "https://g.page/r/padaria-central",
        "https://g.page:443/r/padaria-central",
        "https://search.google.com/local/writereview?placeid=ChIJN1t_tDeuEmsRUsoyG83frY4",
        "https://search.google.com/local/writereview?placeid=ChIJ123&hl=pt-BR",
        "https://maps.app.goo.gl/3wJxyzABC123",
        "https://maps.app.goo.gl/k982736412",
        "https://www.google.com/maps/place/Restaurante+Exemplo/@-23.55,-46.63,17z",
        "https://www.google.com/maps/reviews/@-23.55,-46.63",
        "https://google.com/maps/place/Loja+Central",
        "https://google.com/maps?cid=1234567890",
        "https://search.google.com/local/writereview?placeid=123#overview",
    ],
)
def test_validate_destination_url_valid_cases(valid_url: str):
    """Garante que URLs legítimas de cada domínio da allowlist são aceitas."""
    assert validate_destination_url(valid_url) is True


@pytest.mark.parametrize(
    ("invalid_url", "reason"),
    [
        # Tipos nulos, vazios ou não-strings
        (None, "None"),
        ("", "string vazia"),
        ("   ", "somente espaços"),
        (12345, "inteiro"),
        # Comprimento excessivo
        ("https://g.page/r/" + "a" * 2050, "URL maior que 2048 caracteres"),
        # Esquemas inválidos
        ("http://g.page/r/123", "HTTP inseguro não permitido"),
        ("ftp://g.page/r/123", "FTP"),
        ("javascript:alert(1)", "JavaScript pseudo-protocol"),
        ("data:text/html;base64,PHNjcmlwdD4=", "Data URL"),
        ("//g.page/r/123", "Protocol-relative sem esquema"),
        # Domínios fora da allowlist / tentativas de bypass de hostname
        ("https://google.com.evil.com/maps", "Sufixo de domínio malicioso"),
        ("https://evil.com/google.com/maps", "Domínio malicioso com path enganoso"),
        ("https://notgoogle.com/maps", "Domínio não autorizado"),
        ("https://search.google.com.attacker.com/local/writereview", "Subdomínio em atacante"),
        ("https://sub.g.page/r/123", "Subdomínio não autorizado"),
        ("https://evil.example/x", "Host genérico externo"),
        ("https://bing.com", "Buscador concorrente"),
        # goo.gl removido por não constar na documentação oficial atual
        ("https://goo.gl/maps/9zKxyzABC", "goo.gl não permitido na allowlist oficial"),
        ("https://goo.gl/notmaps", "goo.gl sem /maps"),
        # Userinfo / credenciais em URL
        ("https://g.page@evil.com/r/123", "Userinfo fingindo domínio"),
        ("https://user:password@search.google.com/local/writereview", "Userinfo com senha"),
        ("https://google.com:secret@google.com/maps", "Userinfo com porta falsa"),
        # Portas não padrão
        ("https://g.page:8080/r/123", "Porta 8080"),
        ("https://search.google.com:8443/local/writereview", "Porta 8443"),
        ("https://google.com:80/maps", "Porta 80 sobre HTTPS"),
        ("https://maps.app.goo.gl:3000/xyz", "Porta 3000"),
        # Caracteres de controle e backslashes
        (r"https://g.page/r/\evil.com", "Backslash na URL"),
        ("https://g.page/r/teste\r\n", "CRLF injection"),
        (r"https://search.google.com\evil.com", "Backslash após autoridade"),
        ("https://g.page/r/test" + chr(0) + "null", "Null byte"),
        # Duplo encoding
        ("https://g.page/r/%252f", "Duplo encoding %25"),
        ("https://g.page/r/%5c", "Duplo encoding backslash %5c"),
        ("https://google.com/maps%25", "Sinal de porcentagem duplo"),
        # IP literals
        ("https://127.0.0.1/maps", "IPv4 localhost"),
        ("https://192.168.0.1/maps", "IPv4 privado"),
        ("https://8.8.8.8/maps", "IPv4 público"),
        ("https://[::1]/maps", "IPv6 loopback"),
        # Restrições de path por domínio
        ("https://search.google.com/search?q=test", "search.google.com sem /local/writereview"),
        ("https://search.google.com/", "search.google.com raiz"),
        ("https://www.google.com/search?q=reviews", "www.google.com sem /maps"),
        ("https://www.google.com/", "www.google.com raiz"),
        ("https://google.com/doodles", "google.com sem /maps"),
        # Homógrafos e punycode
        ("https://gооgle.com/maps", "Homógrafo com caracteres cirílicos"),
        ("https://xn--gogle-1qa.com/maps", "Punycode de homógrafo"),
        ("https://g.pаge/r/test", "Homógrafo no domínio g.page"),
    ],
)
def test_validate_destination_url_invalid_cases(invalid_url, reason: str):
    """Garante que qualquer tentativa de bypass, esquema inseguro ou formato anômalo é rejeitada."""
    assert validate_destination_url(invalid_url) is False, f"Falha ao rejeitar: {reason}"
