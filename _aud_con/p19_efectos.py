import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

out = []
out.append("== ESCALACIONES (posibles efectos de mi prueba) ==")
try:
    out.append(str(q("SELECT * FROM barber_escalaciones ORDER BY 1 DESC LIMIT 8")[1]))
except Exception as e:
    out.append("ERR " + str(e))

out.append("")
out.append("== CITAS (mi prueba NO agendo nada) ==")
out.append(str(q("SELECT count(*) FROM barber_citas")[1]))
out.append(str(q("SELECT jid, inicio, servicio, estado FROM barber_citas "
                 "WHERE jid LIKE '%5214501111805%' ORDER BY inicio DESC LIMIT 5")[1]))

out.append("")
out.append("== CLIENTES de prueba ==")
out.append(str(q("SELECT jid, nombre, visitas FROM barber_clientes "
                 "WHERE jid LIKE '%5214501111805%'")[1]))

out.append("")
out.append("== MENSAJES DE MEMORIA n8n_chat_histories de ese JID ==")
out.append(str(q("SELECT count(*) FROM n8n_chat_histories WHERE session_id "
                 "LIKE '%5214501111805%'")[1]))

out.append("")
out.append("== pausas / operadores (intactos) ==")
out.append(str(q("SELECT count(*) FROM barber_pausas")[1]))
out.append(str(q("SELECT jid, activo FROM barber_operadores")[1]))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\efectos.txt", "w", encoding="utf-8").write(txt)
print(txt)