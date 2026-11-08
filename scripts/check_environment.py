#!/usr/bin/env python3
"""
Módulo de Verificação de Pré-requisitos do Ambiente (Módulo A - Passo 1).
Verifica a presença e sanidade do Python 3, Docker CLI, Daemon, Permissões,
Git, GNU timeout, espaço em disco e suporte obrigatório a Cgroups v2.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Tuple


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Executa comando de forma síncrona retornando código de saída, stdout e stderr."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Comando '{cmd[0]}' não encontrado no PATH."
    except Exception as e:
        return 1, "", str(e)


def check_environment() -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    passed_all = True

    # 1. Python 3
    py_version = platform.python_version()
    py_ok = sys.version_info >= (3, 10)
    checks["python3"] = {
        "status": "PASS" if py_ok else "FAIL",
        "version": py_version,
        "executable": sys.executable,
        "detail": "Python 3.10+ requerido."
    }
    if not py_ok:
        passed_all = False

    # 2. Git
    code, out, _ = run_cmd(["git", "--version"])
    git_ok = code == 0
    checks["git"] = {
        "status": "PASS" if git_ok else "FAIL",
        "output": out if git_ok else "Git não encontrado.",
    }
    if not git_ok:
        passed_all = False

    # 3. GNU timeout
    code, out, _ = run_cmd(["timeout", "--version"])
    timeout_ok = code == 0
    checks["timeout"] = {
        "status": "PASS" if timeout_ok else "WARN",
        "output": out.splitlines()[0] if timeout_ok and out else "GNU timeout não encontrado (subprocess nativo será utilizado).",
    }

    # 4. Docker CLI
    code, out, _ = run_cmd(["docker", "--version"])
    docker_cli_ok = code == 0
    checks["docker_cli"] = {
        "status": "PASS" if docker_cli_ok else "FAIL",
        "output": out if docker_cli_ok else "Docker CLI não encontrado.",
    }
    if not docker_cli_ok:
        passed_all = False

    # 5. Docker Daemon & Permissões
    code, out, err = run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"])
    daemon_ok = code == 0
    checks["docker_daemon"] = {
        "status": "PASS" if daemon_ok else "FAIL",
        "server_version": out if daemon_ok else "",
        "detail": f"Docker Engine Server {out} operacional." if daemon_ok else "Daemon inacessível.",
        "error": err if not daemon_ok else None
    }
    if not daemon_ok:
        passed_all = False

    # 6. Permissão de execução de contêineres
    if daemon_ok:
        code, out, err = run_cmd(["docker", "run", "--rm", "hello-world"])
        if code != 0:
            # Tenta com alpine ou python caso hello-world não esteja em cache local
            code, out, err = run_cmd(["docker", "run", "--rm", "python:3.12-slim", "true"])
        can_run = code == 0
        checks["docker_run_permission"] = {
            "status": "PASS" if can_run else "FAIL",
            "detail": "Capacidade de criar e executar contêineres confirmada." if can_run else f"Falha ao executar contêiner: {err}"
        }
        if not can_run:
            passed_all = False
    else:
        checks["docker_run_permission"] = {"status": "FAIL", "detail": "Daemon inacessível."}
        passed_all = False

    # 7. Cgroup v2 e Cgroup Driver
    code, cgroup_ver, _ = run_cmd(["docker", "info", "--format", "{{.CgroupVersion}}"])
    code_d, cgroup_driver, _ = run_cmd(["docker", "info", "--format", "{{.CgroupDriver}}"])
    is_cgroup_v2 = (cgroup_ver == "2")
    checks["cgroup_v2"] = {
        "status": "PASS" if is_cgroup_v2 else "FAIL",
        "cgroup_version": cgroup_ver,
        "cgroup_driver": cgroup_driver,
        "detail": "Cgroups v2 ativo." if is_cgroup_v2 else f"Ambiente utiliza Cgroup v{cgroup_ver}. Cgroup v2 é estritamente obrigatório."
    }
    if not is_cgroup_v2:
        passed_all = False

    # 8. Verificação dos arquivos de controle do Cgroup v2 dentro de contêiner
    cgroup_files = [
        "/sys/fs/cgroup/cpu.max",
        "/sys/fs/cgroup/cpu.stat",
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory.current",
        "/sys/fs/cgroup/pids.max"
    ]
    test_sh = " && ".join([f"[ -f {f} ]" for f in cgroup_files])
    code, _, _ = run_cmd(["docker", "run", "--rm", "python:3.12-slim", "sh", "-c", test_sh])
    files_ok = code == 0
    checks["cgroup_controllers"] = {
        "status": "PASS" if files_ok else "FAIL",
        "verified_files": cgroup_files,
        "detail": "Todos os controladores de CPU, memória e PIDs disponíveis." if files_ok else "Um ou mais arquivos de cgroup v2 não foram encontrados no contêiner."
    }
    if not files_ok:
        passed_all = False

    # 9. Espaço em disco disponível
    usage = shutil.disk_usage(".")
    free_gb = usage.free / (1024 ** 3)
    space_ok = free_gb >= 1.0
    checks["disk_space"] = {
        "status": "PASS" if space_ok else "WARN",
        "free_gb": round(free_gb, 2),
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "detail": f"{free_gb:.2f} GB livres para gravação de resultados."
    }

    # 10. Metadados do Sistema Operacional Local
    checks["host_system"] = {
        "status": "PASS",
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "node": platform.node(),
        "detail": f"{platform.system()} {platform.release()} ({platform.machine()})"
    }

    return {
        "success": passed_all,
        "checks": checks
    }


def main() -> int:
    print("=" * 60)
    print("      VERIFICAÇÃO DE PRÉ-REQUISITOS DO AMBIENTE")
    print("=" * 60)
    results = check_environment()

    for key, val in results["checks"].items():
        status = val.get("status", "INFO")
        detail = val.get("detail") or val.get("output") or val.get("version") or ""
        tag = f"[{status}]"
        print(f"{tag:<8} {key:<24}: {detail}")

    print("=" * 60)
    if results["success"]:
        print("[SUCESSO] Todos os pré-requisitos mandatórios foram atendidos!")
        print("Ambiente pronto para execução dos módulos da Atividade 3.")
        return 0
    else:
        print("[FALHA] Um ou mais requisitos mandatórios não foram atendidos.", file=sys.stderr)
        print("Consulte os detalhes acima antes de prosseguir.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
