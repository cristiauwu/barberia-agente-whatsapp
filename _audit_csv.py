import urllib.request
url = "https://docs.google.com/spreadsheets/d/1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk/export?format=csv&gid=941506024"
r = urllib.request.urlopen(url, timeout=90)
data = r.read()
open(r"G:\Barberia\_audit_sheet.csv", "wb").write(data)
print("bytes:", len(data))
print(data[:4000].decode("utf-8", "replace"))