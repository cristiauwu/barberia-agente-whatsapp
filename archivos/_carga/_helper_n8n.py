"""Helper de la API de n8n."""
import json
import urllib.request
import urllib.error

N8N = "http://localhost:5678"
KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
       "eyJzdWIiOiJjYmQ1ZGQ2Yi05NzJlLTRlZmYtYWVlNC03MTAzOWJmM2E5MDIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmZkZmNiNDQtZmRiMi00MDUwLTg3MWMtMGJkMDI5NGRiOTYwIiwiaWF0IjoxNzkwMjk4ODczfQ."
       "s04weO8S72yEn6ip2rCGE4wCt-wPw22xVWJij-lF4wc")


def call(method, path, body=None, timeout=30):
    url = N8N + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed
    except Exception as e:
        return -1, str(e)


def get(path):
    return call("GET", path)


def post(path, body=None):
    return call("POST", path, body if body is not None else {})


def put(path, body):
    return call("PUT", path, body)


def list_workflows():
    st, data = get("/api/v1/workflows?limit=250")
    return data


if __name__ == "__main__":
    st, d = list_workflows()
    print("status", st)
    for w in (d or {}).get("data", []):
        print(w["id"], "|", w["name"], "| active=", w.get("active"), "| nodes=", len(w.get("nodes", [])))