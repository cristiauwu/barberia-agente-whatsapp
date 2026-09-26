# -*- coding: utf-8 -*-
"""Escaneo de secretos en claro. Solo lectura."""
import os, re, json, io

ROOT = r"G:\Barberia"
SKIP_DIRS = {".git", ".docker", "node_modules", "__pycache__", ".venv", "venv", "fuentes-cache", "tipografias", "capturas", "_tmp"}
TEXT_EXT = {".py",".js",".ts",".json",".md",".txt",".sql",".yml",".yaml",".env",".sh",".ps1",".html",".css",".csv",".conf",".ini",".toml"}

PATTERNS = [
    ("OPENAI_SK",      re.compile(r"sk-[A-Za-z0-9_\-]{16,}")),
    ("JWT_EYJ",        re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}")),
    ("SUPABASE_SB",    re.compile(r"sb_(?:publishable|secret)_[A-Za-z0-9_\-]{10,}")),
    ("SUPABASE_JWT",   re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("POSTGRES_URI",   re.compile(r"postgres(?:ql)?://[^\s\"'<>\)\]]{10,}")),
    ("PASSWORD_KV",    re.compile(r"(?i)\b(password|passwd|pwd|apikey|api_key|api-key|secret|token|auth_key|access_token|bearer)\b\s*[:=]\s*[\"']?([^\s\"',;\)\]\}]{6,})")),
    ("PASSWORD_ARG",   re.compile(r"(?i)--(?:password|apikey|api-key|token)[= ]\s*[\"']?([^\s\"']{6,})")),
    ("GOOGLE_APIKEY",  re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("PRIVATE_KEY",    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("N8N_KEY",        re.compile(r"(?i)X-N8N-API-KEY[\"']?\s*[:=]\s*[\"']?([^\s\"',;]{10,})")),
    ("EVOLUTION_KEY",  re.compile(r"(?i)AUTHENTICATION_API_KEY[^\n]{0,80}")),
    ("BEARER",         re.compile(r"(?i)Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
]

# valores a ignorar (placeholders)
NOISE = re.compile(r"(?i)^(true|false|null|none|changeme|xxx+|\*+|\.\.\.|tu_|your_|<|\{\{|placeholder|example|aqu[ií]|REDACTED|os\.environ|process\.env|ENV\[|getenv)")

hits = []
scanned = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        ext = os.path.splitext(fn)[1].lower()
        if ext not in TEXT_EXT and "." in fn:
            continue
        try:
            if os.path.getsize(p) > 12_000_000:
                continue
            with io.open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            continue
        scanned += 1
        for i, line in enumerate(lines, 1):
            for name, rx in PATTERNS:
                for m in rx.finditer(line):
                    val = m.group(0)
                    # valor de la captura si existe
                    gv = m.group(m.lastindex) if m.lastindex else None
                    check = gv if gv else val
                    if NOISE.match(check.strip()):
                        continue
                    hits.append((os.path.relpath(p, ROOT), i, name, val.strip()[:160]))

print("Archivos de texto escaneados:", scanned)
print("Hallazgos:", len(hits))
print("=" * 100)
by_pattern = {}
for h in hits:
    by_pattern.setdefault(h[2], []).append(h)
for k in sorted(by_pattern):
    print("\n### %s  (%d)" % (k, len(by_pattern[k])))
    for rel, ln, name, val in by_pattern[k]:
        print("  %s:%d  ::  %s" % (rel, ln, val))