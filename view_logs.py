"""
Leitor de logs ao vivo - mostra os logs em tempo real ou analisa sessoes passadas.

Uso:
    python view_logs.py                   # ultima sessao, ao vivo
    python view_logs.py --session arquivo # sessao especifica
    python view_logs.py --summary         # resumo de todas as sessoes
    python view_logs.py --tokens          # mostra todos os tokens encontrados
    python view_logs.py --swf             # lista SWFs capturados
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

BASE_DIR   = Path("captured")
LOGS_DIR   = BASE_DIR / "logs"
TOKENS_DIR = BASE_DIR / "tokens"
SWF_DIR    = BASE_DIR / "swf"

R  = "\033[91m"; G  = "\033[92m"; Y  = "\033[93m"
B  = "\033[94m"; M  = "\033[95m"; C  = "\033[96m"
W  = "\033[97m"; DIM = "\033[2m"; RST = "\033[0m"; BOLD = "\033[1m"


def latest_log() -> Path | None:
    logs = sorted(LOGS_DIR.glob("session_*.jsonl"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def tail_live(path: Path):
    """Segue o arquivo de log ao vivo (tipo tail -f)."""
    print(f"{BOLD}{C}[LIVE]{RST} Lendo: {path}")
    print(f"{DIM}Ctrl+C para sair{RST}\n")
    with open(path, "r", encoding="utf-8") as f:
        f.seek(0, 2)  # vai para o fim
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue
            try:
                rec = json.loads(line)
                _print_record(rec)
            except json.JSONDecodeError:
                print(line, end="")


def print_session(path: Path):
    """Imprime toda a sessao formatada."""
    print(f"{BOLD}{C}Sessao:{RST} {path}\n")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                _print_record(json.loads(line))
            except Exception:
                pass


def _print_record(rec: dict):
    event = rec.get("event", "")
    ts    = rec.get("ts", "")

    if event == "request":
        method = rec.get("method", "?")
        url    = rec.get("url", "")
        color  = G if method in ("GET", "HEAD") else Y
        print(f"{DIM}{ts}{RST} {BOLD}{color}{method:6}{RST} {url}")
        for t in rec.get("tokens", []):
            print(f"  {R}[TOKEN]{RST} {t}")

    elif event == "response":
        status = rec.get("status", "?")
        ct     = rec.get("content_type", "")[:50]
        size   = rec.get("body_size", 0)
        sc     = G if str(status).startswith("2") else (Y if str(status).startswith("3") else R)
        swf    = f" {BOLD}{M}[SWF]{RST}" if rec.get("is_swf") else ""
        print(f"  {DIM}└{RST} {sc}{status}{RST} {DIM}{ct:50}{RST} {size:>8}b{swf}")
        for t in rec.get("tokens", []):
            print(f"    {R}[TOKEN]{RST} {t}")

    elif event == "swf_captured":
        print(f"\n  {BOLD}{M}[SWF CAPTURADO]{RST}")
        print(f"  URL:    {rec.get('url')}")
        print(f"  Tam:    {rec.get('size', 0):,} bytes")
        print(f"  MD5:    {rec.get('md5')}")
        print(f"  Arquivo: {rec.get('file')}\n")


def summary():
    """Resumo de todas as sessoes."""
    logs = sorted(LOGS_DIR.glob("session_*.jsonl"))
    if not logs:
        print("Nenhuma sessao encontrada em", LOGS_DIR)
        return

    total_req = total_resp = total_swf = total_tok = 0
    for log in logs:
        req = resp = swf = tok = 0
        with open(log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    e = r.get("event", "")
                    if e == "request":
                        req += 1
                        tok += len(r.get("tokens", []))
                    elif e == "response":
                        resp += 1
                        tok += len(r.get("tokens", []))
                    elif e == "swf_captured":
                        swf += 1
                except Exception:
                    pass
        print(f"{C}{log.name}{RST}  req={req} resp={resp} {M}swf={swf}{RST} {R}tokens={tok}{RST}")
        total_req += req; total_resp += resp; total_swf += swf; total_tok += tok

    print(f"\n{BOLD}TOTAL:{RST}  req={total_req} resp={total_resp} {M}swf={total_swf}{RST} {R}tokens={total_tok}{RST}")


def list_swf():
    swfs = sorted(SWF_DIR.glob("*.swf"))
    if not swfs:
        print("Nenhum SWF capturado em", SWF_DIR)
        return
    print(f"{BOLD}SWFs capturados ({len(swfs)}):{RST}\n")
    for swf in swfs:
        meta_path = swf.parent / (swf.name + ".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            print(f"  {M}{swf.name}{RST}")
            print(f"    URL:  {meta.get('url')}")
            print(f"    Tam:  {meta.get('size', 0):,} bytes   MD5: {meta.get('md5')}")
        else:
            print(f"  {M}{swf.name}{RST}  ({swf.stat().st_size:,} bytes)")


def show_tokens():
    tok_files = sorted(TOKENS_DIR.glob("tokens_*.txt"))
    if not tok_files:
        print("Nenhum token capturado em", TOKENS_DIR)
        return
    for f in tok_files:
        print(f"\n{BOLD}{C}{f.name}{RST}")
        print(f.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Leitor de logs do Flash Interceptor")
    parser.add_argument("--session",  metavar="ARQUIVO", help="Sessao especifica")
    parser.add_argument("--summary",  action="store_true", help="Resumo de todas as sessoes")
    parser.add_argument("--tokens",   action="store_true", help="Mostra todos os tokens")
    parser.add_argument("--swf",      action="store_true", help="Lista SWFs capturados")
    parser.add_argument("--live",     action="store_true", help="Segue ultima sessao ao vivo")
    args = parser.parse_args()

    if args.summary:
        summary()
    elif args.tokens:
        show_tokens()
    elif args.swf:
        list_swf()
    elif args.session:
        print_session(Path(args.session))
    else:
        log = latest_log()
        if not log:
            print("Nenhuma sessao encontrada. Inicie o proxy primeiro.")
            sys.exit(1)
        if args.live:
            try:
                tail_live(log)
            except KeyboardInterrupt:
                print("\nEncerrado.")
        else:
            print_session(log)


if __name__ == "__main__":
    main()
