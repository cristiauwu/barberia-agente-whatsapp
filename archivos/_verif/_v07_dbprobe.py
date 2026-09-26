import subprocess,sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def d(*a):
    return subprocess.run([DOCKER,*a],capture_output=True,text=True).stdout
sql="""SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2;"""
print(d("exec","barberia-postgres","psql","-U","barberia","-d","barberia","-c",sql))