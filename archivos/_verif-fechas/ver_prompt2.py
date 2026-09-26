#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
wf = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
n = next(x for x in wf["nodes"] if x["name"] == "AI Agent")
print(json.dumps({k: (v if not isinstance(v, str) else f"<<{len(v)} chars>>")
                  for k, v in n["parameters"].items()}, ensure_ascii=False, indent=1))
print()
p = n["parameters"]
for k, v in p.items():
    if isinstance(v, str) and len(v) > 100:
        print("#" * 30, k, len(v))
        print(v)