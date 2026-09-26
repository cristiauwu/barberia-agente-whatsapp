import subprocess, os, io, json
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def psql(sql, db="barberia", user="barberia"):
    r = subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U",user,"-d",db,"-t","-A","-F","|","-c",sql],
        capture_output=True, text=True, timeout=120, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()

out=[]
def W(*a):
    line=" ".join(str(x) for x in a); out.append(line); print(line)

W("### n8n_chat_histories structure")
W(psql("SELECT column_name||' '||data_type FROM information_schema.columns WHERE table_name='n8n_chat_histories' ORDER BY ordinal_position")[1])
W("\n### row counts")
for q,label in [
  ("SELECT count(*) FROM n8n_chat_histories","n8n_chat_histories total rows"),
  ("SELECT count(DISTINCT session_id) FROM n8n_chat_histories","distinct session_ids"),
  ("SELECT pg_size_pretty(pg_total_relation_size('n8n_chat_histories'))","table size"),
  ("SELECT count(*) FROM execution_entity","executions total"),
  ("SELECT count(*) FROM barber_citas","barber_citas"),
  ("SELECT count(*) FROM barber_escalaciones","barber_escalaciones"),
  ("SELECT count(*) FROM barber_operadores","barber_operadores"),
  ("SELECT count(*) FROM barber_pausas","barber_pausas"),
]:
    rc,o,e = psql(q); W(f"{label}: rc={rc} -> {o} {e[:200]}")

W("\n### n8n_chat_histories sample row (message shape)")
rc,o,e = psql("SELECT session_id, left(message::text, 600) FROM n8n_chat_histories LIMIT 3")
W(o); W(e[:300])

W("\n### rows / session distribution (top 15)")
rc,o,e = psql("SELECT session_id, count(*) FROM n8n_chat_histories GROUP BY session_id ORDER BY count(*) DESC LIMIT 15")
W(o); W(e[:300])

W("\n### message length stats")
rc,o,e = psql("SELECT count(*), avg(length(message::text))::int, max(length(message::text)) FROM n8n_chat_histories")
W(o); W(e[:300])

W("\n### n8n version")
rc,o,e = psql("SELECT 1", db="n8n", user="n8n"); W("n8n db rc",rc,o[:200],e[:200])
open(r"G:\Barberia\archivos\_audit\db.txt","w",encoding="utf-8").write("\n".join(out))
