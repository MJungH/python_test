# Multi client 입력 서버

import socket  # tcp/ip socket module load
import pymysql  # mysql module load
import pymysql.cursors
import threading

HOST = "0.0.0.0"  # 모든 IP로부터 접속 허용
PORT = 65535  # 사용할 포트


def handle_client(conn, addr):
    # 클라이언트 한개에 대한 처리. 해당 함수는 thread로 실행
    print(f"Connected: {addr}")
    # 문자열 앞에 f를 붙이면, 중괄호와 변수 이름만으로 문자열에 원하는 변수를 삽입할 수 있음.

    # MySQL 연결, 각 thread 마다 별도로 DB 연결
    try:
        db = pymysql.connect(
            host="10.10.1.122",
            user="jhmoon",
            password="20120507",
            database="employee",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,  # 기본 커서
        )
        cursor = db.cursor()
        current_mode = "employee"  # 기본 모드 설정
    except pymysql.MySQLError as e:
        print(f"DB connection failed : {e}")
        exit(0)

    try:
        while True:
            try:
                data = conn.recv(1024)  # 클라이언트로부터 데이터를 1024바이트까지 받음
            except socket.timeout:
                print(f"[{addr}] Timeout, closing connection")
                break

            if not data:
                print(f"Disconnected from {addr}. Bye Bye!!")
                break

            input_str = (
                data.decode().strip()
            )  # 문자열 decode, .strip()을 사용하여 공백 입력 제거
            print(f"[{addr}] Received: {input_str}")

            if input_str.lower() == "mode cli":
                try:
                    cursor.execute("USE cli;")
                    current_mode = "cli"
                    response = "[Server] Mode changed to CLI.\n"
                except pymysql.MySQLError as e:
                    response = f"[Server] Failed to switch CLI DB:{e}\n"
                conn.sendall(response.encode("utf-8"))

            elif input_str.lower() == "mode employee":
                try:
                    cursor.execute("USE employee;")
                    current_mode = "employee"
                    response = "[Server] Mode changed to EMPLOYEE.\n"
                except pymysql.MySQLError as e:
                    response = f"[Server] Failed to switch EMPLOYEE DB:{e}\n"
                conn.sendall(response.encode("utf-8"))

            elif current_mode == "employee":
                response = ""
                if input_str.lower() == "show all":
                    # 저장되어 있는 목록 조회
                    cursor.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 20")
                    rows = (
                        cursor.fetchall()
                    )  # 레코드를 배열 형식으로 저장된 항목을 모두 가져옴
                    if not rows:
                        response = "No saved list.\n"
                    else:
                        response = "[Recent 10 list]\n"  # response 변수 초기화
                        for row in rows:
                            response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} | timestamp: {row[5]} \n"
                    conn.sendall(response.encode("utf-8"))

                elif input_str.lower().startswith("show id "):
                    # id로 조회
                    parts = input_str.split()
                    if len(parts) >= 3:
                        try:
                            target_id = int(parts[2])
                            # 입력된 문자열에서 두번째 단어를 가지고오는 구문
                            cursor.execute(
                                "SELECT id, name, phone, email, department FROM employees WHERE id = %s",
                                (target_id,),
                            )
                            row = cursor.fetchone()
                            # 레코드를 배열 형식으로 저장된 항목을 특정하나만 가져옴
                            if not row:
                                response = (
                                    f"[Server] No record found with ID {target_id}\n"
                                )
                            else:
                                response = "[Search result]\n"
                                response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} \n"
                        except ValueError:
                            response = "[Server] ID must be a number.\n"
                    else:
                        response = "[Server] Invalid format. Use : show id <number>\n"
                    conn.sendall(response.encode("utf-8"))

                elif input_str.lower().startswith("show name "):
                    try:
                        # name으로 조회
                        target_name = input_str[10:].strip()
                        # name^ 이후 전체 문자열 가지고오는 구문
                        cursor.execute(
                            "SELECT id, name, phone, email, department FROM employees WHERE name = %s",
                            (target_name,),
                        )
                        rows = cursor.fetchall()
                        # 이름에 중복된 결과가 있을 수 있어 fetchall 사용(복수 결과)
                        if not rows:
                            response = (
                                f"[Server] No record found with name {target_name}\n"
                            )
                        else:
                            response = "[Search result]\n"
                            for row in rows:
                                response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} \n"
                    except ValueError:
                        response = "[Server] Name must be a alphabet\n"
                    conn.sendall(response.encode("utf-8"))

                elif input_str.lower().startswith("del id "):
                    # 저장되어 있는 목록 삭제
                    parts = input_str.split()
                    if len(parts) >= 3:
                        try:
                            target_id = int(parts[2])
                            cursor.execute(
                                "DELETE FROM employees WHERE id = %s", (target_id,)
                            )
                            db.commit()
                            if cursor.rowcount > 0:
                                response = f"[Server] ID {target_id} delete complete\n"
                            else:
                                response = f"[Server] ID {target_id} is not found\n"
                        except ValueError:
                            response = "[Server] ID must be a number.\n"
                    else:
                        response = "[Server] Invalid format. Use : del id <number>\n"
                    conn.sendall(response.encode("utf-8"))

                else:
                    try:
                        name, phone, email, dept = [
                            x.strip() for x in input_str.split(",")
                        ]
                        cursor.execute(
                            "INSERT INTO employees (name, phone, email, department) VALUES (%s, %s, %s, %s)",
                            (name, phone, email, dept),
                        )
                        db.commit()
                        response = f"[Server] Information saved successfully: {name}\n"
                        print(
                            f"[Server] Save complete: {name}, {phone}, {email}, {dept}"
                        )
                    except ValueError:
                        response = "[Server] Input format error: Please enter name, phone number, email, department format.\n"
                    conn.sendall(response.encode("utf-8"))

            elif current_mode == "cli":
                response = ""
                if input_str.lower() == "show all":
                    # 저장되어 있는 목록 조회
                    cursor.execute("SELECT * FROM commands ORDER BY id DESC LIMIT 20")
                    rows = (
                        cursor.fetchall()
                    )  # 레코드를 배열 형식으로 저장된 항목을 모두 가져옴
                    if not rows:
                        response = "No saved list.\n"
                    else:
                        response = "[Recent 10 list]\n"  # response 변수 초기화
                        for row in rows:
                            response += f"{row[0]} | {row[1]} | {row[2]} \n"
                    conn.sendall(response.encode("utf-8"))

                elif input_str.lower().startswith("show id "):
                    # Cli id로 조회
                    parts = input_str.split()
                    if len(parts) >= 3:
                        try:
                            target_id = int(parts[2])
                            cursor.execute(
                                "SELECT id, command FROM commands WHERE id = %s",
                                (target_id,),
                            )
                            row = cursor.fetchone()
                            if not row:
                                response = (
                                    f"[Server] No record found with ID {target_id}\n"
                                )
                            else:
                                response = "[Search result]\n"
                                response += f"ID: {row[0]} | Command: {row[1]}\n"
                        except ValueError:
                            response = "[Server] ID must be a number.\n"
                    else:
                        response = "[Server] Invalid format. Use : show id <number>\n"
                    conn.sendall(response.encode("utf-8"))

                elif input_str.lower().startswith("del id "):
                    # 저장 목록 삭제
                    parts = input_str.split()
                    if len(parts) >= 3:
                        try:
                            target_id = int(parts[2])
                            cursor.execute(
                                "DELETE FROM commands WHERE id = %s", (target_id,)
                            )
                            db.commit()
                            if cursor.rowcount > 0:
                                response = f"[Server] ID {target_id} delete complete\n"
                            else:
                                response = f"[Server] ID {target_id} is not found\n"
                        except ValueError:
                            response = "[Server] ID must be a number.\n"
                    else:
                        response = "[Server] Invalid format. Use: del id <number>\n"
                    conn.sendall(response.encode("utf-8"))
                else:
                    cursor.execute(
                        "INSERT INTO commands (command) VALUES (%s)", (input_str,)
                    )
                    db.commit()
                    response = f"[Server] Command saved successfully: {input_str}\n"
                    conn.sendall(response.encode("utf-8"))

    except Exception as e:
        print(f"[Server] Error with {addr} : {e}")

    finally:
        conn.close()  # 클라이언트 소켓 연결 끊기
        cursor.close()  # 커서 종료
        db.close()  ## db 종료
        print(f"Server close for {addr}")


# main server 실행, 서버 소켓 open, 클라이언트 연결 대기
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 소켓 객체 생성
    # socket.AF_INET: 주소종류 지정(IP) / socket.SOCK_STREAM: 통신종류 지정(UDP, TCP)
    # SOCK_STREAM은 TCP를 사용하겠다는 의미.
    # SOCK_DGRAM은 UDP를 사용하겠다는 의미.

    server_socket.bind((HOST, PORT))  # 소켓에 주소 할당
    server_socket.listen()
    # 클라이언트 대기, socket.listen() 함수를 사용하여 클라이언트의 연결 요청을 기다리는 상태로 설정

    print(f"[Server] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        # socket.accept() 함수를 사용하여 연결을 수락하고 클라이언트와 통신할 수 있는 새로운 소켓을 생성
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        # handle_client 함수를 thread로 실행. 클라이언트가 연결될 때마다 새 thread에서 호출
        # daemon=True : 서버 종료시 thread 종료
        thread.start()
        print(f"[Server] Active clients: {threading.active_count() - 1}")
        # 현재 활성화된 thread 수 확인


# 다른 모듈에서 이 파일을 import하여도 서버가 실행되지 않도록 하기 위한 파이썬 관례. start_server() 함수가 호출되고 서버가 열리고 handle_client()는 클라이언트가 들어올때마다 실행
if __name__ == "__main__":
    start_server()

#         [Client 1]         [Client 2]         [Client 3]
#              ↓                 ↓                 ↓
#      ┌─────────────────────────────────────────────┐
#      │              start_server()                 │
#      ├─────────────────────────────────────────────┤
#      │ listen()                                    │
#      │ accept() ──> threading.Thread(handle_client)│
#      └─────────────────────────────────────────────┘
#                    ↓              ↓              ↓
#            handle_client()  handle_client()  handle_client()
