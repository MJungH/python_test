import socket
import threading
import pymysql
import pymysql.cursors
import json

HOST = "0.0.0.0"
PORT = 65535
client_sessions = {}
# 키는 클라이언트 IP, 값은 현재 모드("employee" 또는 "cli"), 클라이언트가 재연결해도 모드를 유지할 수 있도록 저장


def handle_client(data: bytes, addr):
    ip = addr[0]
    # JSON 파싱 및 유효성 검증
    try:
        req = json.loads(data.decode().strip())
        # 클라이언트의 요청을 파싱. 바이트 → 문자열 → 불필요 공백 제거
    except json.JSONDecodeError as e:
        return (
            json.dumps(
                {"status": "error", "error": "Invalid JSON format", "detail": str(e)}
            )
            + "\n"
        )
        # json.loads() 실패 시, 에러 메시지 포함해 즉시 반환

    mode = req.get("mode")
    action = req.get("action")
    if isinstance(action, str):
        action = action.replace(" ", "_")
        # action에 공백이 있으면 언더바로 대체
    params = req.get("params", {})
    if mode not in ("employee", "cli") or not action:
        return (
            json.dumps({"status": "error", "error": "Invalid request parameters"})
            + "\n"
        )

    try:
        db = pymysql.connect(
            host="10.10.1.122",
            user="jhmoon",
            password="20120507",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        cursor = db.cursor()
    except pymysql.MySQLError as e:
        return (
            json.dumps(
                {"status": "error", "error": "DB connection failed", "detail": str(e)}
            )
            + "\n"
        )

    if action == "set_mode":
        target = params.get("target")
        if target in ("employee", "cli"):
            client_sessions[ip] = target
            return (
                json.dumps(
                    {
                        "status": "ok",
                        "mode": target,
                        "message": f"Mode changed to {target.upper()}",
                    }
                )
                + "\n"
            )
            # 모드 변경 처리
        else:
            return (
                json.dumps({"status": "error", "error": "Invalid mode specified"})
                + "\n"
            )

    current_mode = client_sessions.get(ip, mode)
    jresp = {"status": "ok", "mode": current_mode}
    # 세션에 저장된 모드가 있으면 사용, 없으면 요청받은 mode 사용

    try:
        cursor.execute(f"USE {current_mode};")
        if action == "show_all":
            table = "employees" if current_mode == "employee" else "commands"
            cursor.execute(f"SELECT * FROM {table} ORDER BY id ASC LIMIT 100")
            rows = cursor.fetchall()
            if current_mode == "employee":
                jresp["data"] = [
                    {
                        "id": r[0],
                        "name": r[1],
                        "phone": r[2],
                        "email": r[3],
                        "department": r[4],
                        "timestamp": str(r[5]),
                    }
                    for r in rows
                ]
            else:
                jresp["data"] = [
                    {
                        "id": r[0],
                        "command": r[1],
                        "timestamp": (r[2].isoformat() if r[2] else None),
                    }
                    for r in rows
                ]

        elif action == "show_id":
            id_val = params.get("id")
            if not isinstance(id_val, int):
                raise ValueError("ID must be an integer for show_id")
            table = "employees" if current_mode == "employee" else "commands"
            query = (
                "SELECT id, name, phone, email, department FROM employees WHERE id = %s"
                if current_mode == "employee"
                else "SELECT id, command FROM commands WHERE id = %s"
            )
            cursor.execute(query, (id_val,))
            row = cursor.fetchone()
            if not row:
                jresp["data"] = None
            else:
                if current_mode == "employee":
                    jresp["data"] = dict(
                        zip(["id", "name", "phone", "email", "department"], row)
                    )
                else:
                    jresp["data"] = {"id": row[0], "command": row[1]}

        elif action == "show_name" and current_mode == "employee":
            name = params.get("name")
            if not name:
                raise ValueError("Name parameter is required for show_name")
            cursor.execute(
                "SELECT id, name, phone, email, department FROM employees WHERE name = %s",
                (name,),
            )
            rows = cursor.fetchall()
            jresp["data"] = (
                None
                if not rows
                else [
                    dict(zip(["id", "name", "phone", "email", "department"], r))
                    for r in rows
                ]
            )

        elif action == "del_id":
            id_val = params.get("id")
            if not isinstance(id_val, int):
                raise ValueError("ID must be an integer for del_id")
            table = "employees" if current_mode == "employee" else "commands"
            cursor.execute(f"DELETE FROM {table} WHERE id = %s", (id_val,))
            db.commit()
            jresp["deleted"] = cursor.rowcount > 0

        elif action == "save":
            if current_mode == "employee":
                name = params.get("name")
                phone = params.get("phone")
                email = params.get("email")
                dept = params.get("dept")
                if not all([name, phone, email, dept]):
                    raise ValueError("All employee fields are required")
                cursor.execute(
                    "INSERT INTO employees (name, phone, email, department) VALUES (%s,%s,%s,%s)",
                    (name, phone, email, dept),
                )
                db.commit()
                jresp["message"] = f"Saved: {name}"
            else:
                cmd = params.get("command")
                if not cmd:
                    raise ValueError("Command text required for CLI save")
                cursor.execute("INSERT INTO commands (command) VALUES (%s)", (cmd,))
                db.commit()
                jresp["message"] = f"Saved command: {cmd}"
        else:
            jresp = {"status": "error", "error": "Unknown action or mode"}

    except (ValueError, KeyError) as e:
        jresp = {"status": "error", "error": "Invalid input: " + str(e)}
    except pymysql.err.IntegrityError as e:
        jresp = {"status": "error", "error": "Data integrity error", "detail": str(e)}
    except pymysql.MySQLError as e:
        jresp = {"status": "error", "error": "SQL execution failed", "detail": str(e)}
    except Exception as e:
        jresp = {"status": "error", "error": "Internal server error", "detail": str(e)}
    finally:
        cursor.close()
        db.close()

    return json.dumps(jresp) + "\n"


def handle_single_connection(conn, addr):
    print(f"[Server] Connected: {addr}")
    # 60초 동안 recv() 대기 후 데이터가 없으면 socket.timeout 예외 발생
    conn.settimeout(60)
    buf = bytearray()
    try:
        while True:
            try:
                chunk = conn.recv(4096)
                # 클라이언트가 정상 종료했거나 빈 데이터를 보냈을 때
                if not chunk:
                    print(f"[Server] Client at {addr} disconnected cleanly.")
                    break
                buf += chunk

                while True:
                    nl = buf.find(b"\n")
                    if nl == -1:
                        break
                    line = bytes(buf[:nl])  # '\n' 제외
                    del buf[: nl + 1]  # 다음 메시지 대비
                    response = handle_client(line, addr)
                    conn.sendall(response.encode("utf-8"))

            except socket.timeout:
                # 60초 동안 입력이 없으면 타임아웃 처리
                print(f"[Server] No input from {addr} for 60 seconds. Closing session.")
                break

    except Exception as e:
        print(f"[Server] Unexpected error with {addr}: {e}")

    finally:
        conn.close()
        print(f"[Server] Connection closed: {addr}")


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[Server] Listening on {HOST}:{PORT}")
    while True:
        conn, addr = server_socket.accept()
        threading.Thread(
            target=handle_single_connection, args=(conn, addr), daemon=True
        ).start()
    # accept() 대기 → 새 연결이 들어오면 바로 스레드로 넘김
    # 메인 스레드는 계속 대기 상태 유지 → 다중 클라이언트 동시 처리 가능


if __name__ == "__main__":
    start_server()
