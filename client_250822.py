import socket
import json

SERVER_IP = input("Input server ip (Default: 127.0.0.1): ").strip() or "127.0.0.1"
SERVER_PORT = input("Input server port (Default: 65535): ").strip()
SERVER_PORT = int(SERVER_PORT) if SERVER_PORT.isdigit() else 65535


def _recv_until_newline(sock: socket.socket, timeout: float = 60.0) -> bytes:
    sock.settimeout(timeout)
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            if not buf:
                raise ConnectionError(
                    "Server closed the connection before sending data."
                )
            break
        buf += chunk
        if b"\n" in chunk:
            break
    nl = buf.find(b"\n")
    if nl == -1:
        raise ConnectionError("No newline terminator in response.")
    return buf[:nl]


def send_request(sock: socket.socket, payload: dict) -> dict:
    raw = json.dumps(payload) + "\n"
    sock.sendall(raw.encode("utf-8"))
    data = _recv_until_newline(sock)
    return json.loads(data.decode("utf-8"))


def _is_complete_json_braces(s: str) -> bool:
    count = 0
    in_str = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if in_str:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                count += 1
            elif ch == "}":
                count -= 1
    return (count == 0) and (not in_str)


def _read_multiline_json_block(first_line: str) -> str:
    stripped = first_line.strip()

    if stripped.startswith("```"):
        lines = []
        while True:
            line = input("... ")
            if line.strip() == "```":
                break
            lines.append(line)
        return "\n".join(lines)

    buf = first_line
    if _is_complete_json_braces(buf):
        return buf
    while True:
        line = input("... ")
        buf += "\n" + line
        if _is_complete_json_braces(buf):
            return buf
    return buf


def prompt_loop():
    current_mode = "employee"
    print("Enter raw JSON or commands. Idle timeout: 60s.")
    while True:
        user_input = input(f"[{current_mode.upper()}] >>> ")
        if user_input.strip() == "":
            continue
        if user_input.strip().lower() == "exit":
            print("Disconnected. Bye!")
            break

        payload = None
        first_nonspace = user_input.lstrip()

        if first_nonspace.startswith("{") or first_nonspace.startswith("```"):
            try:
                raw_json_text = _read_multiline_json_block(user_input)
                payload = json.loads(raw_json_text)
            except json.JSONDecodeError as e:
                print(f"[Input Error] Invalid JSON: {e}")
                continue

        else:
            try:
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                params = parts[1] if len(parts) > 1 else ""
                payload = {"mode": current_mode}

                if cmd == "mode":
                    if not params:
                        raise ValueError("Mode target required.")
                    payload["action"] = "set_mode"
                    payload["params"] = {"target": params.lower()}
                elif cmd == "show" and params.lower() == "all":
                    payload["action"] = "show_all"
                elif cmd == "show" and params.lower().startswith("id "):
                    id_str = params[3:].strip()
                    if not id_str.isdigit():
                        raise ValueError("ID must be number.")
                    payload["action"] = "show_id"
                    payload["params"] = {"id": int(id_str)}
                elif cmd == "show_id":
                    if not params.isdigit():
                        raise ValueError("ID must be number.")
                    payload["action"] = "show_id"
                    payload["params"] = {"id": int(params)}
                elif cmd == "show" and params.lower().startswith("name "):
                    name_val = params[5:].strip()
                    if not name_val:
                        raise ValueError("Name required.")
                    payload["action"] = "show_name"
                    payload["params"] = {"name": name_val}
                elif cmd == "show_name":
                    if not params:
                        raise ValueError("Name required.")
                    payload["action"] = "show_name"
                    payload["params"] = {"name": params.strip()}
                elif cmd == "del_id":
                    if not params.isdigit():
                        raise ValueError("ID must be number.")
                    payload["action"] = "del_id"
                    payload["params"] = {"id": int(params)}
                else:
                    payload["action"] = "save"
                    if current_mode == "employee":
                        parts_data = [x.strip() for x in user_input.split(",")]
                        if len(parts_data) != 4:
                            raise ValueError("Requires name,phone,email,dept.")
                        name, phone, email, dept = parts_data
                        payload["params"] = {
                            "name": name,
                            "phone": phone,
                            "email": email,
                            "dept": dept,
                        }
                    else:
                        if not user_input:
                            raise ValueError("Command required.")
                        payload["params"] = {"command": user_input}

            except ValueError as e:
                print(f"[Input Error] {e}")
                continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(60)
                sock.connect((SERVER_IP, SERVER_PORT))
                try:
                    resp = send_request(sock, payload)
                except socket.timeout:
                    print("[Timeout] No response within 60 seconds.")
                    continue

        except Exception as e:
            print(f"[Connection Error] {e}")
            continue

        if resp.get("status") == "ok":
            if resp.get("mode") and payload.get("action") == "set_mode":
                current_mode = resp["mode"]
            if "data" in resp:
                print(json.dumps(resp["data"], indent=2, ensure_ascii=False))
            elif "deleted" in resp:
                print("Deleted" if resp["deleted"] else "No record removed.")
            elif "message" in resp:
                print(resp["message"])
        else:
            print(f"[Server Error] {resp.get('error')}")
            if resp.get("detail"):
                print(f"[Detail] {resp.get('detail')}")


if __name__ == "__main__":
    prompt_loop()
