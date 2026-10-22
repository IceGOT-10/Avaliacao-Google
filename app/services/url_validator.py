"""Servi?o de valida??o de URL de destino para preven??o de Open Redirect.

Garante que URLs de redirecionamento perten?am estritamente aos dom?nios e caminhos
oficiais autorizados do Google Meu Neg?cio / Google Maps / Google Reviews.

Fonte oficial de refer?ncia:
https://support.google.com/business/answer/16816815?hl=pt-BR
(Criar um link ou QR code para pedir avalia??es - Ajuda do Perfil da empresa no Google)
"""

import ipaddress
from urllib.parse import urlsplit

# Comprimento m?ximo seguro para URLs
MAX_URL_LENGTH = 2048

# Allowlist de hostnames oficiais do Google autorizados para avalia??es
ALLOWED_GOOGLE_HOSTS: frozenset[str] = frozenset({
    "g.page",
    "search.google.com",
    "maps.app.goo.gl",
    "www.google.com",
    "google.com",
    "goo.gl",
})

# Restri??es de prefixo de caminho obrigat?rio por hostname
PATH_PREFIX_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "search.google.com": ("/local/writereview",),
    "www.google.com": ("/maps",),
    "google.com": ("/maps",),
    "goo.gl": ("/maps",),
}


def validate_destination_url(url: str | None) -> bool:
    r"""Valida estritamente se uma URL de destino pertence aos dom?nios do Google autorizados.

    Fun??o pura, estritamente determin?stica e sem I/O de rede.

    Regras de valida??o:
    - Esquema obrigatoriamente HTTPS.
    - Hostname existente, exato na allowlist oficial (sem subdom?nios arbitr?rios).
    - Proibi??o de credenciais / userinfo (ex.: user@host).
    - Proibi??o de portas n?o-padr?o (apenas 443 ou omitida).
    - Proibi??o de caracteres de controle, espa?os em branco e backslashes (\).
    - Proibi??o de endere?os IP literais (IPv4 e IPv6).
    - Proibi??o de hom?grafos / IDN / punycode.
    - Valida??o de prefixo de caminho para dom?nios gen?ricos (search.google.com, google.com).
    """
    if not url or not isinstance(url, str):
        return False

    # Rejeitar URLs com espa?os em branco extras (in?cio/fim) ou comprimento excessivo
    if url != url.strip() or len(url) > MAX_URL_LENGTH:
        return False

    # Rejeitar caracteres de controle ASCII, whitespace e backslash (bypasses comuns de parser)
    if any(ord(c) < 32 or ord(c) == 127 or c == "\\" for c in url):
        return False

    # Rejeitar tentativas com duplo encoding de separadores (ex.: %25, %2f, %5c)
    if "%25" in url.lower() or "%5c" in url.lower():
        return False

    try:
        parsed = urlsplit(url)
    except Exception:
        return False

    # 1. Esquema estritamente HTTPS
    if parsed.scheme.lower() != "https":
        return False

    # 2. Rejeitar presen?a de userinfo (ex: https://g.page@evil.com)
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        return False

    # 3. Porta: apenas omitida (None) ou explicitamente 443
    try:
        if parsed.port is not None and parsed.port != 443:
            return False
    except ValueError:
        return False

    # 4. Hostname
    hostname = parsed.hostname
    if not hostname:
        return False
    hostname = hostname.lower()

    # Rejeitar hom?grafos Unicode e punycode (todos os dom?nios Google autorizados s?o ASCII puro)
    if not hostname.isascii() or hostname.startswith("xn--"):
        return False

    # Rejeitar IP literal (ex.: https://127.0.0.1/)
    try:
        ipaddress.ip_address(hostname)
        return False  # Se for IP, rejeita
    except ValueError:
        pass  # N?o ? IP, prossegue

    # 5. Hostname deve bater exatamente com a allowlist
    if hostname not in ALLOWED_GOOGLE_HOSTS:
        return False

    # 6. Valida??o de caminhos restritos por dom?nio
    if hostname in PATH_PREFIX_REQUIREMENTS:
        allowed_prefixes = PATH_PREFIX_REQUIREMENTS[hostname]
        path = parsed.path or "/"
        if not any(path.startswith(prefix) for prefix in allowed_prefixes):
            return False

    return True
