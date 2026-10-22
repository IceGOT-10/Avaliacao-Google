"""Testes unit?rios rigorosos para o validador anti-open-redirect (validate_destination_url)."""

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
        "https://goo.gl/maps/9zKxyzABC",
        "https://search.google.com/local/writereview?placeid=123#overview",
    ],
)
def test_validate_destination_url_valid_cases(valid_url: str):
    """Garante que URLs leg?timas de cada dom?nio da allowlist s?o aceitas."""
    assert validate_destination_url(valid_url) is True


@pytest.mark.parametrize(
    ("invalid_url", "reason"),
    [
        # Tipos nulos, vazios ou n?o-strings
        (None, "None"),
        ("", "string vazia"),
        ("   ", "somente espa?os"),
        (12345, "inteiro"),
        # Comprimento excessivo
        ("https://g.page/r/" + "a" * 2050, "URL maior que 2048 caracteres"),
        # Esquemas inv?lidos
        ("http://g.page/r/123", "HTTP inseguro n?o permitido"),
        ("ftp://g.page/r/123", "FTP"),
        ("javascript:alert(1)", "JavaScript pseudo-protocol"),
        ("data:text/html;base64,PHNjcmlwdD4=", "Data URL"),
        ("//g.page/r/123", "Protocol-relative sem esquema"),
        # Dom?nios fora da allowlist / tentativas de bypass de hostname
        ("https://google.com.evil.com/maps", "Sufixo de dom?nio malicioso"),
        ("https://evil.com/google.com/maps", "Dom?nio malicioso com path enganoso"),
        ("https://notgoogle.com/maps", "Dom?nio n?o autorizado"),
        ("https://search.google.com.attacker.com/local/writereview", "Subdom?nio em atacante"),
        ("https://sub.g.page/r/123", "Subdom?nio n?o autorizado"),
        ("https://evil.example/x", "Host gen?rico externo"),
        ("https://bing.com", "Buscador concorrente"),
        # Userinfo / credenciais em URL
        ("https://g.page@evil.com/r/123", "Userinfo fingindo dom?nio"),
        ("https://user:password@search.google.com/local/writereview", "Userinfo com senha"),
        ("https://google.com:secret@google.com/maps", "Userinfo com porta falsa"),
        # Portas n?o padr?o
        ("https://g.page:8080/r/123", "Porta 8080"),
        ("https://search.google.com:8443/local/writereview", "Porta 8443"),
        ("https://google.com:80/maps", "Porta 80 sobre HTTPS"),
        ("https://maps.app.goo.gl:3000/xyz", "Porta 3000"),
        # Caracteres de controle e backslashes
        ("https://g.page/r/\\evil.com", "Backslash na URL"),
        ("https://g.page/r/teste\r\n", "CRLF injection"),
        ("https://search.google.com\\evil.com", "Backslash ap?s autoridade"),
        ("https://g.page/r/test" + chr(0) + "null", "Null byte"),
        # Duplo encoding
        ("https://g.page/r/%252f", "Duplo encoding %25"),
        ("https://g.page/r/%5c", "Duplo encoding backslash %5c"),
        ("https://google.com/maps%25", "Sinal de porcentagem duplo"),
        # IP literals
        ("https://127.0.0.1/maps", "IPv4 localhost"),
        ("https://192.168.0.1/maps", "IPv4 privado"),
        ("https://8.8.8.8/maps", "IPv4 p?blico"),
        ("https://[::1]/maps", "IPv6 loopback"),
        # Restri??es de path por dom?nio
        ("https://search.google.com/search?q=test", "search.google.com sem /local/writereview"),
        ("https://search.google.com/", "search.google.com raiz"),
        ("https://www.google.com/search?q=reviews", "www.google.com sem /maps"),
        ("https://www.google.com/", "www.google.com raiz"),
        ("https://google.com/doodles", "google.com sem /maps"),
        ("https://goo.gl/notmaps", "goo.gl sem /maps"),
        # Hom?grafos e punycode
        ("https://g??gle.com/maps", "Hom?grafo com caracteres cir?licos"),
        ("https://xn--gogle-1qa.com/maps", "Punycode de hom?grafo"),
        ("https://g.p?ge/r/test", "Hom?grafo no dom?nio g.page"),
    ],
)
def test_validate_destination_url_invalid_cases(invalid_url, reason: str):
    """Garante que qualquer tentativa de bypass, esquema inseguro ou formato an?malo ? rejeitada."""
    assert validate_destination_url(invalid_url) is False, f"Falha ao rejeitar: {reason}"
