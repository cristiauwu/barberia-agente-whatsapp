import subprocess,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def sql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-c",s],capture_output=True,text=True)
    return r.stdout+r.stderr
print(sql("\\d n8n_chat_histories"))
print(sql("SELECT session_id, count(*) FROM n8n_chat_histories GROUP BY 1 ORDER BY 2 DESC LIMIT 20;"))
print(sql("SELECT id, session_id, left(message::text,120) FROM n8n_chat_histories ORDER BY id DESC LIMIT 5;"))
print(sql("SELECT * FROM barber_operadores;"))
print(sql("SELECT * FROM barber_servicios;"))