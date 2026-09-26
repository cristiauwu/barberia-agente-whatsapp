import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

t = tb.TEST if hasattr(tb, "TEST") else None
stopped = False
fila = {
    "ID": "verif-rec-t1", "Estatus": "cancelado", "Nombre": "Verif Rec",
    "Servicio": "Ceja", "Precio del servicio": "30", "Día ": "2026-11-20",
    "Hora": "10:00:00", "Numero celular": "5214501111805@s.whatsapp.net",
    "Execution ID": "",
}
print("=== ANTES ===")
before = tb.parse_csv(tb.read_sheet())
print(f"filas={len(before)}")
for i, r in enumerate(before, 1):
    print(f"  {i}: {r[:3]}")

print("\n=== APPEND ===")
print(json.dumps(tb.append_row(fila), ensure_ascii=False, indent=1))

time.sleep(3)
print("\n=== DESPUES ===")
after = tb.parse_csv(tb.read_sheet())
print(f"filas={len(after)}")
for i, r in enumerate(after, 1):
    print(f"  {i}: {r[:3]}")