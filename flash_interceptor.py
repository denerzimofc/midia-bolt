"""
Flash Player Traffic Interceptor
=================================
mitmproxy addon que captura:
  - Arquivos .swf em trânsito
  - Todos os endpoints acessados
  - Tokens, cookies e headers sensíveis
  - Payloads de request/response (AMF, XML, JSON, form-data)

Uso: mitmdump -s flash_interceptor.py --listen-port 8080
"""

import os
import re
import json
import time
import hashlib
import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from mitmproxy import http, ctx
from mitmproxy.net.http import encoding as http_encoding


# ─── Pastas de saída ───────────────────────────────────────────────────────────
BASE_DIR   = Path("captured")
SWF_DIR    = BASE_DIR / "swf"
LOGS_DIR   = BASE_DIR / "logs"
TOKENS_DIR = BASE_DIR / "tokens"

for d in (SWF_DIR, LOGS_DIR, TOKENS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ─── Arquivo de log da sessão ──────────────────────────────────────────────────
SESSION_TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE    = LOGS_DIR   / f"session_{SESSION_TS}.jsonl"
TOKEN_FILE  = TOKENS_DIR / f"tokens_{SESSION_TS}.txt"

# ─── Padrões para extração de tokens ──────────────────────────────────────────
TOKEN_HEADERS = {
    "authorization", "x-auth-token", "x-api-key", "x-access-token",
    "x-session-token", "x-user-token", "x-csrf-token", "x-requested-with",
    "x-flash-version", "cookie", "set-cookie",
}

TOKEN_PATTERNS = [
    re.compile(r'token["\s:=]+([A-Za-z0-9\-_\.]{16,})', re.IGNORECASE),
    re.compile(r'session["\s:=]+([A-Za-z0-9\-_\.]{16,})', re.IGNORECASE),
    re.compile(r'auth["\s:=]+([A-Za-z0-9\-_\.]{16,})',   re.IGNORECASE),
    re.compile(r'key["\s:=]+([A-Za-z0-9\-_\.]{16,})',    re.IGNORECASE),
    re.compile(r'Bearer\s+([A-Za-z0-9\-_\.]{16,})',      re.IGNORECASE),
    re.compile(r'PHPSESSID=([A-Za-z0-9]+)',               re.IGNORECASE),
    re.compile(r'JSESSIONID=([A-Za-z0-9]+)',              re.IGNORECASE),
    re.compile(r'ASP\.NET_SessionId=([A-Za-z0-9\-]+)',   re.IGNORECASE),
]

# ─── Cores ANSI ───────────────────────────────────────────────────────────────
R  = "\033[91m"   # vermelho
G  = "\033[92m"   # verde
Y  = "\033[93m"   # amarelo
B  = "\033[94m"   # azul
M  = "\033[95m"   # magenta
C  = "\033[96m"   # ciano
W  = "\033[97m"   # branco
DIM = "\033[2m"
RST = "\033[0m"
BOLD = "\033[1m"


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def banner_line(char="─", width=72):
    return char * width


def extract_tokens_from_text(text: str) -> list[str]:
    found = []
    for pat in TOKEN_PATTERNS:
        for m in pat.finditer(text):
            found.append(m.group(0))
    return list(set(found))


def save_token(source: str, token_str: str):
    with open(TOKEN_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts()}] {source}\n  {token_str}\n\n")


def decode_body(flow_msg) -> str | None:
    """Tenta decodificar o corpo da mensagem como texto."""
    ct = flow_msg.headers.get("content-type", "")
    body = flow_msg.get_content()
    if not body:
        return None
    # tenta UTF-8, depois latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            return body.decode(enc)
        except Exception:
            pass
    return f"<binary {len(body)} bytes>"


def pretty_headers(headers) -> dict:
    return {k: v for k, v in headers.items()}


def write_log(record: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class FlashInterceptor:
    """Addon principal do mitmproxy."""

    def __init__(self):
        self.swf_count   = 0
        self.req_count   = 0
        self.token_count = 0
        print(f"\n{BOLD}{M}{banner_line('═')}{RST}")
        print(f"{BOLD}{M}  FLASH PLAYER TRAFFIC INTERCEPTOR{RST}")
        print(f"{M}{banner_line('═')}{RST}")
        print(f"  {C}SWF salvo em:{RST}    {SWF_DIR}")
        print(f"  {C}Logs em:{RST}         {LOG_FILE}")
        print(f"  {C}Tokens em:{RST}       {TOKEN_FILE}")
        print(f"  {C}Porta:{RST}           8080")
        print(f"{M}{banner_line('─')}{RST}\n")

    # ── Requisições ────────────────────────────────────────────────────────────
    def request(self, flow: http.HTTPFlow):
        self.req_count += 1
        url    = flow.request.pretty_url
        method = flow.request.method
        parsed = urlparse(url)
        hdrs   = pretty_headers(flow.request.headers)
        body   = decode_body(flow.request)

        # ── Token nos headers ──
        found_tokens = []
        for hname, hval in flow.request.headers.items():
            if hname.lower() in TOKEN_HEADERS:
                found_tokens.append(f"{hname}: {hval}")
        if body:
            found_tokens += extract_tokens_from_text(body)

        if found_tokens:
            self.token_count += len(found_tokens)
            for t in found_tokens:
                save_token(f"REQ {method} {url}", t)

        # ── Terminal ──
        color = G if method in ("GET", "HEAD") else Y
        print(f"{DIM}{ts()}{RST} {BOLD}{color}{method}{RST} {W}{url}{RST}")

        if found_tokens:
            for t in found_tokens:
                print(f"  {BOLD}{R}[TOKEN]{RST} {t}")

        if body and len(body) < 2000:
            # mostra payload compacto
            preview = body.replace("\n", " ").replace("\r", "")[:300]
            print(f"  {DIM}payload: {preview}…{RST}" if len(body) > 300 else f"  {DIM}payload: {preview}{RST}")

        # ── Log ──
        write_log({
            "event":   "request",
            "ts":      ts(),
            "method":  method,
            "url":     url,
            "host":    parsed.netloc,
            "path":    parsed.path,
            "query":   parse_qs(parsed.query),
            "headers": hdrs,
            "tokens":  found_tokens,
            "body":    body if body and len(body) < 8192 else f"<{len(body or b'')} bytes>",
        })

    # ── Respostas ───────────────────────────────────────────────────────────────
    def response(self, flow: http.HTTPFlow):
        url    = flow.request.pretty_url
        status = flow.response.status_code
        ct     = flow.response.headers.get("content-type", "")
        body   = flow.response.get_content()

        # ── SWF detectado no corpo ──
        is_swf = (
            url.lower().endswith(".swf")
            or "application/x-shockwave-flash" in ct.lower()
            or (body and body[:3] == b"CWS") or (body and body[:3] == b"FWS")
            or (body and body[:3] == b"ZWS")
        )

        if is_swf and body:
            self._save_swf(url, body)

        # ── Tokens na resposta ──
        resp_body_text = decode_body(flow.response)
        found_tokens   = []
        for hname, hval in flow.response.headers.items():
            if hname.lower() in TOKEN_HEADERS:
                found_tokens.append(f"{hname}: {hval}")
        if resp_body_text:
            found_tokens += extract_tokens_from_text(resp_body_text)

        if found_tokens:
            self.token_count += len(found_tokens)
            for t in found_tokens:
                save_token(f"RESP {status} {url}", t)

        # ── Terminal ──
        sc = G if 200 <= status < 300 else (Y if 300 <= status < 400 else R)
        swf_tag = f" {BOLD}{M}[SWF CAPTURADO]{RST}" if is_swf else ""
        tok_tag = f" {BOLD}{R}[{len(found_tokens)} TOKENS]{RST}" if found_tokens else ""
        size    = len(body) if body else 0
        print(f"  {DIM}└─{RST} {sc}{status}{RST} {DIM}{ct[:40]:40}{RST} {DIM}{size:>8} bytes{RST}{swf_tag}{tok_tag}")

        if found_tokens:
            for t in found_tokens:
                print(f"     {R}[TOKEN]{RST} {t}")

        # ── Log ──
        write_log({
            "event":        "response",
            "ts":           ts(),
            "url":          url,
            "status":       status,
            "content_type": ct,
            "headers":      pretty_headers(flow.response.headers),
            "tokens":       found_tokens,
            "is_swf":       is_swf,
            "body_size":    size,
            "body": (
                resp_body_text[:8192]
                if resp_body_text and "text" in ct or "json" in ct or "xml" in ct or "form" in ct
                else f"<binary {size} bytes>"
            ),
        })

    # ── Salva SWF ──────────────────────────────────────────────────────────────
    def _save_swf(self, url: str, data: bytes):
        self.swf_count += 1
        # nome do arquivo: hash + slug da URL
        slug = re.sub(r"[^\w\-.]", "_", urlparse(url).path.split("/")[-1] or "unknown")
        if not slug.endswith(".swf"):
            slug += ".swf"
        digest = hashlib.md5(data).hexdigest()[:8]
        fname  = f"{SESSION_TS}_{self.swf_count:03d}_{digest}_{slug}"
        fpath  = SWF_DIR / fname
        fpath.write_bytes(data)

        meta = {
            "url":      url,
            "size":     len(data),
            "md5":      hashlib.md5(data).hexdigest(),
            "sha256":   hashlib.sha256(data).hexdigest(),
            "file":     str(fpath),
            "ts":       ts(),
        }
        meta_path = SWF_DIR / (fname + ".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        print(f"\n  {BOLD}{M}{banner_line('─', 60)}{RST}")
        print(f"  {BOLD}{M}  SWF #{self.swf_count} CAPTURADO{RST}")
        print(f"  {C}  URL:   {RST}{url}")
        print(f"  {C}  Tam:   {RST}{len(data):,} bytes")
        print(f"  {C}  MD5:   {RST}{meta['md5']}")
        print(f"  {C}  SHA256:{RST}{meta['sha256']}")
        print(f"  {C}  Salvo: {RST}{fpath}")
        print(f"  {M}{banner_line('─', 60)}{RST}\n")

        write_log({"event": "swf_captured", **meta})

    # ── Erros TLS ───────────────────────────────────────────────────────────────
    def tls_handshake_error(self, tls_client_hello, exc):
        print(f"  {Y}[TLS-ERRO]{RST} {exc}")

    def tls_failed_client(self, tls_client_hello):
        print(f"  {Y}[TLS-FALHA-CLIENT]{RST}")


addons = [FlashInterceptor()]
