import socket  # socket module load

server_ip = input("Input server ip (Default ip : 127.0.0.1): ")
server_port = input("Input server port (Default port : 65535): ")

if not server_ip:
    server_ip = "127.0.0.1"
else:
    server_ip

if not server_port:
    server_port = 65535
else:
    server_port = int(server_port)

try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 소켓 객체 생성
    # socket.AF_INET: 주소종류 지정(IP) / socket.SOCK_STREAM: 통신종류 지정(UDP, TCP)
    # SOCK_STREAM은 TCP를 사용하겠다는 의미.
    # SOCK_DGRAM은 UDP를 사용하겠다는 의미.
    client_socket.settimeout(60)  # 입력이 60초 이상 없을 시 타임아웃
    client_socket.connect((server_ip, server_port))  # 소켓에 주소 할당
    print(f"Connected to {server_ip}:{server_port}")
    print("Input mode cli or mode employee. If you want to quit, input 'exit'")

except ConnectionRefusedError:
    print("Connection fail")
    exit(0)

current_mode = "employee"


def get_prompt():
    return f"[{current_mode}] shell: "


while True:
    msg = input(get_prompt()).strip()
    # .strip()을 사용하여 공백 입력 제거
    if not msg:
        print("[Warning] Nothing was entered. Please enter a command.")
        continue

    if msg.lower() == "exit":
        # .lower(): 입력된 문자를 소문자로 변경.
        print("Disconnected to server. Bye Bye!!")
        client_socket.close()  # 소켓 종료
        break

    msg = msg.encode("utf-8")  # 문자열 encode

    try:
        client_socket.sendall(msg)
        # sendall(): 데이터를 모두 전송할 때까지 반복적으로 send()를 호출
    except (OSError, BrokenPipeError, ConnectionResetError) as e:
        print(f"[Client]Server connection lost during send: {e}")
        client_socket.close()
        break

    try:
        data = client_socket.recv(4096)
        # 서버 응답 수신
        if not data:
            print("[Client] Sever Disconnected")
            break

        response = data.decode().strip()
        print(response)

        if "Mode changed to CLI" in response:
            current_mode = "cli"
        elif "Mode changed to EMPLOYEE" in response:
            current_mode = "employee"

    except (ConnectionResetError, ConnectionRefusedError, OSError) as e:
        print(f"[Error] Server connection lost: {e}")
        break

try:
    client_socket.close()
except Exception as e:
    print(f"Error occured: {e}")
    pass
print("[Client] Socket closed.")
