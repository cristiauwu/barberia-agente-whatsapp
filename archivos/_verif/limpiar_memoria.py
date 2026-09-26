import sys,io,subprocess
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def psql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",s],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()
JID=sys.argv[1] if len(sys.argv)>1 else "5214501111805@s.whatsapp.net"
print("antes:",psql(f"SELECT count(*) FROM n8n_chat_histories WHERE session_id='{JID}';"))
print(psql(f"DELETE FROM n8n_chat_histories WHERE session_id='{JID}';"))
print("despues:",psql(f"SELECT count(*) FROM n8n_chat_histories WHERE session_id='{JID}';"))