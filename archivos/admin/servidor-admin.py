#!/usr/bin/env python3
"""Panel + API same-origin. Run: python archivos/admin/servidor-admin.py

Install DB driver: python -m pip install 'psycopg[binary]>=3,<4'.
Generate password hash: python archivos/admin/servidor-admin.py --hash-password
Required: ADMIN_DB_DSN (SELECT-only role), ADMIN_PASSWORD_HASH, ADMIN_SESSION_SECRET
(64+ random characters), ADMIN_PUBLIC_ORIGIN (e.g. https://admin.example.com).
Price edits default OFF: manually migrate precios-admin.sql, deploy and verify W1
reads live catalog, then configure ADMIN_PRICE_DB_DSN (restricted function-only role)
and ADMIN_PRICE_UPDATES_ENABLED=true; never use the n8n/owner DB credential.
Optional: ADMIN_BIND=127.0.0.1, ADMIN_PORT=8765, ADMIN_TLS_CERT,
ADMIN_TLS_KEY, ADMIN_JOURNAL_PATH, EVOLUTION_URL, EVOLUTION_API_KEY,
EVOLUTION_INSTANCE. Public binding requires TLS cert/key; behind a TLS reverse
proxy bind loopback and forward only trusted origin/host (never expose port).
The SQLite journal MUST reside on persistent private storage, with one server
instance sharing it; UNKNOWN outcomes are never retried automatically.
"""
import base64
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
from datetime import datetime
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import ssl
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib.util import module_from_spec, spec_from_file_location
_spec = spec_from_file_location("datos_admin", Path(__file__).with_name("datos-admin.py"))
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)
Datos = _module.Datos
PriceConflict = _module.PriceConflict

HTML = Path(__file__).with_name("barber-chinos-admin.html")
COOKIE = "admin_session"
MAX_BODY = 4096
COOKIE_AGE = 8 * 3600
PHONE = re.compile(r"^(?:52(?:1)?)?[1-9][0-9]{9}$")  # 10, 52+10, 521+10 digits
KEY = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
SERVICE_KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MONEY = re.compile(r"^(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,2})?$")


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def hash_password(password, salt=None):
    if not password or len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt:16384:8:1:" + base64.urlsafe_b64encode(salt).decode() + ":" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password, encoded):
    try:
        kind, n, r, p, salt, expected = encoded.split(":")
        if kind != "scrypt" or (n,r,p) != ("16384","8","1"):
            return False
        got = hashlib.scrypt(password.encode(), salt=base64.urlsafe_b64decode(salt), n=16384,r=8,p=1)
        return secrets.compare_digest(got, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


class Journal:
    """Durable at-most-one-attempt claim, across threads and process restarts."""
    def __init__(self, path):
        self.path = str(path)
        if os.name != "nt":
            old=os.umask(0o077)
            try:
                Path(self.path).touch(mode=0o600,exist_ok=True)
            finally:
                os.umask(old)
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sends (key TEXT PRIMARY KEY, payload TEXT NOT NULL, jid TEXT NOT NULL, state TEXT NOT NULL, created INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS sends_jid ON sends(jid,created)")

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def claim(self, key, jid, text, now=None):
        now = int(time.time() if now is None else now)
        fingerprint = hashlib.sha256((jid+"\0"+text).encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT payload,state FROM sends WHERE key=?", (key,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise ApiError(422,"KEY_REUSED","La clave corresponde a otro mensaje")
                raise ApiError(409,"ALREADY_ATTEMPTED","El mensaje ya fue solicitado; no se reenvía automáticamente")
            recent = db.execute("SELECT count(*) FROM sends WHERE jid=? AND created>=?", (jid,now-300)).fetchone()[0]
            if recent:
                raise ApiError(429,"FREQUENCY_LIMIT","Espera cinco minutos antes de enviar otro mensaje a este cliente")
            db.execute("INSERT INTO sends(key,payload,jid,state,created) VALUES(?,?,?,'unknown',?)",
                       (key,fingerprint,jid,now))
        # Claim committed BEFORE request. A crash/timeout remains UNKNOWN forever.

    def mark_sent(self,key):
        with self.db() as db:
            db.execute("UPDATE sends SET state='sent' WHERE key=?", (key,))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


class Evolution:
    def __init__(self, base, api_key, instance, opener=None):
        self.base = base.rstrip("/")
        self.api_key = api_key
        self.instance = instance
        self.opener = opener or build_opener(NoRedirect).open
        url = urlsplit(self.base)
        if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("EVOLUTION_URL inválida")
        if url.scheme == "http" and url.hostname not in ("localhost","127.0.0.1","::1","evolution_api"):
            raise ValueError("Evolution remoto requiere HTTPS")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",instance):
            raise ValueError("EVOLUTION_INSTANCE inválida")

    def send(self,jid,text):
        # n8n forwards remoteJid verbatim to Evolution; preserve 52+1+10 aliases.
        number = jid
        request = Request(self.base + "/message/sendText/" + quote(self.instance),
                          data=json.dumps({"number":number,"text":text}).encode(),
                          headers={"apikey":self.api_key,"Content-Type":"application/json"},
                          method="POST")
        try:
            with self.opener(request,timeout=10) as resp:
                if resp.status < 200 or resp.status >= 300:
                    raise ApiError(502,"SEND_UNKNOWN","No se pudo confirmar el envío; no reintentar sin comprobar Evolution")
                data = resp.read(65537)
                if len(data)>65536:
                    raise ValueError("Respuesta demasiado grande")
                payload = json.loads(data)
                if not isinstance(payload,dict) or not isinstance(payload.get("key"),dict) or not isinstance(payload["key"].get("id"),str) or not payload["key"]["id"]:
                    raise ValueError("Respuesta de Evolution sin id de mensaje")
                return payload["key"]["id"]
        except (HTTPError, URLError, OSError, ValueError, TimeoutError) as exc:
            raise ApiError(502,"SEND_UNKNOWN","No se pudo confirmar el envío; no reintentar sin comprobar Evolution") from exc


class App:
    def __init__(self, origin, password_hash, secret, datos, journal, evolution=None, tls=False, price_updates_enabled=False):
        parsed=urlsplit(origin)
        if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("ADMIN_PUBLIC_ORIGIN inválido")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost","127.0.0.1","::1"):
            raise ValueError("Origen HTTP solo permitido en localhost")
        if parsed.scheme == "http" and tls:
            raise ValueError("ADMIN_PUBLIC_ORIGIN debe ser https cuando TLS esté activo")
        if len(secret)<64 or not password_hash:
            raise ValueError("Configurar ADMIN_SESSION_SECRET largo y ADMIN_PASSWORD_HASH")
        self.origin=origin.rstrip("/")
        self.host=parsed.netloc.lower()
        self.secure=parsed.scheme=="https"
        self.password_hash=password_hash
        self.secret=secret.encode()
        self.datos=datos
        self.journal=journal
        self.evolution=evolution
        self.price_updates_enabled=price_updates_enabled
        self.sessions={}
        self.lock=threading.Lock()
        self.failures={}

    def session(self, cookie_header):
        cookies=SimpleCookie()
        try:
            cookies.load(cookie_header or "")
            token=cookies[COOKIE].value if COOKIE in cookies else ""
        except Exception:
            return None
        signature=hashlib.sha256(self.secret+b"\0"+token.encode()).hexdigest()
        with self.lock:
            session=self.sessions.get(signature)
            if session and session["expires"]>time.time():
                return session
        return None

    def issue(self):
        token=secrets.token_urlsafe(32)
        csrf=secrets.token_urlsafe(32)
        signature=hashlib.sha256(self.secret+b"\0"+token.encode()).hexdigest()
        with self.lock:
            self.sessions[signature]={"csrf":csrf,"expires":time.time()+COOKIE_AGE}
        cookie=f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={COOKIE_AGE}"
        if self.secure:
            cookie += "; Secure"
        return csrf,cookie

    def revoke(self,cookie_header):
        cookies=SimpleCookie()
        try:
            cookies.load(cookie_header or "")
            token=cookies[COOKIE].value if COOKIE in cookies else ""
        except Exception:
            token=""
        signature=hashlib.sha256(self.secret+b"\0"+token.encode()).hexdigest()
        with self.lock:
            self.sessions.pop(signature,None)

    def authorize(self,session,csrf):
        if not session:
            raise ApiError(401,"AUTH_REQUIRED","Inicia sesión")
        if not csrf or not secrets.compare_digest(session["csrf"],csrf):
            raise ApiError(403,"CSRF_INVALID","Token CSRF inválido")


class Handler(BaseHTTPRequestHandler):
    server_version="BarberAdmin"
    sys_version=""

    def log_message(self,format,*args):
        # Never log paths (may contain personal data), headers, request bodies or credentials.
        pass

    def response(self,status,payload,extra=None,html=False):
        body = payload if html else json.dumps(payload,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","text/html; charset=utf-8" if html else "application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'none'; style-src 'self' 'unsafe-inline' data:; script-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if self.server.app.secure:
            self.send_header("Strict-Transport-Security","max-age=31536000")
        for k,v in (extra or {}).items():
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def fail(self,error):
        self.response(error.status,{"ok":False,"error":{"code":error.code,"message":error.message}})

    def parse(self):
        length=self.headers.get("Content-Length","")
        if not length.isdigit() or int(length)>MAX_BODY:
            raise ApiError(413,"BODY_SIZE","Tamaño de solicitud inválido")
        if self.headers.get("Content-Type","").split(";",1)[0].strip().lower()!="application/json":
            raise ApiError(415,"CONTENT_TYPE","Se requiere application/json")
        try:
            body=json.loads(self.rfile.read(int(length)))
        except (UnicodeDecodeError,ValueError):
            raise ApiError(400,"INVALID_JSON","JSON inválido")
        if not isinstance(body,dict):
            raise ApiError(400,"INVALID_JSON","Se requiere objeto JSON")
        return body

    def check_host(self,write=False):
        app=self.server.app
        if self.headers.get("Host","").lower()!=app.host:
            raise ApiError(403,"HOST_INVALID","Host inválido")
        if write:
            if self.headers.get("Origin","")!=app.origin:
                raise ApiError(403,"ORIGIN_INVALID","Origen inválido")
            if self.headers.get("Sec-Fetch-Site","") not in ("", "same-origin"):
                raise ApiError(403,"ORIGIN_INVALID","Origen inválido")

    def run(self,method):
        try:
            self.check_host(method=="POST")
            path=urlsplit(self.path).path
            app=self.server.app
            if method=="GET" and path in ("/", "/admin", "/admin/"):
                # HTML has no private data; browser authenticates to access each API.
                self.response(200,HTML.read_bytes(),html=True)
                return
            if not path.startswith("/api/admin/"):
                raise ApiError(404,"NOT_FOUND","Ruta no encontrada")
            key=path.removeprefix("/api/admin/")
            if method=="POST" and key=="login":
                body=self.parse()
                password=body.get("password")
                if not isinstance(password,str) or len(password)>1024:
                    raise ApiError(400,"INVALID_INPUT","Contraseña inválida")
                ip=self.client_address[0]
                with app.lock:
                    attempts=[x for x in app.failures.get(ip,[]) if x>time.time()-900]
                    app.failures[ip]=attempts
                    if len(attempts)>=5:
                        raise ApiError(429,"LOGIN_LIMIT","Demasiados intentos; vuelve más tarde")
                if not verify_password(password,app.password_hash):
                    with app.lock:
                        app.failures.setdefault(ip,[]).append(time.time())
                    raise ApiError(401,"AUTH_INVALID","Credenciales inválidas")
                with app.lock:
                    app.failures.pop(ip,None)
                csrf,cookie=app.issue()
                self.response(200,{"ok":True,"data":{"autenticado":True,"csrfToken":csrf}}, {"Set-Cookie":cookie})
                return
            session=app.session(self.headers.get("Cookie"))
            if not session:
                raise ApiError(401,"AUTH_REQUIRED","Inicia sesión")
            if method=="GET":
                params=parse_qs(urlsplit(self.path).query)
                if key=="sesion":
                    data={"autenticado":True,"csrfToken":session["csrf"]}
                elif key=="resumen":
                    data=app.datos.resumen()
                elif key=="reportes":
                    data=app.datos.reportes()
                elif key=="servicios":
                    data=app.datos.servicios()
                    data["preciosEditables"]=app.price_updates_enabled
                elif key in ("citas","clientes"):
                    def positive(name,default,limit):
                        raw=params.get(name,[str(default)])[0]
                        if not raw.isdecimal() or not 1<=int(raw)<=limit:
                            raise ApiError(400,"INVALID_INPUT","Paginación inválida")
                        return int(raw)
                    page=positive("page",1,10000)
                    size=positive("pageSize",20,100)
                    if key=="clientes":
                        buscar=params.get("buscar",params.get("q",[""]))[0]
                        if len(buscar)>100:
                            raise ApiError(400,"INVALID_INPUT","Búsqueda demasiado larga")
                        data=app.datos.clientes(page,size,buscar)
                    else:
                        fecha=params.get("fecha",[None])[0]
                        desde=params.get("desde",[None])[0]
                        for value in (fecha,desde):
                            if value:
                                try:
                                    if datetime.strptime(value,"%Y-%m-%d").strftime("%Y-%m-%d")!=value: raise ValueError()
                                except ValueError:
                                    raise ApiError(400,"INVALID_INPUT","Fecha inválida")
                        data=app.datos.citas(page,size,fecha,desde)
                else:
                    raise ApiError(404,"NOT_FOUND","Ruta no encontrada")
                self.response(200,{"ok":True,"data":data})
                return
            app.authorize(session,self.headers.get("X-CSRF-Token"))
            if key=="servicios/precio":
                if not app.price_updates_enabled:
                    raise ApiError(503,"PRICE_DISABLED","La edición de precios aún no está habilitada")
                body=self.parse()
                if set(body)!={"clave","precio","version"}:
                    raise ApiError(400,"INVALID_INPUT","Se requieren clave, precio y version")
                clave, raw, version=body["clave"],body["precio"],body["version"]
                if not isinstance(clave,str) or not SERVICE_KEY.fullmatch(clave) or clave=="depilacion":
                    raise ApiError(422,"INVALID_SERVICE","Servicio no editable; depilación depende de la zona")
                if not isinstance(raw,str) or not MONEY.fullmatch(raw):
                    raise ApiError(422,"INVALID_PRICE","Indica precio positivo en MXN con máximo dos decimales")
                try:
                    precio=Decimal(raw)
                except InvalidOperation:
                    raise ApiError(422,"INVALID_PRICE","Precio inválido")
                if not Decimal("0")<precio<=Decimal("999999.99"):
                    raise ApiError(422,"INVALID_PRICE","Precio fuera de rango")
                if type(version) is not int or not 1<=version<=9223372036854775806:
                    raise ApiError(422,"INVALID_VERSION","Versión del precio inválida")
                try:
                    data=app.datos.cambiar_precio(clave,precio,version,secrets.token_hex(16))
                except PriceConflict:
                    raise ApiError(409,"PRICE_CONFLICT","El precio cambió; actualiza la lista antes de confirmar")
                self.response(200,{"ok":True,"data":data})
            elif key=="logout":
                app.revoke(self.headers.get("Cookie"))
                cookie=f"{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                if app.secure: cookie+="; Secure"
                self.response(200,{"ok":True,"data":{"autenticado":False}}, {"Set-Cookie":cookie})
            elif key=="mensajes":
                body=self.parse()
                jid=body.get("jid")
                cliente=body.get("cliente_id")
                cita=body.get("cita_id")
                if sum(x is not None for x in (jid,cliente,cita))!=1:
                    raise ApiError(400,"INVALID_INPUT","Indica exactamente un destinatario")
                if not all(isinstance(x,str) and 0<len(x)<=128 for x in (jid,cliente,cita) if x is not None):
                    raise ApiError(400,"INVALID_INPUT","Destinatario inválido")
                text=body.get("texto")
                idem=body.get("idempotencyKey",body.get("idempotencia"))
                if not isinstance(text,str) or not 1<=len(text.strip())<=1000 or any(ord(ch)<32 and ch not in "\n\t" for ch in text):
                    raise ApiError(400,"INVALID_INPUT","Mensaje inválido (1–1000 caracteres)")
                if not isinstance(idem,str) or not KEY.fullmatch(idem):
                    raise ApiError(400,"INVALID_INPUT","idempotencyKey inválida (16–128 caracteres)")
                resolved=app.datos.resolve_jid(jid or cliente,cita)
                if not resolved:
                    raise ApiError(404,"NOT_FOUND","Cliente no registrado en Postgres")
                number=resolved.split("@",1)[0]
                if not PHONE.fullmatch(number) or ("@" in resolved and not resolved.endswith("@s.whatsapp.net")):
                    raise ApiError(422,"INVALID_PHONE","Número del cliente no apto para WhatsApp")
                if app.evolution is None:
                    raise ApiError(503,"SEND_DISABLED","Evolution no configurado")
                app.journal.claim(idem,resolved,text.strip())
                provider_id=app.evolution.send(resolved,text.strip())
                app.journal.mark_sent(idem)
                self.response(200,{"ok":True,"data":{"estado":"aceptado_por_evolution","id":provider_id}})
            else:
                raise ApiError(404,"NOT_FOUND","Ruta no encontrada")
        except ApiError as error:
            self.fail(error)
        except Exception:
            # No exception text: DB DSNs, provider responses, internals must not leak.
            self.fail(ApiError(503,"UNAVAILABLE","Servicio temporalmente no disponible"))

    def do_GET(self): self.run("GET")
    def do_POST(self): self.run("POST")


def main():
    if sys.argv[1:]==["--hash-password"]:
        import getpass
        print(hash_password(getpass.getpass("Contraseña admin (min 12 caracteres): ")))
        return
    required=("ADMIN_DB_DSN","ADMIN_PASSWORD_HASH","ADMIN_SESSION_SECRET","ADMIN_PUBLIC_ORIGIN")
    missing=[key for key in required if not os.getenv(key)]
    if missing: raise SystemExit("Falta configuración: "+", ".join(missing))
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Instala psycopg: python -m pip install 'psycopg[binary]>=3,<4'") from exc
    host=os.getenv("ADMIN_BIND","127.0.0.1")
    port=int(os.getenv("ADMIN_PORT","8765"))
    cert=os.getenv("ADMIN_TLS_CERT")
    key=os.getenv("ADMIN_TLS_KEY")
    if host not in ("localhost","127.0.0.1","::1") and not (cert and key):
        raise SystemExit("Bind externo requiere ADMIN_TLS_CERT y ADMIN_TLS_KEY")
    if (cert is None)!=(key is None):
        raise SystemExit("TLS requiere certificado y llave")
    journal_path=Path(os.getenv("ADMIN_JOURNAL_PATH",str(Path.home()/".barber-admin-sends.sqlite3")))
    if not journal_path.parent.exists():
        raise SystemExit("Crear antes directorio privado ADMIN_JOURNAL_PATH")
    evo=None
    env=(os.getenv("EVOLUTION_URL"),os.getenv("EVOLUTION_API_KEY"),os.getenv("EVOLUTION_INSTANCE"))
    if all(env): evo=Evolution(*env)
    elif any(env): raise SystemExit("Configurar los tres valores EVOLUTION_URL/API_KEY/INSTANCE")
    flag=os.getenv("ADMIN_PRICE_UPDATES_ENABLED","false").lower()
    if flag not in ("true","false"):
        raise SystemExit("ADMIN_PRICE_UPDATES_ENABLED requiere true o false")
    enabled=flag == "true"
    if enabled and not os.getenv("ADMIN_PRICE_DB_DSN"):
        raise SystemExit("ADMIN_PRICE_DB_DSN requerido para editar precios")
    if os.getenv("ADMIN_PRICE_DB_DSN") and os.getenv("ADMIN_PRICE_DB_DSN")==os.getenv("ADMIN_DB_DSN"):
        raise SystemExit("ADMIN_PRICE_DB_DSN debe ser distinto del rol de lectura")
    def connect():
        return psycopg.connect(os.environ["ADMIN_DB_DSN"],connect_timeout=5)
    def connect_price():
        return psycopg.connect(os.environ["ADMIN_PRICE_DB_DSN"],connect_timeout=5)
    app=App(os.environ["ADMIN_PUBLIC_ORIGIN"],os.environ["ADMIN_PASSWORD_HASH"],
            os.environ["ADMIN_SESSION_SECRET"],Datos(connect,connect_price if enabled else None),
            Journal(journal_path),evo,tls=bool(cert),price_updates_enabled=enabled)
    if cert and not app.secure:
        raise SystemExit("ADMIN_PUBLIC_ORIGIN debe ser https con TLS")
    if not cert and app.secure and host not in ("localhost","127.0.0.1","::1"):
        raise SystemExit("TLS en proxy requiere ADMIN_BIND solo loopback")
    if not cert and not app.secure and urlsplit(app.origin).hostname not in ("localhost","127.0.0.1","::1"):
        raise SystemExit("HTTP solo permitido en localhost")
    server=ThreadingHTTPServer((host,port),Handler)
    server.app=app
    if cert:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version=ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert,key)
        server.socket=ctx.wrap_socket(server.socket,server_side=True)
    print("Admin escuchando en",host,port,"(TLS" if cert else "(loopback", ")",flush=True)
    server.serve_forever()


if __name__=="__main__":
    main()
