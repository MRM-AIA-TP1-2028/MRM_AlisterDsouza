import socket, threading, json, sqlite3, hashlib, hmac, os, re, sys, time, getpass
 
PORT, ROOM, DB = 5000, "#general", "chat.db"
online, lock, send_lock = {}, threading.Lock(), threading.Lock()
 
 

def q(sql, args=()):
    c = sqlite3.connect(DB)
    try:
        rows = c.execute(sql, args).fetchall()
        c.commit()
        return rows
    finally:
        c.close()
 
def h(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
 
 

def send(sock, obj):
    with send_lock:
        try:
            sock.sendall((json.dumps(obj) + "\n").encode())
        except OSError:
            pass
 
def valid(to, me):
    return to == ROOM or bool(q("SELECT 1 FROM users WHERE username=?", (to,)))
 
def serve(conn):
    f, me = conn.makefile("r", encoding="utf-8"), None
    err = lambda why: send(conn, {"type": "error", "reason": why})
    try:
        for line in f: 
            try:
                r = json.loads(line); t = r["type"]
            except (ValueError, KeyError, TypeError):
                continue
 
            if me is None: 
                if t not in ("register", "login"):
                    err("login first"); continue
                u, pw = str(r.get("username", "")).strip().lower(), str(r.get("password", ""))
                if not re.fullmatch(r"[a-z0-9_]{3,20}", u):
                    err("username: 3-20 letters/digits/underscore"); continue
                if t == "register":
                    if len(pw) < 6:
                        err("password needs 6+ chars"); continue
                    salt = os.urandom(16)
                    try:
                        q("INSERT INTO users VALUES(?,?,?)", (u, salt, h(pw, salt)))
                    except sqlite3.IntegrityError:
                        err("username taken"); continue
                else:
                    row = q("SELECT salt, pw FROM users WHERE username=?", (u,))
                    if not row or not hmac.compare_digest(h(pw, row[0][0]), row[0][1]):
                        time.sleep(1); err("wrong username or password"); continue
                with lock:             
                    online.setdefault(u, []).append(conn)
                me = u
                send(conn, {"type": "ok", "username": u})
 
            elif t == "msg":
                to, body = str(r.get("to", "")).strip().lower(), str(r.get("body", "")).strip()
                if not body or len(body) > 1000 or not valid(to, me):
                    err("bad message or unknown recipient"); continue
                ts = time.time()
                q("INSERT INTO messages(sender,recipient,body,ts) VALUES(?,?,?,?)", (me, to, body, ts))
                with lock:
                    targets = [c for cs in online.values() for c in cs if c is not conn] if to == ROOM else \
                              [c for c in online.get(to, []) if c is not conn]
                for c in targets:
                    send(c, {"type": "msg", "from": me, "to": to, "body": body, "ts": ts})
                send(conn, {"type": "sent", "to": to, "delivered": bool(targets) or to == ROOM})
 
            elif t == "history":
                w = str(r.get("with", "")).strip().lower()
                if not valid(w, me):
                    err("unknown chat"); continue
                rows = q("SELECT sender,body,ts FROM messages WHERE recipient=? ORDER BY id DESC LIMIT 50", (ROOM,)) \
                    if w == ROOM else \
                    q("SELECT sender,body,ts FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) "
                      "ORDER BY id DESC LIMIT 50", (me, w, w, me))
                send(conn, {"type": "history", "with": w,
                            "messages": [{"sender": a, "body": b, "ts": c} for a, b, c in rows[::-1]]})
 
            elif t == "users":
                with lock:
                    on = set(online)
                send(conn, {"type": "users", "users": [[u, u in on] for (u,) in q("SELECT username FROM users ORDER BY 1")]})
            else:
                err("unknown command")
    except (OSError, ValueError):
        pass
    finally:
        if me:
            with lock:
                if conn in online.get(me, []):
                    online[me].remove(conn)
                    if not online[me]:
                        del online[me]
        conn.close()
 
def server():
    q("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt BLOB, pw BLOB)")
    q("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, body TEXT, ts REAL)")
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))
    s.listen()
    s.settimeout(1)
    try:
        t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); t.connect(("8.8.8.8", 80)); ip = t.getsockname()[0]
    except OSError:
        ip = "(run ipconfig)"
    print(f"Server up. Clients connect to {ip}:{PORT}")
    try:
        while True:
            try:
                c, _ = s.accept()
            except socket.timeout:
                continue
            c.settimeout(None)
            threading.Thread(target=serve, args=(c,), daemon=True).start()
    except KeyboardInterrupt:
        pass
 
 

def client(host):
    s = socket.create_connection((host, PORT))
    f = s.makefile("r", encoding="utf-8")
    tx = lambda d: s.sendall((json.dumps(d) + "\n").encode())
    cur = [None]
 
    while True:
        k = input("(l)ogin or (r)egister? ").strip().lower()[:1]
        if k not in ("l", "r"):
            continue
        tx({"type": "login" if k == "l" else "register",
            "username": input("Username: "), "password": getpass.getpass("Password: ")})
        r = json.loads(f.readline() or sys.exit("server closed"))
        if r["type"] == "ok":
            me = r["username"]; break
        print("X", r["reason"])
 
    def show(m):
        return f"[{time.strftime('%H:%M', time.localtime(m['ts']))}] {'you' if m['sender'] == me else m['sender']}: {m['body']}"
 
    def listen():
        for line in f:
            m = json.loads(line); t = m["type"]
            if t == "msg":
                chat = ROOM if m["to"] == ROOM else m["from"]
                who = "" if m["from"] == me else m["from"]
                print("\n" + show({**m, "sender": who}) if chat == cur[0] else f"\n🔔 new message in {chat}")
            elif t == "history":
                cur[0] = m["with"]; print(f"\n--- {m['with']} ---")
                for x in m["messages"]: print(show(x))
            elif t == "users":
                print("\nUsers:", ", ".join(("{G} " if o else "{R} ") + u for u, o in m["users"]))
            elif t == "error":
                print("\n✗", m["reason"])
            elif t == "sent" and not m["delivered"]:
                print("\n(saved - no other window of yours is open)" if m["to"] == me else
                      f"\n(saved - {m['to']} is offline, they'll see it in history)")
            print("> ", end="", flush=True)
        print("\n[disconnected]"); os._exit(0)
 
    threading.Thread(target=listen, daemon=True).start()
    print("Commands: /chat <user|#general>   /users   /quit")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line == "/quit": break
        elif line == "/users": tx({"type": "users"})
        elif line.startswith("/chat "):
            cur[0] = line[6:].strip().lower(); tx({"type": "history", "with": cur[0]}) # type: ignore
        elif line.startswith("/"): print("unknown command")
        elif line and cur[0]: tx({"type": "msg", "to": cur[0], "body": line})
        elif line: print("open a chat first: /chat <user>")
 
 
if __name__ == "__main__":
    a = sys.argv
    if len(a) > 1 and a[1] == "server": server()
    elif len(a) > 2 and a[1] == "client": client(a[2])
    else: print("usage: python chat.py server   |   python chat.py client <server-ip>")