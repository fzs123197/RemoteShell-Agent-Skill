import socket
import json


class RemoteShellAgentClient:
    def __init__(self, host: str, port: int, auth_token: str):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.sock: socket.socket | None = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.sendall((self.auth_token + "\n").encode("utf-8"))

    def run_cmd(self, cmd: str) -> dict:
        if self.sock is None:
            raise ConnectionError("not connected")
        payload = json.dumps({"cmd": cmd}, ensure_ascii=False).encode("utf-8")
        payload += b"\n###END###\n"
        self.sock.sendall(payload)

        buf = b""
        while True:
            chunk = self.sock.recv(16384)
            if not chunk:
                raise IOError("connection closed")
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                continue

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None


if __name__ == "__main__":
    client = RemoteShellAgentClient(
        host="127.0.0.1",
        port=9999,
        auth_token="MY_AGENT_SECRET_123456"
    )
    client.connect()

    ret = client.run_cmd("ipconfig")
    print("===stdout===")
    print(ret["stdout"])
    print("===stderr===")
    print(ret["stderr"])
    print(f"cwd={ret['cwd']}, ok={ret['success']}")

    ret2 = client.run_cmd("cd ..")
    print(ret2)

    client.close()
