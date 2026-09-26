# -*- coding: utf-8 -*-
"""¿Se usa instance_server_url en alguna URL de algun nodo? ¿Y el apikey?"""
import io, json, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for path, label in [
    (r"G:\Barberia\BarberiaAgenteFLUJO-1-UNCENSORED.json", "AGENTE"),
    (r"G:\Barberia\BarberiaAgenteFLUJO-2-RECORDATORIOS.json", "RECORDATORIOS"),
]:
    doc = json.load(io.open(path, encoding="utf-8"))
    print("=" * 84); print("### %s (%s)" % (label, path)); print("=" * 84)
    for n in doc["nodes"]:
        s = json.dumps(n.get("parameters") or {}, ensure_ascii=False)
        if "instance_server_url" in s or "instance_apikey" in s or "instance_name" in s:
            print("\nNODO: %s  (%s)" % (n.get("name"), n.get("type")))
            p = n.get("parameters") or {}
            for k, v in p.items():
                vs = json.dumps(v, ensure_ascii=False)
                if "instance_" in vs:
                    print("   %-22s = %s" % (k, vs[:400]))