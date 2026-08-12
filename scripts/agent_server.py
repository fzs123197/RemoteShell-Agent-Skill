import socket
import subprocess
import os
import json

AUTH_TOKEN = "MY_AGENT_SECRET_123456"  # 修改为你的密钥
BUF_SIZE = 8192


def exec_command(cmd: str, cwd: str):
    """执行命令，返回输出，维持工作目录"""
    if cmd.strip().startswith("cd "):
        target = cmd[3:].strip()
        try:
            os.chdir(target)
            return {
                "success": True,
                "stdout": "",
                "stderr": "",
                "cwd": os.getcwd()
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "cwd": cwd
            }

    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace"
    )
    stdout, stderr = proc.communicate(timeout=120)
    return {
        "success": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "cwd": os.getcwd()
    }


def run_agent_server(host="0.0.0.0", port=9999):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        current_cwd = os.getcwd()
        try:
            # 第一步鉴权
            raw_token = conn.recv(1024).decode("utf-8").strip()
            if raw_token != AUTH_TOKEN:
                conn.send(json.dumps({"error": "auth failed"}).encode())
                conn.close()
                continue

            while True:
                data_buf = b""
                while True:
                    chunk = conn.recv(BUF_SIZE)
                    if not chunk:
                        return
                    data_buf += chunk
                    # 简单协议：以 \n###END###\n 作为消息结束标记
                    if b"\n###END###\n" in data_buf:
                        data_buf, _ = data_buf.split(b"\n###END###\n", 1)
                        break
                if not data_buf:
                    break
                payload = json.loads(data_buf.decode("utf-8"))
                command = payload.get("cmd", "")
                res = exec_command(command, current_cwd)
                current_cwd = res["cwd"]
                resp_bytes = json.dumps(res, ensure_ascii=False).encode("utf-8")
                conn.sendall(resp_bytes)
        except Exception:
            pass
        finally:
            conn.close()


if __name__ == "__main__":
    run_agent_server(port=9999)
