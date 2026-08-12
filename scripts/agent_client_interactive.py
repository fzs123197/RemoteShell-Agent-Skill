import socket
import json
import argparse


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

    def interactive_shell(self):
        print(f"已连接 {self.host}:{self.port} | 输入 exit 退出交互")
        while True:
            try:
                cmd = input("remote> ").strip()
                if cmd.lower() == "exit":
                    break
                if not cmd:
                    continue
                res = self.run_cmd(cmd)
                if res["stdout"]:
                    print(res["stdout"], end="")
                if res["stderr"]:
                    print(res["stderr"], end="")
                print(f"[cwd:{res['cwd']}]")
            except KeyboardInterrupt:
                print("\n[!] Ctrl+C，退出交互")
                break
            except Exception as e:
                print(f"\n[通信异常] {e}")
                break


def main():
    parser = argparse.ArgumentParser(description="远程shell客户端，支持交互/API调用")
    parser.add_argument("--host", default="127.0.0.1", help="被控端IP")
    parser.add_argument("--port", type=int, default=9999, help="端口")
    parser.add_argument("--token", default="MY_AGENT_SECRET_123456", help="认证token")
    parser.add_argument("--cmd", help="直接执行一条命令（非交互，给脚本调用）")
    args = parser.parse_args()

    cli = RemoteShellAgentClient(args.host, args.port, args.token)
    try:
        cli.connect()
        if args.cmd:
            ret = cli.run_cmd(args.cmd)
            print(ret["stdout"], end="")
            print(ret["stderr"], end="")
        else:
            cli.interactive_shell()
    finally:
        cli.close()


if __name__ == "__main__":
    main()
