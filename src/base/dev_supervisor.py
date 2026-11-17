#!/usr/bin/env python3
"""Unified supervisor for local development services of AI-Model platform.

Manages the lifecycle of:
  - PostgreSQL (port 5433, unix socket in base/.run)
  - Django REST backend (port 8000)
  - FastAPI inference engine (port 8001)
  - PostGraphile GraphQL server (port 5000)
  - Vite React frontend (port 5173)

Features:
  - Port conflict resolution (kills orphan processes holding dev ports)
  - Socket preservation (does not delete active postgres sockets)
  - Automatic restart on unexpected process termination (max 5 retries)
  - Health monitoring with live status in base/.run/status.json
  - Graceful shutdown signal handling (SIGINT, SIGTERM, SIGHUP)
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SRC_ROOT = BASE_DIR.parent
ROOT_DIR = SRC_ROOT.parent

RUN_DIR = BASE_DIR / ".run"
LOG_DIR = BASE_DIR / ".logs"
PGDATA_DIR = BASE_DIR / ".pgdata"
BACKEND_DIR = SRC_ROOT / "backend"
FRONTEND_DIR = SRC_ROOT / "frontend"
POSTGRAPHQL_DIR = BASE_DIR / "postgraphql"

# Binary discovery
PG_BIN_DIR = next(
    (p for p in [Path("/usr/lib/postgresql/18/bin"), Path("/usr/lib/postgresql/16/bin"), Path("/usr/bin")] if (p / "postgres").exists()),
    Path("/usr/bin"),
)

PYTHON_BIN = next(
    (p for p in [
        Path(os.environ.get("HOME", "/home/v1")) / ".cache/pypoetry/virtualenvs" / "ai-model-De_w0nez-py3.14/bin/python",
        *sorted(Path(os.environ.get("HOME", "/home/v1")).glob(".cache/pypoetry/virtualenvs/ai-model-*/bin/python"), reverse=True),
        Path(sys.executable),
    ] if p.exists()),
    Path(sys.executable),
)

NODE_BIN = Path(os.environ.get("NODE_BIN") or shutil.which("node") or "/home/v1/.nvm/versions/node/v24.21.0/bin/node")
NPM_BIN = Path(os.environ.get("NPM_BIN") or shutil.which("npm") or "/home/v1/.nvm/versions/node/v24.21.0/bin/npm")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "ai_model")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ai_model")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ai_model_dev_pass")

DJANGO_HOST = os.getenv("DJANGO_HOST", "127.0.0.1")
DJANGO_PORT = int(os.getenv("DJANGO_PORT", "8000"))
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "127.0.0.1")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8001"))
POSTGRAPHILE_HOST = os.getenv("POSTGRAPHILE_HOST", "127.0.0.1")
POSTGRAPHILE_PORT = int(os.getenv("POSTGRAPHILE_PORT", "5000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))

processes: dict[str, subprocess.Popen] = {}
log_files: dict[str, object] = {}
crash_counts: dict[str, int] = {}
is_shutting_down = False


def log(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] [supervisor] {msg}", flush=True)


def free_port(port: int) -> None:
    """Kill any lingering process holding the given TCP port."""
    try:
        subprocess.run(["fuser", "-k", "-9", f"{port}/tcp"], capture_output=True)
    except Exception:
        pass


def cleanup_stale_files() -> None:
    """Clean stale PID and socket files safely without breaking running services."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Free dev server HTTP ports
    for port in [DJANGO_PORT, FASTAPI_PORT, POSTGRAPHILE_PORT, FRONTEND_PORT]:
        free_port(port)

    # Only purge PostgreSQL lock files if PostgreSQL is NOT accepting connections
    if not is_postgres_ready():
        for f in ["postmaster.pid"]:
            p = PGDATA_DIR / f
            if p.exists():
                p.unlink(missing_ok=True)
        for p in RUN_DIR.glob(".s.PGSQL.*"):
            p.unlink(missing_ok=True)

    for p in RUN_DIR.glob("*.pid"):
        if p.stem != "postgres" or not is_postgres_ready():
            p.unlink(missing_ok=True)


def write_pid(name: str, pid: int) -> None:
    (RUN_DIR / f"{name}.pid").write_text(f"{pid}\n", encoding="utf-8")


def check_url(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SupervisorHealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        return e.code in (200, 301, 302, 401, 403, 404, 405)
    except Exception:
        return False


def is_postgres_ready() -> bool:
    isready_bin = PG_BIN_DIR / "pg_isready"
    if not isready_bin.exists():
        return False
    # Check socket first
    res = subprocess.run([str(isready_bin), "-h", str(RUN_DIR), "-p", str(POSTGRES_PORT)],
                         capture_output=True, text=True)
    if res.returncode == 0:
        return True
    # Check host/port
    res2 = subprocess.run([str(isready_bin), "-h", POSTGRES_HOST, "-p", str(POSTGRES_PORT)],
                          capture_output=True, text=True)
    return res2.returncode == 0


def ensure_postgres_db() -> bool:
    psql_bin = PG_BIN_DIR / "psql"
    createdb_bin = PG_BIN_DIR / "createdb"
    env = os.environ.copy()
    env["PGPASSWORD"] = POSTGRES_PASSWORD

    for host_arg in [str(RUN_DIR), POSTGRES_HOST]:
        check_cmd = [
            str(psql_bin), "-h", host_arg, "-p", str(POSTGRES_PORT),
            "-U", POSTGRES_USER, "-d", "postgres", "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{POSTGRES_DB}'"
        ]
        res = subprocess.run(check_cmd, env=env, capture_output=True, text=True)
        if "1" in res.stdout:
            return True
        create_cmd = [
            str(createdb_bin), "-h", host_arg, "-p", str(POSTGRES_PORT),
            "-U", POSTGRES_USER, POSTGRES_DB
        ]
        subprocess.run(create_cmd, env=env, capture_output=True, text=True)
        res2 = subprocess.run(check_cmd, env=env, capture_output=True, text=True)
        if "1" in res2.stdout:
            return True
    return False


def update_status_file(statuses: dict[str, dict[str, object]]) -> None:
    status_path = RUN_DIR / "status.json"
    temp_path = RUN_DIR / "status.json.tmp"
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "supervisor_pid": os.getpid(),
        "services": statuses,
    }
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(status_path)


def start_service(name: str, cmd: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> subprocess.Popen:
    log_path = LOG_DIR / f"{name}.log"
    log_file = open(log_path, "a", encoding="utf-8")
    log_files[name] = log_file

    env = os.environ.copy()
    node_dir = str(NODE_BIN.parent)
    py_dir = str(PYTHON_BIN.parent)
    env["PATH"] = f"{node_dir}:{py_dir}:{env.get('PATH', '')}"
    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    processes[name] = proc
    write_pid(name, proc.pid)
    log(f"Spawned {name} (PID {proc.pid}) -> logging to {log_path.name}")
    return proc


# Service specifications for starting and restarting
SERVICE_CONFIGS: dict[str, dict[str, object]] = {
    "django": {
        "cmd": [str(PYTHON_BIN), "manage.py", "runserver", f"{DJANGO_HOST}:{DJANGO_PORT}", "--noreload"],
        "cwd": BACKEND_DIR,
        "env": {"PYTHONPATH": f"{BACKEND_DIR}:{SRC_ROOT}"},
        "port": DJANGO_PORT,
    },
    "fastapi": {
        "cmd": [str(PYTHON_BIN), "-m", "uvicorn", "api.main:app", "--host", FASTAPI_HOST, "--port", str(FASTAPI_PORT), "--log-level", "info"],
        "cwd": SRC_ROOT,
        "env": {"PYTHONPATH": str(SRC_ROOT)},
        "port": FASTAPI_PORT,
    },
    "postgraphql": {
        "cmd": [str(NODE_BIN), str(POSTGRAPHQL_DIR / "server.cjs")],
        "cwd": POSTGRAPHQL_DIR,
        "env": {},
        "port": POSTGRAPHILE_PORT,
    },
    "frontend": {
        "cmd": [str(NPM_BIN), "run", "dev", "--", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        "cwd": FRONTEND_DIR,
        "env": {},
        "port": FRONTEND_PORT,
    },
}


def restart_service(name: str) -> None:
    """Safely restart a service after cleaning its port."""
    if name not in SERVICE_CONFIGS:
        return
    cfg = SERVICE_CONFIGS[name]
    port = int(cfg["port"])
    free_port(port)
    time.sleep(0.4)
    start_service(name, cfg["cmd"], Path(cfg["cwd"]), dict(cfg.get("env", {})))


def shutdown(signum=None, frame=None) -> None:
    global is_shutting_down
    if is_shutting_down:
        return
    is_shutting_down = True
    log(f"Received shutdown signal ({signum}). Gracefully stopping all services...")

    order = ["frontend", "postgraphql", "fastapi", "django", "postgres"]
    for name in order:
        proc = processes.get(name)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass

    for name in order:
        proc = processes.get(name)
        if proc and proc.poll() is None:
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass

    for f in log_files.values():
        try:
            f.close()
        except Exception:
            pass

    cleanup_stale_files()
    log("All platform services stopped cleanly.")
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGHUP, shutdown)

    write_pid("supervisor", os.getpid())

    log("=" * 60)
    log("AI-Model Local Platform Supervisor Initializing")
    log(f"Python: {PYTHON_BIN}")
    log(f"PostgreSQL binary: {PG_BIN_DIR / 'postgres'}")
    log("=" * 60)

    cleanup_stale_files()

    # 1. Start PostgreSQL
    log("1/5 Starting local PostgreSQL cluster...")
    if not is_postgres_ready():
        pg_cmd = [
            str(PG_BIN_DIR / "postgres"),
            "-D", str(PGDATA_DIR),
            "-k", str(RUN_DIR),
            "-h", POSTGRES_HOST,
            "-p", str(POSTGRES_PORT),
        ]
        start_service("postgres", pg_cmd, BASE_DIR)
    else:
        log("PostgreSQL is already running and accepting connections.")

    # Wait for PostgreSQL
    pg_ready = False
    for i in range(30):
        if is_postgres_ready():
            pg_ready = True
            log(f"PostgreSQL is accepting connections on {POSTGRES_HOST}:{POSTGRES_PORT}")
            break
        time.sleep(0.4)

    if not pg_ready:
        log("ERROR: PostgreSQL failed to become ready within 12 seconds.")
        shutdown(signal.SIGTERM)

    ensure_postgres_db()

    # Run Django migrations and seeding
    log("Applying Django migrations & seeding database...")
    env_django = {"PYTHONPATH": f"{BACKEND_DIR}:{SRC_ROOT}"}
    subprocess.run(
        [str(PYTHON_BIN), "manage.py", "migrate", "--noinput"],
        cwd=str(BACKEND_DIR),
        env={**os.environ, **env_django},
        capture_output=True,
    )
    subprocess.run(
        [str(PYTHON_BIN), "manage.py", "seed_ai_platform"],
        cwd=str(BACKEND_DIR),
        env={**os.environ, **env_django},
        capture_output=True,
    )

    # 2. Start Django
    log("2/5 Starting Django REST Backend on port 8000...")
    free_port(DJANGO_PORT)
    start_service("django", SERVICE_CONFIGS["django"]["cmd"], SERVICE_CONFIGS["django"]["cwd"], SERVICE_CONFIGS["django"]["env"])

    # 3. Start FastAPI Inference Engine
    log("3/5 Starting FastAPI Inference Engine on port 8001...")
    free_port(FASTAPI_PORT)
    start_service("fastapi", SERVICE_CONFIGS["fastapi"]["cmd"], SERVICE_CONFIGS["fastapi"]["cwd"], SERVICE_CONFIGS["fastapi"]["env"])

    # 4. Start PostGraphile GraphQL Server
    log("4/5 Starting PostGraphile GraphQL Server on port 5000...")
    free_port(POSTGRAPHILE_PORT)
    start_service("postgraphql", SERVICE_CONFIGS["postgraphql"]["cmd"], SERVICE_CONFIGS["postgraphql"]["cwd"], SERVICE_CONFIGS["postgraphql"]["env"])

    # 5. Start Vite React Frontend
    log("5/5 Starting Vite React Frontend on port 5173...")
    free_port(FRONTEND_PORT)
    start_service("frontend", SERVICE_CONFIGS["frontend"]["cmd"], SERVICE_CONFIGS["frontend"]["cwd"], SERVICE_CONFIGS["frontend"]["env"])

    # Allow services 2.5s to warm up
    log("Warming up services...")
    time.sleep(2.5)

    health_urls = {
        "django": f"http://{DJANGO_HOST}:{DJANGO_PORT}/api/",
        "fastapi": f"http://{FASTAPI_HOST}:{FASTAPI_PORT}/api/v1/health",
        "postgraphql": f"http://{POSTGRAPHILE_HOST}:{POSTGRAPHILE_PORT}/health",
        "frontend": f"http://127.0.0.1:{FRONTEND_PORT}",
    }

    log("=" * 60)
    log("INITIAL HEALTH STATUS:")
    log(f"  postgres     : {'HEALTHY' if is_postgres_ready() else 'DEGRADED'} ({POSTGRES_HOST}:{POSTGRES_PORT})")
    for name, url in health_urls.items():
        ok = check_url(url)
        log(f"  {name:<13}: {'HEALTHY' if ok else 'STARTING'} ({url})")
    log("=" * 60)

    # Monitoring and auto-recovery loop
    check_interval = 5.0
    while not is_shutting_down:
        current_status: dict[str, dict[str, object]] = {}

        # Postgres check & auto-recovery
        pg_proc = processes.get("postgres")
        pg_conn = is_postgres_ready()
        pg_pid = pg_proc.pid if pg_proc else None
        if not pg_pid and (PGDATA_DIR / "postmaster.pid").exists():
            try:
                pg_pid = int((PGDATA_DIR / "postmaster.pid").read_text().split()[0])
            except Exception:
                pg_pid = None

        if pg_conn:
            crash_counts["postgres"] = 0
        elif not is_shutting_down:
            crash_counts["postgres"] = crash_counts.get("postgres", 0) + 1
            if crash_counts["postgres"] <= 5:
                log(f"PostgreSQL stopped or unreachable. Auto-recovering (attempt {crash_counts['postgres']}/5)...")
                (PGDATA_DIR / "postmaster.pid").unlink(missing_ok=True)
                pg_cmd = [
                    str(PG_BIN_DIR / "postgres"),
                    "-D", str(PGDATA_DIR),
                    "-k", str(RUN_DIR),
                    "-h", POSTGRES_HOST,
                    "-p", str(POSTGRES_PORT),
                ]
                start_service("postgres", pg_cmd, BASE_DIR)
                time.sleep(1.0)
                pg_proc = processes.get("postgres")
                pg_pid = pg_proc.pid if pg_proc else None
                pg_conn = is_postgres_ready()

        current_status["postgres"] = {
            "status": "RUNNING" if pg_conn else "CRASHED",
            "pid": pg_pid,
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "healthy": pg_conn,
        }

        # HTTP services check & auto-restart
        for name, url in health_urls.items():
            proc = processes.get(name)
            alive = proc is not None and proc.poll() is None

            if not alive and not is_shutting_down:
                exit_code = proc.poll() if proc else "unknown"
                crash_counts[name] = crash_counts.get(name, 0) + 1
                if crash_counts[name] <= 5:
                    log(f"Service '{name}' exited with code {exit_code}. Auto-recovering (attempt {crash_counts[name]}/5)...")
                    restart_service(name)
                    proc = processes.get(name)
                    alive = proc is not None and proc.poll() is None
                elif crash_counts[name] == 6:
                    log(f"Service '{name}' exceeded max restart attempts (5). Pausing auto-restart.")

            ok = check_url(url) if alive else False
            if alive and ok:
                crash_counts[name] = 0

            current_status[name] = {
                "status": "RUNNING" if alive else "CRASHED",
                "pid": proc.pid if proc else None,
                "url": url,
                "healthy": ok,
            }

        update_status_file(current_status)
        time.sleep(check_interval)


if __name__ == "__main__":
    main()
