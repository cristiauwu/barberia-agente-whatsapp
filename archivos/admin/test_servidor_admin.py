"""Hermetic tests: no Postgres access and no Evolution network sends."""
import importlib.util
import io
import json
from decimal import Decimal
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import URLError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor

MOD = Path(__file__).with_name("servidor-admin.py")
spec = importlib.util.spec_from_file_location("servidor_admin", MOD)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeDatos:
    def resumen(self): return {"kpis": {"ingresosHoy": 0}, "hoy": [], "proximas": [], "grafica30": [], "meta": {"advertencia": "Postgres no sincronizado"}}
    def citas(self,*args): return {"items": [], "pagination": {"page": args[0], "pageSize": args[1], "totalItems": 0, "totalPages": 0}, "meta": {}}
    def clientes(self,*args): return self.citas(*args)
    def servicios(self): return {"items": [{"clave":"corte","nombre":"Corte","precio":150,"precioVersion":1,"activo":True},{"clave":"depilacion","nombre":"Depilación","precio":0,"precioVersion":1,"activo":True}], "meta": {}}
    def cambiar_precio(self, clave, precio, version, request_id):
        if clave!="corte" or version!=1: raise mod.PriceConflict()
        assert isinstance(precio,Decimal) and len(request_id)==32
        self.updated=(clave,precio)
        return {"clave":clave,"precio":str(precio),"precioVersion":2}
    def reportes(self): return {"kpis": {}, "grafica30": [], "ocupacion": [], "servicios": [], "meta": {}}
    def resolve_jid(self,cliente_id=None,cita_id=None):
        if cliente_id in ("5214501111805@s.whatsapp.net", "524501111805@s.whatsapp.net",
                          "4501111805@s.whatsapp.net", "521234567890@s.whatsapp.net"):
            return cliente_id
        if cita_id=="CITA-1": return "5214501111805@s.whatsapp.net"
        return None


class FakeEvo:
    def __init__(self): self.sent=[]
    def send(self,jid,text):
        self.sent.append((jid,text))
        return "provider-123"


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.evo=FakeEvo()
        self.server=ThreadingHTTPServer(("127.0.0.1",0),mod.Handler)
        self.origin=f"http://127.0.0.1:{self.server.server_port}"
        self.server.app=mod.App(self.origin,mod.hash_password("correct-password-123"),
                                "x"*64,FakeDatos(),mod.Journal(Path(self.tmp.name)/"journal.sqlite3"),self.evo)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.http=build_opener(HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def req(self,path,body=None,headers=None):
        hdr=headers or {}
        if body is not None:
            hdr={"Content-Type":"application/json","Origin":self.origin,**hdr}
        request=Request(self.origin+path, data=json.dumps(body).encode() if body is not None else None,
                        headers=hdr,method="POST" if body is not None else "GET")
        try:
            with self.http.open(request,timeout=3) as response:
                return response.status,json.loads(response.read()),dict(response.headers)
        except Exception as exc:
            if hasattr(exc,"code") and hasattr(exc,"read"):
                try:
                    return exc.code,json.loads(exc.read()),dict(exc.headers)
                finally:
                    exc.close()
            raise

    def login(self):
        code,data,_=self.req("/api/admin/login", {"password":"correct-password-123"})
        self.assertEqual(code,200)
        return data["data"]["csrfToken"]

    def test_auth_and_empty_real_data(self):
        code,_,_=self.req("/api/admin/resumen")
        self.assertEqual(code,401)
        csrf=self.login()
        self.assertTrue(csrf)
        code,data,_=self.req("/api/admin/sesion")
        self.assertEqual((code,data["data"]["csrfToken"]),(200,csrf))
        for path in ("resumen","citas?desde=2026-09-25","clientes?q=lo","servicios","reportes"):
            code,data,_=self.req("/api/admin/"+path)
            self.assertEqual(code,200)
            self.assertTrue(data["ok"])
        self.assertEqual(self.req("/api/admin/citas?fecha=2026-02-30")[0],400)
        self.assertEqual(self.req("/api/admin/clientes?pageSize=1000")[0],400)

    def test_price_mutation_disabled_by_default_and_catalog_sentinel(self):
        csrf=self.login()
        status,payload,_=self.req('/api/admin/servicios')
        self.assertEqual(status,200)
        self.assertFalse(payload['data']['preciosEditables'])
        self.assertEqual(payload['data']['items'][1]['precio'],0)
        self.assertEqual(self.req('/api/admin/servicios/precio',
                         {'clave':'corte','precio':'180.00','version':1}, {'X-CSRF-Token':csrf})[0],503)

    def test_price_mutation_security_validation_conflict_and_success(self):
        csrf=self.login()
        app=self.server.app
        app.price_updates_enabled=True
        body={'clave':'corte','precio':'180.25','version':1}
        self.assertEqual(self.req('/api/admin/servicios/precio',body)[0],403)
        self.assertEqual(self.req('/api/admin/servicios/precio',body,
                         {'X-CSRF-Token':csrf,'Origin':'https://evil.invalid'})[0],403)
        self.assertEqual(self.req('/api/admin/servicios/precio',body,
                         {'X-CSRF-Token':csrf,'Sec-Fetch-Site':'cross-site'})[0],403)
        bad=[{'clave':'depilacion','precio':'40','version':1},
             {'clave':'corte','precio':0,'version':1},
             {'clave':'corte','precio':'0','version':1},
             {'clave':'corte','precio':'1.234','version':1},
             {'clave':'corte','precio':'NaN','version':1},
             {'clave':'corte','precio':'1e3','version':1},
             {'clave':'corte','precio':'1000000','version':1},
             {'clave':'corte','precio':'10','version':True},
             {'clave':'corte','precio':'10','version':0},
             {'clave':'corte','precio':'10','version':1,'extra':'oops'}]
        for invalid in bad:
            code,_,_=self.req('/api/admin/servicios/precio',invalid,{'X-CSRF-Token':csrf})
            self.assertIn(code,(400,422),invalid)
        code,result,_=self.req('/api/admin/servicios/precio',body,{'X-CSRF-Token':csrf})
        self.assertEqual((code,result['data']['precio'],result['data']['precioVersion']),(200,'180.25',2))
        self.assertEqual(app.datos.updated,('corte',Decimal('180.25')))
        self.assertEqual(self.req('/api/admin/servicios/precio',
            {**body,'version':2},{'X-CSRF-Token':csrf})[0],409)
        self.assertEqual(self.evo.sent,[])

    def test_csrf_origin_idempotency_and_frequency(self):
        csrf=self.login()
        msg={"cita_id":"CITA-1","texto":"Recordatorio privado","idempotencia":"same-intent-123456"}
        self.assertEqual(self.req("/api/admin/mensajes",msg)[0],403)
        self.assertEqual(self.req("/api/admin/mensajes",msg,{"Origin":"https://bad.invalid","X-CSRF-Token":csrf})[0],403)
        code,data,_=self.req("/api/admin/mensajes",msg,{"X-CSRF-Token":csrf})
        self.assertEqual((code,data["data"]["estado"]),(200,"aceptado_por_evolution"))
        self.assertEqual(self.req("/api/admin/mensajes",msg,{"X-CSRF-Token":csrf})[0],409)
        self.assertEqual(self.req("/api/admin/mensajes",{**msg,"texto":"another"},{"X-CSRF-Token":csrf})[0],422)
        self.assertEqual(self.req("/api/admin/mensajes",{**msg,"idempotencia":"different-intent-123456"},{"X-CSRF-Token":csrf})[0],429)
        self.assertEqual(self.evo.sent,[("5214501111805@s.whatsapp.net","Recordatorio privado")])
        self.assertEqual(self.req("/api/admin/logout",{}, {"X-CSRF-Token":csrf})[0],200)
        self.assertEqual(self.req("/api/admin/sesion")[0],401)

    def test_mexican_phone_variants_preserve_registered_jid(self):
        csrf=self.login()
        for index,jid in enumerate(("5214501111805@s.whatsapp.net", "524501111805@s.whatsapp.net",
                                    "4501111805@s.whatsapp.net")):
            body={"cliente_id":jid,"texto":f"Aviso {index}","idempotencyKey":f"unique-message-{index:02d}-123456"}
            code,data,_=self.req("/api/admin/mensajes",body,{"X-CSRF-Token":csrf})
            self.assertEqual((code,data["data"]["estado"]),(200,"aceptado_por_evolution"),jid)
        self.assertEqual([jid for jid,_ in self.evo.sent],
                         ["5214501111805@s.whatsapp.net", "524501111805@s.whatsapp.net", "4501111805@s.whatsapp.net"])

    def test_public_html_and_secure_cookie_rules(self):
        request=Request(self.origin+"/")
        with self.http.open(request,timeout=3) as response:
            self.assertEqual(response.status,200)
            self.assertIn(b"<html", response.read(500).lower())
        _,_,headers=self.req("/api/admin/login",{"password":"correct-password-123"})
        cookie=headers["Set-Cookie"]
        self.assertIn("Path=/;",cookie)
        self.assertIn("HttpOnly",cookie)
        self.assertIn("SameSite=Strict",cookie)
        self.assertNotIn("; Secure",cookie)  # loopback HTTP only
        https=mod.App("https://admin.example.com",mod.hash_password("correct-password-123"),
                      "x"*64,FakeDatos(),mod.Journal(Path(self.tmp.name)/"secure.sqlite3"))
        self.assertIn("; Secure",https.issue()[1])

    def test_login_attempt_limit_and_unknown_provider(self):
        for _ in range(5):
            self.assertEqual(self.req("/api/admin/login",{"password":"incorrect"})[0],401)
        self.assertEqual(self.req("/api/admin/login",{"password":"correct-password-123"})[0],429)
        with self.server.app.lock:
            self.server.app.failures.clear()
        csrf=self.login()
        self.server.app.evolution=None
        body={"cita_id":"CITA-1","texto":"Hello","idempotencia":"provider-down-123456"}
        self.assertEqual(self.req("/api/admin/mensajes",body,{"X-CSRF-Token":csrf})[0],503)
        self.assertEqual(self.req("/api/admin/mensajes",{**body,"cita_id":"missing"},{"X-CSRF-Token":csrf})[0],404)
        class Unknown:
            def send(self,jid,text):
                raise mod.ApiError(502,"SEND_UNKNOWN","Indeterminate")
        self.server.app.evolution=Unknown()
        self.assertEqual(self.req("/api/admin/mensajes",body,{"X-CSRF-Token":csrf})[0],502)
        self.assertEqual(self.req("/api/admin/mensajes",body,{"X-CSRF-Token":csrf})[0],409)

    def test_journal_persists_unknown_after_restart(self):
        path=Path(self.tmp.name)/"durable.sqlite3"
        journal=mod.Journal(path)
        journal.claim("dead-process-123456","521234567890@s.whatsapp.net","hi")
        with self.assertRaises(mod.ApiError) as ctx:
            mod.Journal(path).claim("dead-process-123456","521234567890@s.whatsapp.net","hi")
        self.assertEqual(ctx.exception.status,409)

    def test_parameterized_postgres_queries_with_mock_db(self):
        executed=[]
        class Cursor:
            description=[("total",)]
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def execute(self,sql,params=()):
                executed.append((sql,params))
                self.description=([("total",),("ultimaActualizacion",)] if "max(actualizado_en)" in sql else
                                  [("total",)] if "count(*) AS total" in sql else [("jid",),("nombre",)])
            def fetchall(self):
                if len(self.description)==2 and self.description[0][0]=="total": return [(0,None)]
                return [(0,)] if self.description==[("total",)] else []
        class Connection:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def cursor(self): return Cursor()
        data=mod.Datos(lambda:Connection())
        data.clientes(1,20,"%_\\' OR TRUE")
        sql,params=next((query,values) for query,values in executed if "WHERE (nombre ILIKE" in query)
        self.assertIn("%s",sql)
        self.assertNotIn(" OR TRUE",sql)
        self.assertIn("\\%\\_",params[0])
        self.assertTrue(any(query=="SET TRANSACTION READ ONLY" for query,_ in executed))
        executed.clear()
        data.citas(1,20,desde="2026-09-25")
        self.assertIn(("2026-09-25",20,0), [tuple(values) for _,values in executed])

    def test_price_database_call_is_parameterized_and_uses_separate_connection(self):
        calls=[]
        class Cursor:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def execute(self,sql,params): calls.append((sql,params))
            def fetchone(self): return (Decimal('175.50'),3)
        class Connection:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def cursor(self): return Cursor()
        def read_only(): raise AssertionError('price writer must not use SELECT credential')
        data=mod.Datos(read_only,lambda:Connection())
        result=data.cambiar_precio('corte',Decimal('175.50'),2,'a'*32)
        self.assertEqual(result['precioVersion'],3)
        self.assertIn('admin_cambiar_precio(%s, %s::numeric, %s, %s::uuid)',calls[0][0])
        self.assertEqual(calls[0][1],('corte',Decimal('175.50'),2,'a'*32))
        class ConflictCursor(Cursor):
            def fetchone(self): return None
        Connection.cursor=lambda self: ConflictCursor()
        with self.assertRaises(mod.PriceConflict):
            data.cambiar_precio('missing',Decimal('175.50'),2,'b'*32)

    def test_evolution_mocked_provider_validation(self):
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'{"key":{"id":"abc"}}'
        requests=[]
        def opener(req,timeout):
            requests.append(req)
            return Response()
        evo=mod.Evolution("http://localhost:8080","secret","hector",opener)
        self.assertEqual(evo.send("521234567890@s.whatsapp.net","hi"),"abc")
        self.assertEqual(json.loads(requests[0].data),{"number":"521234567890@s.whatsapp.net","text":"hi"})
        self.assertEqual(evo.send("5214501111805@s.whatsapp.net","hola"),"abc")
        self.assertEqual(json.loads(requests[1].data),{"number":"5214501111805@s.whatsapp.net","text":"hola"})
        self.assertEqual(requests[0].headers["Apikey"],"secret")
        fail=mod.Evolution("http://localhost:8080","secret","hector",lambda req,timeout: (_ for _ in ()).throw(URLError("timeout")))
        with self.assertRaises(mod.ApiError) as ctx:
            fail.send("521234567890@s.whatsapp.net","hi")
        self.assertEqual(ctx.exception.code,"SEND_UNKNOWN")


if __name__=="__main__":
    unittest.main()
