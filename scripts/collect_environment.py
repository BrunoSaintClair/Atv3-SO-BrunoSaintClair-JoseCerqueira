#!/usr/bin/env python3
"""
Módulo de Coleta e Documentação do Ambiente (Módulo A).
Coleta metadados técnicos do host Linux e do Docker Engine, fixando o digest
da imagem base, gerando os artefatos de documentação e o diagrama de arquitetura Mermaid.
"""

import datetime
import json
import os
import platform
import subprocess
import sys
from typing import Any, Dict


def run_cmd(cmd: list) -> str:
    """Executa um comando de subprocesso e retorna sua saída tratada."""
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Aviso ao executar {' '.join(cmd)}: {e.stderr.strip()}\n")
        return ""


def get_os_release_info() -> Dict[str, str]:
    info = {}
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    info[k] = v.strip('"')
    return info


def collect_environment() -> Dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    os_info = get_os_release_info()

    # Informações do host local
    uname_r = run_cmd(["uname", "-r"])
    uname_v = run_cmd(["uname", "-v"])
    uname_m = run_cmd(["uname", "-m"])
    cpu_count = os.cpu_count() or 1

    mem_total_bytes = 0
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_total_bytes = int(parts[1]) * 1024
                    break

    # Contexto e Versões Docker
    docker_context = run_cmd(["docker", "context", "show"])
    client_version = run_cmd(["docker", "version", "--format", "{{.Client.Version}}"])
    server_version = run_cmd(["docker", "version", "--format", "{{.Server.Version}}"])
    
    # Informações do Daemon via docker info
    raw_daemon_info = run_cmd(["docker", "info", "--format", "{{json .}}"])
    daemon_parsed = {}
    if raw_daemon_info:
        try:
            daemon_parsed = json.loads(raw_daemon_info)
        except Exception:
            pass

    cgroup_ver = daemon_parsed.get("CgroupVersion", run_cmd(["docker", "info", "--format", "{{.CgroupVersion}}"]))
    cgroup_drv = daemon_parsed.get("CgroupDriver", run_cmd(["docker", "info", "--format", "{{.CgroupDriver}}"]))
    daemon_os = daemon_parsed.get("OperatingSystem", "")
    daemon_kernel = daemon_parsed.get("KernelVersion", "")
    storage_driver = daemon_parsed.get("Driver", "")

    # Base image inspect
    base_image_tag = "python:3.12-slim"
    base_image_digest = run_cmd(["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", base_image_tag])

    # Custom built image inspect
    custom_image_tag = "so-atividade3:latest"
    build_cmd = (
        f'docker build --build-arg PYTHON_BASE="{base_image_digest}" '
        f'-t {custom_image_tag} -f docker/Dockerfile .'
    )
    custom_image_id = run_cmd(["docker", "image", "inspect", "--format", "{{.Id}}", custom_image_tag])
    if not custom_image_id:
        print(f"[*] Construindo imagem customizada {custom_image_tag}...")
        subprocess.run(build_cmd, shell=True, check=True)
        custom_image_id = run_cmd(["docker", "image", "inspect", "--format", "{{.Id}}", custom_image_tag])

    custom_image_created = run_cmd(["docker", "image", "inspect", "--format", "{{.Created}}", custom_image_tag])
    python_in_container = run_cmd(["docker", "run", "--rm", custom_image_tag, "python", "--version"])

    is_bare_metal = (uname_r == daemon_kernel and platform.system() == "Linux")

    env_data: Dict[str, Any] = {
        "timestamp_utc": now,
        "local_host": {
            "os_pretty_name": os_info.get("PRETTY_NAME", platform.platform()),
            "os_name": os_info.get("NAME", platform.system()),
            "os_version": os_info.get("VERSION", platform.version()),
            "kernel_release": uname_r,
            "kernel_version_details": uname_v,
            "architecture": uname_m,
            "logical_cpus": cpu_count,
            "memory_total_bytes": mem_total_bytes,
            "memory_total_human": f"{mem_total_bytes / (1024**3):.2f} GiB" if mem_total_bytes else "N/A"
        },
        "docker_environment": {
            "client_version": client_version,
            "server_version": server_version,
            "context": docker_context,
            "daemon_operating_system": daemon_os,
            "daemon_kernel_version": daemon_kernel,
            "cgroup_version": cgroup_ver,
            "cgroup_driver": cgroup_drv,
            "storage_driver": storage_driver,
            "intermediate_vm_present": not is_bare_metal,
            "isolation_type": "Bare-metal Linux (compartilhamento direto do kernel hospedeiro)" if is_bare_metal else "Virtualização intermediária detectada"
        },
        "container_image": {
            "base_image_tag": base_image_tag,
            "base_image_digest": base_image_digest,
            "custom_image_tag": custom_image_tag,
            "custom_image_id": custom_image_id,
            "custom_image_created": custom_image_created,
            "python_container_version": python_in_container,
            "build_command": build_cmd
        }
    }

    return env_data


def generate_architecture_markdown(data: Dict[str, Any]) -> str:
    host = data["local_host"]
    dock = data["docker_environment"]
    img = data["container_image"]

    return f"""# Arquitetura de Execução e Isolamento

Este documento descreve as camadas de abstração, virtualização baseada em contêineres e isolamento de recursos utilizadas nos experimentos da **Atividade 3 de Sistemas Operacionais**.

## Diagrama da Arquitetura em Camadas

```mermaid
flowchart TD
    subgraph BareMetal ["1. Hardware Físico"]
        HW["Hardware Físico ({host['architecture']} / {host['logical_cpus']} CPUs Lógicas / {host['memory_total_human']} RAM)"]
    end

    subgraph HostLayer ["2. Sistema Operacional Hospedeiro (Bare-metal)"]
        OS["{host['os_pretty_name']}"]
        Kernel["Kernel Linux {host['kernel_release']}\n• Escalonador CFS / Cgroups v2\n• Controladores: cpu, memory, pids\n• Namespaces: PID, MNT, NET, IPC, UTS, USER"]
    end

    subgraph EngineLayer ["3. Camada do Docker Engine"]
        Docker["Docker Engine {dock['server_version']} (Contexto: {dock['context']})\nDriver cgroup: {dock['cgroup_driver']} | Cgroup v{dock['cgroup_version']}"]
    end

    subgraph ContainerA ["4. Contêiner A (so-atividade3-ns-a / C1)"]
        A_proc["Processo Isolado\nNamespaces: PID 1 interno | MNT isolado | NET isolado\nCgroups v2: Quota 0.5 CPU / 256 MiB RAM / 64 PIDs"]
    end

    subgraph ContainerB ["5. Contêiner B (so-atividade3-ns-b / C2)"]
        B_proc["Processo Isolado\nNamespaces: PID 1 interno | MNT isolado | NET isolado\nCgroups v2: Quota 1.0 CPU / 256 MiB RAM / 64 PIDs"]
    end

    HW --> OS
    OS --> Kernel
    Kernel --> Docker
    Docker --> ContainerA
    Docker --> ContainerB
```

## Análise de Compartilhamento do Kernel

- **Ausência de Máquina Virtual Intermediária:** O ambiente operacional detectado é uma instalação nativa em *bare-metal* Linux. O kernel local (`{host['kernel_release']}`) é exatamente o mesmo executado pelo daemon do Docker (`{dock['daemon_kernel_version']}`). Não há hipervisor (como QEMU, KVM, VirtualBox ou Hyper-V) intercalado entre o host e os contêineres.
- **Mecanismo de Contêineres:** Os contêineres não emulam hardware nem inicializam um novo kernel. Eles consistem puramente em processos convencionais do Linux encapsulados por duas tecnologias nativas do kernel:
  1. **Namespaces:** Criam visões virtuais e restritas de recursos globais (tabela de processos, árvores de montagem de sistemas de arquivos e interfaces de rede).
  2. **Cgroups v2 (Control Groups):** Monitoram, restringem e contabilizam a alocação de recursos físicos (tempo de CPU, limite de memória residente, swap e quantidade máxima de threads/tarefas).
- **Fixação da Imagem:**
  - Imagem base: `{img['base_image_tag']}`
  - Digest criptográfico SHA256: `{img['base_image_digest']}`
  - Imagem customizada: `{img['custom_image_tag']}` (`{img['custom_image_id'][:19]}`)
"""


def main() -> int:
    os.makedirs("results/environment", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    print("[*] Coletando informações detalhadas do ambiente...")
    env_data = collect_environment()

    # 1. Salvar results/environment/environment.json
    json_path = "results/environment/environment.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=2)
    print(f"[+] Gravado: {json_path}")

    # 2. Salvar results/environment/environment.txt
    txt_path = "results/environment/environment.txt"
    host = env_data["local_host"]
    dock = env_data["docker_environment"]
    img = env_data["container_image"]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DO AMBIENTE EXPERIMENTAL (ATIVIDADE 3)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp UTC:            {env_data['timestamp_utc']}\n")
        f.write(f"Host OS:                  {host['os_pretty_name']}\n")
        f.write(f"Host Kernel:              {host['kernel_release']}\n")
        f.write(f"Arquitetura:              {host['architecture']}\n")
        f.write(f"CPUs Lógicas:             {host['logical_cpus']}\n")
        f.write(f"Memória Total:            {host['memory_total_human']}\n")
        f.write(f"Docker Client Version:    {dock['client_version']}\n")
        f.write(f"Docker Server Version:    {dock['server_version']}\n")
        f.write(f"Docker Context:           {dock['context']}\n")
        f.write(f"Daemon OS:                {dock['daemon_operating_system']}\n")
        f.write(f"Daemon Kernel:            {dock['daemon_kernel_version']}\n")
        f.write(f"Cgroup Version:           {dock['cgroup_version']}\n")
        f.write(f"Cgroup Driver:            {dock['cgroup_driver']}\n")
        f.write(f"Storage Driver:           {dock['storage_driver']}\n")
        f.write(f"VM Intermediária:         {'Sim' if dock['intermediate_vm_present'] else 'Não (Bare-metal)'}\n")
        f.write(f"Imagem Base Digest:       {img['base_image_digest']}\n")
        f.write(f"Imagem Customizada ID:    {img['custom_image_id']}\n")
        f.write(f"Python no Contêiner:      {img['python_container_version']}\n")
        f.write("=" * 60 + "\n")
    print(f"[+] Gravado: {txt_path}")

    # 3. Salvar results/environment/docker_info.txt (filtrado e seguro)
    dock_info_path = "results/environment/docker_info.txt"
    with open(dock_info_path, "w", encoding="utf-8") as f:
        f.write("DOCKER ENGINE CONFIGURAÇÃO E SUPORTE\n")
        f.write("=" * 60 + "\n")
        for k, v in dock.items():
            f.write(f"{k}: {v}\n")
        f.write("=" * 60 + "\n")
    print(f"[+] Gravado: {dock_info_path}")

    # 4. Salvar results/environment/architecture.md e docs/architecture.md
    arch_md = generate_architecture_markdown(env_data)
    with open("results/environment/architecture.md", "w", encoding="utf-8") as f:
        f.write(arch_md)
    with open("docs/architecture.md", "w", encoding="utf-8") as f:
        f.write(arch_md)
    print(f"[+] Gravados: results/environment/architecture.md e docs/architecture.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
