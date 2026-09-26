import datetime,sys,io
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
dias=["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
for f in ["2026-09-25","2026-09-26","2026-09-27","2026-09-28","2026-09-29","2026-10-01","2026-10-05","2026-10-06","2026-10-08"]:
    d=datetime.date.fromisoformat(f)
    print(f, "->", dias[d.weekday()])