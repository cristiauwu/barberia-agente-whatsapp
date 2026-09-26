import urllib.request, re, zipfile, io, json
SID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
buf=[]
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

# xlsx raw
try:
    b = get(f"https://docs.google.com/spreadsheets/d/{SID}/export?format=xlsx")
    buf.append(f"xlsx bytes={len(b)} head={b[:200]!r}")
    z = zipfile.ZipFile(io.BytesIO(b))
    buf.append("names: " + ", ".join(z.namelist()[:40]))
    for n in z.namelist():
        if "workbook" in n.lower():
            buf.append(f"{n}: {z.read(n)[:2000].decode('utf-8','replace')}")
except Exception as e:
    buf.append(f"xlsx ERR {e}")

# html view
try:
    h = get(f"https://docs.google.com/spreadsheets/d/{SID}/htmlview").decode("utf-8","replace")
    buf.append("htmlview len " + str(len(h)))
except Exception as e:
    buf.append(f"htmlview ERR {e}")

# gviz for gid
for gid in ("941506024","0","1","2","3","4"):
    try:
        b = get(f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&gid={gid}")
        buf.append(f"--- gviz gid={gid} ({len(b)} bytes): {b[:300].decode('utf-8','replace')!r}")
    except Exception as e:
        buf.append(f"--- gviz gid={gid} ERR {e}")

open(r"G:\Barberia\_audit\_sheets.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")