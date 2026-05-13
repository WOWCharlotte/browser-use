#!/usr/bin/env python3
"""一键启动前后端服务"""
import subprocess
import sys
import os
import time
import signal

def run_command(cmd, cwd, name):
    """启动子进程"""
    print(f"[{name}] 启动中...")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return proc

def main():
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(script_dir, "backend")
    frontend_dir = os.path.join(script_dir, "frontend")

    processes = []

    try:
        # 启动后端
        backend_proc = run_command(
            "uv run python -m app.main",
            backend_dir,
            "Backend (FastAPI :8888)"
        )
        processes.append(backend_proc)

        # 等待后端启动
        time.sleep(2)

        # 启动前端
        frontend_proc = run_command(
            "npm run dev",
            frontend_dir,
            "Frontend (Next.js :3000)"
        )
        processes.append(frontend_proc)

        print("\n========================================")
        print("  服务已启动:")
        print("  - 后端: http://localhost:8888")
        print("  - 前端: http://localhost:3000")
        print("  按 Ctrl+C 停止所有服务")
        print("========================================\n")

        # 等待所有进程
        for proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\n\n正在停止所有服务...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("所有服务已停止")

if __name__ == "__main__":
    main()