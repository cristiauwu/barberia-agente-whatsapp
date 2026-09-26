import re
sql = open(r"G:\Barberia\archivos\conocimiento-barberia.sql", encoding="utf-8").read()
i = sql.find("VALUES"); j = sql.find("ON CONFLICT", i)
bloque = sql[i:j]
# reconstruir las entradas por bloques que empiezan con ('
partes = re.split(r"\n(?=\(')", bloque)
partes = [p for p in partes if p.strip().startswith("('")]
print("total entradas:", len(partes))
for n in (1, 40, 41, 42, 52):
    if n <= len(partes):
        p = " ".join(partes[n - 1].split())
        print("#%d -> %s" % (n, p[:130]))

print()
print("== COMPARACION ARCHIVO REPO vs PROMPT VIVO ==")
repo = open(r"G:\Barberia\prompt-sistema-agente-barberia.txt", encoding="utf-8").read()
vivo = open(r"G:\Barberia\_aud_con\prompt_vivo.txt", encoding="utf-8").read()
print("repo : %d caracteres" % len(repo))
print("vivo : %d caracteres" % len(vivo))
print("iguales (exacto)      :", repo == vivo)
print("iguales (sin espacios):", repo.strip() == vivo.strip())
# primera diferencia
for n, (a, b) in enumerate(zip(repo, vivo)):
    if a != b:
        print("primera diferencia en pos %d: %r vs %r" % (n, repo[n-40:n+40], vivo[n-40:n+40]))
        break
else:
    print("sin diferencias en el prefijo comun; longitudes %d vs %d" % (len(repo), len(vivo)))