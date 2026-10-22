"""Serviço de validação de URL de destino para prevenção de Open Redirect.

Garante que URLs de redirecionamento pertençam estritamente aos domínios e caminhos
oficiais autorizados do Google Meu Negócio / Google Maps / Google Reviews.

Fonte oficial de referência:
https://support.google.com/business/answer/16816815?hl=pt-BR
(Criar um link ou QR code para pedir avaliações - Ajuda do Perfil da empresa no Google)
"""

import ipaddress
from urllib.parse import urlsplit

# Comprimento máximo seguro para URLs
MAX_URL_LENGTH = 2048

# Allowlist de hostnames oficiais do Google autorizados para avaliações
# Nota: goo.gl foi removido por não constar na documentação oficial atual de avaliações do Google.
ALLOWED_GOOGLE_HOSTS: frozenset[str] = frozenset({
    "g.page",
    "search.google.com",
    "maps.app.goo.gl",
    "www.google.com",
    "google.com",
})

# Restrições de prefixo de caminho obrigatório por hostname
PATH_PREFIX_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "search.google.com": ("/local/writereview",),
    "www.google.com": ("/maps",),
    "google.com": ("/maps",),
}


def validate_destination_url(url: str | None) -> bool:
    r"""Valida estritamente se uma URL de destino pertence aos domínios do Google autorizados.

    Função pura, estritamente determinística e sem I/O de rede.

    Regras de validação:
    - Esquema obrigatoriamente HTTPS.
    - Hostname existente, exato na allowlist oficial (sem subdomínios arbitrários).
    - Proibição de credenciais / userinfo (ex.: user@host).
    - Proibição de portas não-padrão (apenas 443 ou omitida).
    - Proibição de caracteres de controle, espaços em branco e backslashes (\).
    - Proibição de endereços IP literais (IPv4 e IPv6).
    - Proibição de homógrafos Unicode / IDN / punycode.
    - Validação de prefixo de caminho para domínios genéricos (search.google.com, google.com).
    """
    if not url or not isinstance(url, str):
        return False

    # Rejeitar URLs com espaços em branco extras (início/fim) ou comprimento excessivo
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

    # 2. Rejeitar presença de userinfo (ex: https://g.page@evil.com)
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

    # Rejeitar homógrafos Unicode e punycode (todos os domínios Google autorizados são ASCII puro)
    if not hostname.isascii() or hostname.startswith("xn--"):
        return False

    # Rejeitar IP literal (ex.: https://127.0.0.1/)
    try:
        ipaddress.ip_address(hostname)
        return False  # Se for IP, rejeita
    except ValueError:
        pass  # Não é IP, prossegue

    # 5. Hostname deve bater exatamente com a allowlist
    if hostname not in ALLOWED_GOOGLE_HOSTS:
        return False

    # 6. Validação de caminhos restritos por domínio
    if hostname in PATH_PREFIX_REQUIREMENTS:
        allowed_prefixes = PATH_PREFIX_REQUIREMENTS[hostname]
        path = parsed.path or "/"
        if not any(path.startswith(prefix) for prefix in allowed_prefixes):
            return False

    return True
