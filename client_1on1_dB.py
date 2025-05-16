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
    print("Connect server.")
    print(
        "Input information(name, phone, email, department). If you want to quit, input 'exit'"
    )

except ConnectionRefusedError:
    print("Connection fail")
    exit(0)

while True:
    msg = input("[Client] knshell : ").strip()
    # .strip()을 사용하여 공백 입력 제거
    if not msg:
        print("[Warning] Nothing was entered. Please enter a command.")
        continue

    if msg.lower() == "exit":
        # .lower(): 입력된 문자를 소문자로 변경.
        print("Disconnected to server. Bye Bye!!")
        break

    msg = msg.encode("UTF-8")  # 문자열 encode
    client_socket.sendall(msg)
    # sendall(): 데이터를 모두 전송할 때까지 반복적으로 send()를 호출

    data = client_socket.recv(4096)
    if data:
        print(data.decode())

client_socket.close()  # 소켓 종료
