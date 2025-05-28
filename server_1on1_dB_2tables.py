import socket  # tcp/ip socket module load
import pymysql  # mysql module load
import pymysql.cursors

# MySQL 연결
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
except pymysql.MySQLError as e:
    print(f"DB connection failed : {e}")
    exit(0)

HOST = "0.0.0.0"  # 모든 IP로부터 접속 허용
PORT = 65535  # 사용할 포트

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 소켓 객체 생성
# socket.AF_INET: 주소종류 지정(IP) / socket.SOCK_STREAM: 통신종류 지정(UDP, TCP)
# SOCK_STREAM은 TCP를 사용하겠다는 의미.
# SOCK_DGRAM은 UDP를 사용하겠다는 의미.

server_socket.bind((HOST, PORT))  # 소켓에 주소 할당
server_socket.listen(1)
# 클라이언트 최대 1명 대기, socket.listen() 함수를 사용하여 클라이언트의 연결 요청을 기다리는 상태로 설정

print("Waiting for connection on client")

conn, addr = server_socket.accept()
# socket.accept() 함수를 사용하여 연결을 수락하고 클라이언트와 통신할 수 있는 새로운 소켓을 생성
print(f"Connected: {addr}")
# 문자열 앞에 f를 붙이면, 중괄호와 변수 이름만으로 문자열에 원하는 변수를 삽입할 수 있음.

current_mode = "employee"  # 기본 모드 설정

while True:
    data = conn.recv(1024)  # 클라이언트로부터 데이터를 1024바이트까지 받음
    if not data:
        print("Disconnected to client. Bye Bye!!")
        break

    input_str = (
        data.decode().strip()
    )  # 문자열 decode, .strip()을 사용하여 공백 입력 제거
    print(f"[Server] Received: {input_str}")

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
        if input_str.lower() == "show all":
            # 저장되어 있는 목록 조회
            cursor.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()  # 레코드를 배열 형식으로 저장된 항목을 모두 가져옴
            if not rows:
                response = "No saved list.\n"
            else:
                response = "[Recent 10 list]\n"  # response 변수 초기화
                for row in rows:
                    response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} | timestamp: {row[5]} \n"
            conn.sendall(response.encode("utf-8"))
            print("[Server] Sent employee query result.")

        elif input_str.lower().startswith("show id "):
            # id로 조회
            target_id = int(input_str.split()[2])
            # 입력된 문자열에서 두번째 단어를 가지고오는 구문
            cursor.execute(
                "SELECT id, name, phone, email, department FROM employees WHERE id = %s",
                (target_id,),
            )
            row = cursor.fetchone()
            # 레코드를 배열 형식으로 저장된 항목을 특정하나만 가져옴
            if not row:
                response = f"[Server] No record found with ID {target_id}\n"
            else:
                response = "[Search result]\n"
                response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} \n"
            conn.sendall(response.encode("utf-8"))

        elif input_str.lower().startswith("show name "):
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
                response = f"[Server] No record found with name {target_name}\n"
            else:
                response = "[Search result]\n"
                for row in rows:
                    response += f"ID: {row[0]} | Name: {row[1]} | Phone: {row[2]} | Email: {row[3]} | Dept: {row[4]} \n"
            conn.sendall(response.encode("utf-8"))

        elif input_str.lower().startswith("del id "):
            # 저장되어 있는 목록 삭제
            target_id = int(input_str.split()[2])
            cursor.execute("DELETE FROM employees WHERE id = %s", (target_id,))
            db.commit()

            if cursor.rowcount > 0:
                conn.sendall(f"[Server] ID {target_id} delete complete\n".encode())
            else:
                conn.sendall(f"[Server] ID {target_id} is not found\n".encode())

        else:
            try:
                name, phone, email, dept = [x.strip() for x in input_str.split(",")]
                cursor.execute(
                    "INSERT INTO employees (name, phone, email, department) VALUES (%s, %s, %s, %s)",
                    (name, phone, email, dept),
                )
                db.commit()
                response = f"[Server] Information saved successfully: {name}\n"
                print(f"[Server] Save complete: {name}, {phone}, {email}, {dept}")
                conn.sendall(response.encode("utf-8"))

            except ValueError:
                conn.sendall(
                    "[Server] Input format error: Please enter name, phone number, email, department format.\n".encode()
                )

    elif current_mode == "cli":
        if input_str.lower() == "show all":
            # 저장되어 있는 목록 조회
            cursor.execute("SELECT * FROM commands ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()  # 레코드를 배열 형식으로 저장된 항목을 모두 가져옴
            if not rows:
                response = "No saved list.\n"
            else:
                response = "[Recent 10 list]\n"  # response 변수 초기화
                for row in rows:
                    response += f"{row[0]} | {row[1]} | {row[2]} \n"
            conn.sendall(response.encode("utf-8"))
            print("[Server] Sent CLI query result.")
        elif input_str.lower().startswith("show id "):
            # Cli id로 조회
            target_id = int(input_str.split()[2])
            cursor.execute(
                "SELECT id, command FROM commands WHERE id = %s",
                (target_id,),
            )
            row = cursor.fetchone()
            if not row:
                response = f"[Server] No record found with ID {target_id}\n"
            else:
                response = "[Search result]\n"
                response += f"ID: {row[0]} | Command: {row[1]}\n"
            conn.sendall(response.encode("utf-8"))
        elif input_str.lower().startswith("del id "):
            # 저장 목록 삭제
            target_id = int(input_str.split()[2])
            cursor.execute("DELETE FROM commands WHERE id = %s", (target_id,))
            db.commit()
            if cursor.rowcount > 0:
                conn.sendall(f"[Server] ID {target_id} delete complete\n".encode())
            else:
                conn.sendall(f"[Server] ID {target_id} is not found\n".encode())
        else:
            cursor.execute("INSERT INTO commands (command) VALUES (%s)", (input_str,))
            db.commit()
            response = f"[Server] Command saved successfully: {input_str}\n"
            conn.sendall(response.encode("utf-8"))
conn.close()  # 클라이언트 소켓 연결 끊기
server_socket.close()  # 모든 소켓 종료
cursor.close()  # 커서 종료
db.close()  ## db 종료
print("Server close")
