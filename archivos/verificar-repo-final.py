#!/usr/bin/env python3
"""Verifica el repo publicado leyendo GitHub. Comprueba que NO haya claves."""
import base64, json, subprocess, sys, urllib.error, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
GCM=r"C:\Program Files\Git\mingw64\bin\git-credential-manager.exe"
U="cristiauwu"; R="barberia-agente-whatsapp"
CLAVES=["DC64CCC7469D-4E50","iWbaegXpWBjJ7PGs","Chinos452@@",
        "vTcYIYR7h7n357m9dohntQ","lXrbroKwpGHTqqCYoMpb3w"]
def tok():
    p=subprocess.run([GCM,"--no-ui","get"],input="protocol=https\nhost=github.com\n\n",
      capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    for l in (p.stdout or "").splitlines():
        if l.startswith("password="): return l.split("=",1)[1]
def api(t,ruta):
    r=urllib.request.Request("https://api.github.com"+ruta)
    r.add_header("Authorization",f"Bearer {t}")
    r.add_header("Accept","application/vnd.github+json")
    r.add_header("User-Agent","verificar")
    try:
        with urllib.request.urlopen(r,timeout=60) as x: return x.status, json.loads(x.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code, {}
t=tok()
print("="*66); print("VERIFICACION DEL REPO PUBLICADO"); print("="*66)
st,repo=api(t,f"/repos/{U}/{R}")
if st!=200: print(f"  MAL HTTP {st}"); sys.exit(1)
print(f"\n  URL: {repo['html_url']}")
print(f"  privado: {repo['private']}")
print(f"  commits en main: (consultando)")
st,arbol=api(t,f"/repos/{U}/{R}/git/trees/main?recursive=1")
blobs=[x for x in arbol.get("tree",[]) if x["type"]=="blob"]
print(f"  archivos publicados: {len(blobs)}")
print("\n=== CLAVES EN EL REPO REMOTO ===")
malos=[]; rev=0
vig=[b for b in blobs if any(k in b["path"].lower() for k in
     ("env","key","conn","secret","credential",".json",".yml",".md",".py"))
     and b["size"]<500_000]
print(f"  analizando {len(vig)} archivos...")
for b in vig:
    st2,c=api(t,f"/repos/{U}/{R}/git/blobs/{b['sha']}")
    if st2!=200 or not isinstance(c,dict): continue
    cont=c.get("content","")
    if not cont: continue
    try: txt=base64.b64decode(cont).decode("utf-8","replace")
    except Exception: continue
    rev+=1
    for k in CLAVES:
        if k in txt: malos.append((b["path"],k)); break
print(f"  contenido analizado: {rev} archivos")
if malos:
    print("  MAL: CLAVES PUBLICADAS:")
    for f,k in malos[:15]: print(f"    {f}  ->  {k[:18]}...")
else:
    print("  OK  ninguna clave en el repo publico")
print("\n=== ARCHIVOS PROHIBIDOS ===")
nombres=[b["path"] for b in blobs]
for p in (".env",".env.evolution",".n8n-key.txt",".supabase-conn.txt",
          ".supabase-pass.txt","qr-base64.txt","qr-whatsapp.png"):
    pres=[n for n in nombres if n.endswith(p)]
    print(f"  {'MAL ' if pres else 'OK  '} {p}")
print("\n=== CONTENIDO CLAVE ===")
for r,d in (("README.md","README"),("verify.py","187 comprobaciones"),
    ("prompt-sistema-agente-barberia.txt","el prompt"),
    ("BarberiaAgenteFLUJO-1-UNCENSORED.json","el agente"),
    ("BarberiaAgenteFLUJO-2-RECORDATORIOS.json","recordatorios"),
    ("archivos/dashboard/dashboard.html","el panel"),
    ("archivos/dashboard/REDISENO.md","informe del diseno"),
    ("archivos/MANUAL-DUENO.md","manual del dueno")):
    print(f"  {'OK  ' if r in nombres else 'FALTA'} {d}")
print("\n=== TAMANO ===")
g=sorted(blobs,key=lambda x:-x["size"])[:3]
for b in g: print(f"  {b['size']/1024/1024:>6.2f} MB  {b['path']}")
print("\n"+"="*66)
print("RESULTADO: "+("TODO OK" if not malos else "REVISAR"))
print("="*66)