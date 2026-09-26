import subprocess, os, io, json
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def psql(sql, db="barberia", user="barberia"):
    r = subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U",user,"-d",db,"-t","-A","-F","|","-c",sql],
        capture_output=True, text=True, timeout=120, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s)
def q(sql,label):
    rc,o,e=psql(sql); W(f"### {label}\nrc={rc}\n{o}\nERR:{e[:300]}\n")

q("SELECT session_id, count(*) FROM n8n_chat_histories GROUP BY session_id ORDER BY count(*) DESC","rows per session")
q("SELECT count(*), avg(length(message::text))::int, max(length(message::text)) FROM n8n_chat_histories","message length stats")
q("SELECT message->>'type' AS t, count(*), avg(length(message->>'content'))::int, max(length(message->>'content')) FROM n8n_chat_histories GROUP BY 1","by message type")
q("SELECT left(message::text,700) FROM n8n_chat_histories ORDER BY id LIMIT 2","sample rows")
q("SELECT left(message::text,900) FROM n8n_chat_histories WHERE session_id=(SELECT session_id FROM n8n_chat_histories GROUP BY session_id ORDER BY count(*) DESC LIMIT 1) ORDER BY id DESC LIMIT 3","latest msgs of busiest session")
open(r"G:\Barberia\archivos\_audit\db2.txt","w",encoding="utf-8").write("\n".join(out))
print("ok")
