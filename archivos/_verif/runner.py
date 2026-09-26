# -*- coding: utf-8 -*-
import json, sys, io, os, time
sys.path.insert(0, r"G:\Barberia\archivos\_verif")
from harness import enviar, psql, api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
    sys.stdout._vutf8=True

JID_CLIENTE="5214501111805@s.whatsapp.net"
OUT=r"G:\Barberia\archivos\_verif\resultados.json"

CASOS=[
 # id, etiqueta, texto
 ("B9","hola — primer mensaje (memoria vaciada)","hola"),
 ("A1","¿a qué hora abren?","¿A qué hora abren?"),
 ("A2","¿hasta qué hora están abiertos?","¿Y hasta qué hora están abiertos?"),
 ("A3","cita fuera de horario (07:00)","quiero un corte mañana a las 7 de la mañana"),
 ("A4","cita que termina después de cerrar (peinado 19:30)","quiero un peinado mañana a las 19:30"),
 ("A5","domingo","quiero un corte el domingo a las 12"),
 ("A6","fecha en el pasado","quiero un corte ayer a las 4"),
 ("A7","el jueves (debe ser próximo jueves 1 oct)","quiero un corte el jueves a las 4 de la tarde"),
 ("C11a","mensaje basura: ?","?"),
 ("C11b","mensaje basura: asdfgh","asdfgh"),
 ("C11c","mensaje basura: 12345","12345"),
 ("C13","emojis solos","😀😀😀"),
 ("C14","petición imposible: tinte","quiero un tinte de cabello"),
 ("C15","precio corte de niño (esperado $150)","¿cuánto cuesta el corte de niño?"),
 ("C12","mensaje muy largo (2000+ car.)","Quiero informacion sobre sus servicios " + ("y precios disponibles " * 60) + "gracias"),
 ("D18","no debe decir no-show","¿qué pasa si no llego?"),
 ("D19","no debe decir que vio audio/foto","te mandé un audio y una foto, ¿los escuchaste?"),
 ("D20","no debe prometer facturación","¿me pueden facturar la cita?"),
]

def cargar():
    if os.path.exists(OUT):
        return json.load(open(OUT,encoding="utf-8"))
    return {}

def main():
    ini=int(sys.argv[1]); fin=int(sys.argv[2])
    res=cargar()
    for i in range(ini,min(fin,len(CASOS))):
        cid,etq,txt=CASOS[i]
        if cid in res and res[cid].get("respuesta"):
            print(f"[{cid}] ya hecho, salto"); continue
        print(f"\n>>> [{cid}] {etq}\n>>> ENVIO: {txt[:120]!r}")
        r=enviar(JID_CLIENTE,txt)
        r["caso"]=cid; r["etiqueta"]=etq; r["enviado"]=txt
        res[cid]=r
        json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
        if r.get("respuesta"):
            print("<<< RESP:",r["respuesta"])
            print("<<< exec",r["exec_id"],r["status"],"| nodos:",r["nodos"])
        else:
            print("<<< SIN RESPUESTA:",json.dumps(r,ensure_ascii=False)[:600])
        time.sleep(13)

main()