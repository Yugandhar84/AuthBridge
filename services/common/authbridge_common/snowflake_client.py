"""Snowflake access for the local services: SQL (stored procedures, views) and
the Cortex Agents REST API.

Authentication is key-pair (preferred) or a programmatic access token (PAT).
Credentials come from .env and never reach the browser.
"""

import base64
import hashlib
import json
import queue
import threading
import time
from contextlib import contextmanager

import httpx


class SnowflakeSQL:
    """Tiny connection pool around snowflake-connector-python."""

    def __init__(self, settings, size=4):
        self.s = settings
        self._pool = queue.Queue(maxsize=size)
        self._size = size
        self._created = 0
        self._lock = threading.Lock()

    def _connect(self):
        import snowflake.connector  # imported lazily so mock mode needs no driver

        kwargs = dict(
            account=self.s.sf_account, user=self.s.sf_user, role=self.s.sf_role,
            warehouse=self.s.sf_warehouse, database=self.s.sf_database,
            client_session_keep_alive=True, application="AuthBridge",
        )
        if self.s.sf_private_key_path:
            kwargs["private_key_file"] = self.s.sf_private_key_path
            if self.s.sf_private_key_passphrase:
                kwargs["private_key_file_pwd"] = self.s.sf_private_key_passphrase
        elif self.s.sf_pat:
            # A PAT can be supplied as the password for driver connections.
            kwargs["password"] = self.s.sf_pat
        else:
            raise RuntimeError("Set SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PAT for %s" % self.s.service)
        return snowflake.connector.connect(**kwargs)

    @contextmanager
    def connection(self):
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._created < self._size:
                    self._created += 1
                    conn = self._connect()
                else:
                    conn = None
            if conn is None:
                conn = self._pool.get(timeout=30)
        try:
            yield conn
        finally:
            self._pool.put(conn)

    def query(self, sql, params=None):
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql, params or [])
                cols = [c[0].lower() for c in cur.description or []]
                return [dict(zip(cols, [_decode(v) for v in row])) for row in cur.fetchall()]
            finally:
                cur.close()

    def execute(self, sql, params=None):
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql, params or [])
                return cur.rowcount
            finally:
                cur.close()

    def call(self, procedure, *args):
        """CALL a procedure that returns VARIANT; JSON-ish args are passed as strings."""
        placeholders = ", ".join(["%s"] * len(args))
        prepared = [json.dumps(a) if isinstance(a, (dict, list)) else a for a in args]
        rows = self.query("CALL %s(%s)" % (procedure, placeholders), prepared)
        if not rows:
            return None
        value = list(rows[0].values())[0]
        return value


def _decode(v):
    if isinstance(v, str) and v[:1] in ("{", "["):
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


class CortexAgents:
    """Calls POST /api/v2/databases/{db}/schemas/{schema}/agents/{name}:run and
    yields simplified events for the UI: text, status, table, chart, error, done."""

    def __init__(self, settings):
        self.s = settings
        host = settings.sf_host or "%s.snowflakecomputing.com" % settings.sf_account.replace("_", "-").lower()
        self.base = host if host.startswith("http") else "https://" + host
        self._jwt = None
        self._jwt_exp = 0

    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self.s.sf_role:
            h["X-Snowflake-Role"] = self.s.sf_role
        if self.s.sf_private_key_path:
            h["Authorization"] = "Bearer " + self._keypair_jwt()
            h["X-Snowflake-Authorization-Token-Type"] = "KEYPAIR_JWT"
        elif self.s.sf_pat:
            h["Authorization"] = "Bearer " + self.s.sf_pat
            h["X-Snowflake-Authorization-Token-Type"] = "PROGRAMMATIC_ACCESS_TOKEN"
        else:
            raise RuntimeError("No Snowflake credentials configured for the Agents API")
        return h

    def _keypair_jwt(self):
        if self._jwt and time.time() < self._jwt_exp - 60:
            return self._jwt
        import jwt
        from cryptography.hazmat.primitives import serialization

        with open(self.s.sf_private_key_path, "rb") as f:
            pw = self.s.sf_private_key_passphrase.encode() if self.s.sf_private_key_passphrase else None
            key = serialization.load_pem_private_key(f.read(), password=pw)
        pub = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(pub).digest()).decode()
        account = self.s.sf_account.split(".")[0].upper()
        user = self.s.sf_user.upper()
        now = int(time.time())
        payload = {"iss": "%s.%s.%s" % (account, user, fingerprint), "sub": "%s.%s" % (account, user),
                   "iat": now, "exp": now + 3600}
        self._jwt = jwt.encode(payload, key, algorithm="RS256")
        self._jwt_exp = now + 3600
        return self._jwt

    def run(self, agent, message, schema="AI", thread_id=None, parent_message_id=None):
        url = "%s/api/v2/databases/%s/schemas/%s/agents/%s:run" % (self.base, self.s.sf_database, schema, agent)
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": message}]}]}
        if thread_id is not None:
            body["thread_id"] = thread_id
            body["parent_message_id"] = parent_message_id or 0
        with httpx.stream("POST", url, headers=self._headers(), json=body, timeout=httpx.Timeout(900, connect=20)) as r:
            if r.status_code >= 400:
                yield {"type": "error", "message": "Agent call failed (%s): %s" % (r.status_code, r.read().decode()[:500])}
                return
            event = None
            for line in r.iter_lines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    simplified = simplify_agent_event(event, data)
                    if simplified:
                        yield simplified
        yield {"type": "done"}


def simplify_agent_event(event, data):
    try:
        payload = json.loads(data) if data else {}
    except ValueError:
        payload = {"raw": data}
    if event == "response.text.delta":
        return {"type": "text", "text": payload.get("text", "")}
    if event == "response.status":
        return {"type": "status", "message": payload.get("message") or payload.get("status")}
    if event == "response.thinking.delta":
        return None
    if event == "response.table":
        return {"type": "table", "result_set": payload.get("result_set", payload)}
    if event == "response.chart":
        return {"type": "chart", "spec": payload.get("chart_spec", payload)}
    if event == "response.text.annotation":
        return {"type": "annotation", "annotation": payload.get("annotation", payload)}
    if event == "response.tool_result":
        return {"type": "status", "message": "Tool finished: %s" % payload.get("name", "")}
    if event == "error":
        return {"type": "error", "message": payload.get("message", data)}
    return None
