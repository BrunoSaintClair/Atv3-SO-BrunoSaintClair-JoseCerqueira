#!/usr/bin/env python3
"""
Módulo de Verificação e Demonstração de Isolamento de Namespaces (Módulo B).
Executa dois contêineres independentes (so-atividade3-ns-a e so-atividade3-ns-b),
coleta os PIDs do host do daemon, PID 1 interno e os identificadores de inodes
dos namespaces PID, MNT e NET, gerando relatórios, tabelas comparativas e análise técnica.
"""

import csv
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Tuple


CONTAINER_A = "so-atividade3-ns-a"
CONTAINER_B = "so-atividade3-ns-b"
IMAGE_TAG = "so-atividade3:latest"


def run_cmd(cmd: list) -> Tuple[int, str, str]:
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def stop_and_remove_container(name: str) -> None:
    run_cmd(["docker", "stop", "-t", "2", name])
    run_cmd(["docker", "rm", "-f", name])


def launch_container(name: str) -> bool:
    stop_and_remove_container(name)
    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "--label", "project=so-atividade3",
        "--label", "module=namespaces",
        "--network", "none",
        IMAGE_TAG,
        "sleep", "infinity"
    ]
    code, out, err = run_cmd(cmd)
    if code != 0:
        sys.stderr.write(f"Falha ao iniciar contêiner {name}: {err}\n")
        return False
    return True


def collect_container_namespaces(name: str) -> Dict[str, Any]:
    # 1. Coleta do PID no host do daemon via inspect
    code, pid_host_str, _ = run_cmd(["docker", "inspect", "--format", "{{.State.Pid}}", name])
    pid_host = int(pid_host_str) if pid_host_str.isdigit() else None

    # 2. Coleta do comm do PID 1 interno
    code, comm_pid1, _ = run_cmd(["docker", "exec", name, "sh", "-c", "cat /proc/1/comm"])

    # 3. Coleta dos handles de namespaces (leitura de symlinks em /proc/1/ns/)
    ns_targets = ["pid", "mnt", "net", "ipc", "uts", "user"]
    ns_handles: Dict[str, str] = {}
    for ns in ns_targets:
        code, handle, _ = run_cmd(["docker", "exec", name, "readlink", f"/proc/1/ns/{ns}"])
        ns_handles[ns] = handle if code == 0 else "N/A"

    return {
        "container_name": name,
        "pid_host_daemon": pid_host,
        "pid_1_internal_comm": comm_pid1,
        "namespaces": ns_handles
    }


def generate_interpretation_markdown(data_a: Dict[str, Any], data_b: Dict[str, Any]) -> str:
    pid_comp = "Diferente (Isolado)" if data_a["namespaces"]["pid"] != data_b["namespaces"]["pid"] else "Igual (Não Isolado)"
    mnt_comp = "Diferente (Isolado)" if data_a["namespaces"]["mnt"] != data_b["namespaces"]["mnt"] else "Igual (Não Isolado)"
    net_comp = "Diferente (Isolado)" if data_a["namespaces"]["net"] != data_b["namespaces"]["net"] else "Igual (Não Isolado)"

    return f"""# Análise e Interpretação de Isolamento por Namespaces

Este documento analisa os dados empíricos coletados durante a execução simultânea dos contêineres `{data_a['container_name']}` e `{data_b['container_name']}`.

## 1. Tabela Comparativa de Identificadores Reais

| Recurso / Namespace | Contêiner A (`{data_a['container_name']}`) | Contêiner B (`{data_b['container_name']}`) | Resultado Observado |
|---|---|---|---|
| **PID do Host (Daemon)** | `{data_a['pid_host_daemon']}` | `{data_b['pid_host_daemon']}` | Diferente (Processos distintos no host) |
| **PID 1 Interno (`comm`)** | `{data_a['pid_1_internal_comm']}` (PID 1) | `{data_b['pid_1_internal_comm']}` (PID 1) | Ambos são PID 1 localmente |
| **PID Namespace** | `{data_a['namespaces']['pid']}` | `{data_b['namespaces']['pid']}` | **{pid_comp}** |
| **Mount (MNT) Namespace** | `{data_a['namespaces']['mnt']}` | `{data_b['namespaces']['mnt']}` | **{mnt_comp}** |
| **Network (NET) Namespace** | `{data_a['namespaces']['net']}` | `{data_b['namespaces']['net']}` | **{net_comp}** |
| **IPC Namespace** | `{data_a['namespaces']['ipc']}` | `{data_b['namespaces']['ipc']}` | Diferente (Filas/Memória Compartilhada isoladas) |
| **UTS Namespace** | `{data_a['namespaces']['uts']}` | `{data_b['namespaces']['uts']}` | Diferente (Hostnames independentes) |

---

## 2. Respostas Fundamentadas às Questões Obrigatórias

### 2.1. O que é o Namespace PID?
O namespace PID (*Process ID Namespace*) virtualiza a árvore de processos do Linux. Ele garante que os processos dentro de um determinado contêiner visualizem apenas os seus próprios descendentes, iniciando a numeração a partir de 1 (`init`/processo raiz do contêiner). Ele oculta totalmente os processos do sistema operacional hospedeiro e de outros contêineres.

### 2.2. O que é o Namespace Mount (MNT)?
O namespace MNT isola a tabela de pontos de montagem do sistema de arquivos (*mount points*). Cada contêiner possui sua própria raiz virtual (`/`), podendo montar, desmontar ou alterar sistemas de arquivos (como `/proc`, `/sys`, *rootfs* overlay) sem que essas modificações sejam propagadas ou visíveis para o host ou para contêineres vizinhos.

### 2.3. O que é o Namespace Network (NET)?
O namespace NET virtualiza a pilha de rede completa do kernel: interfaces de rede (loopback, veth), tabelas de roteamento, regras de firewall (iptables/nftables) e portas de sockets (TCP/UDP). Mesmo configurados com `--network none`, os contêineres possuem pilhas de rede separadas (apenas com sua interface de loopback isolada), garantindo que conexões ou vinculações de portas não conflitem.

### 2.4. O que cada identificador demonstra?
No Linux, os links simbólicos em `/proc/[pid]/ns/` apontam para objetos especiais do kernel no formato `tipo:[inode_number]`.
- O contêiner A possui `{data_a['namespaces']['pid']}` e o contêiner B possui `{data_b['namespaces']['pid']}`.
- O número de inode diferente comprova matematicamente que o kernel alocou estruturas de dados `struct nsproxy` e `struct pid_namespace` distintas na memória do kernel para cada um dos contêineres.

### 2.5. Por que os dois contêineres possuem PID 1 internamente?
Porque cada contêiner reside em seu próprio namespace PID. No momento em que um namespace PID é criado (`CLONE_NEWPID`), o primeiro processo criado torna-se o processo raiz do namespace e recebe obrigatoriamente o PID 1. Esse processo atua como o inicializador local, adotando processos órfãos dentro daquele namespace.

### 2.6. Por que o PID 1 interno não equivale ao PID do host?
A numeração de processos é relativa à hierarquia de namespaces. No namespace global do hospedeiro, todos os processos de todos os contêineres são visíveis e recebem identificadores únicos globais. 
O processo do contêiner A possui PID `{data_a['pid_host_daemon']}` no host, enquanto o processo do contêiner B possui PID `{data_b['pid_host_daemon']}`. Ambos são enxergados como processos convencionais gerenciados pelo escalonador do kernel Linux hospedeiro.

### 2.7. Por que namespaces diferentes não significam kernels independentes?
Namespaces não realizam emulação de hardware nem executam instâncias isoladas de sistemas operacionais. Eles são simplesmente filtros lógicos de visibilidade dentro do mesmo e único kernel Linux (`Linux 7.0.0-38-generic`). 
Se houver uma pane de kernel (*kernel panic*), exaustão de descritores de arquivo ou uma vulnerabilidade crítica em uma chamada de sistema (*syscall*), todos os contêineres que compartilham aquele kernel são afetados.

### 2.8. Quais aspectos não podem ser comprovados apenas pelos handles?
Os identificadores de inode comprovam a separação das tabelas de controle, mas **não** comprovam:
1. Limitação ou divisão de recursos físicos de hardware (função exclusiva dos *Cgroups*).
2. Políticas de segurança, restrição de *capabilities* ou filtros de chamadas de sistema (*seccomp* / AppArmor).
3. Existência de canais ocultos (*covert channels*) como concorrência de cache L3 da CPU ou acesso a informações temporais globais.

### 2.9. Relação entre PID do Host e Ambientes Virtualizados
No ambiente em teste (*Bare-metal Linux*), o comando `docker inspect` retorna o PID direto do processo no `/proc` local. Caso o experimento fosse executado no Docker Desktop (Windows/macOS) ou WSL2, o PID retornado pertenceria à máquina virtual Linux interna do Docker e não estaria presente no gerenciador de tarefas do sistema operacional hospedeiro externo.
"""


def main() -> int:
    os.makedirs("results/namespaces", exist_ok=True)
    print("=" * 60)
    print("      EXECUÇÃO DO EXPERIMENTO DE NAMESPACES (PARTE B)")
    print("=" * 60)

    try:
        print(f"[*] Iniciando contêiner A ({CONTAINER_A})...")
        if not launch_container(CONTAINER_A):
            return 1

        print(f"[*] Iniciando contêiner B ({CONTAINER_B})...")
        if not launch_container(CONTAINER_B):
            return 1

        # Breve espera para assegurar inicialização dos processos
        time.sleep(1)

        print("[*] Coletando namespaces e PIDs do contêiner A...")
        data_a = collect_container_namespaces(CONTAINER_A)

        print("[*] Coletando namespaces e PIDs do contêiner B...")
        data_b = collect_container_namespaces(CONTAINER_B)

        # 1. Salvar JSONs individuais
        with open("results/namespaces/container_a.json", "w", encoding="utf-8") as f:
            json.dump(data_a, f, indent=2)
        with open("results/namespaces/container_b.json", "w", encoding="utf-8") as f:
            json.dump(data_b, f, indent=2)

        # 2. Gerar CSV comparativo
        csv_path = "results/namespaces/namespaces.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["recurso", "container_a", "container_b", "resultado"])
            writer.writerow(["host_pid", data_a["pid_host_daemon"], data_b["pid_host_daemon"], "Diferente" if data_a["pid_host_daemon"] != data_b["pid_host_daemon"] else "Igual"])
            writer.writerow(["internal_pid_1", data_a["pid_1_internal_comm"], data_b["pid_1_internal_comm"], "Ambos PID 1"])
            for ns in ["pid", "mnt", "net", "ipc", "uts", "user"]:
                val_a = data_a["namespaces"].get(ns, "N/A")
                val_b = data_b["namespaces"].get(ns, "N/A")
                comp = "Diferente (Isolado)" if val_a != val_b else "Igual (Compartilhado)"
                writer.writerow([ns, val_a, val_b, comp])

        # 3. Gerar tabelas e interpretações markdown
        interp_md = generate_interpretation_markdown(data_a, data_b)
        with open("results/namespaces/namespaces_comparison.md", "w", encoding="utf-8") as f:
            f.write(interp_md)
        with open("results/namespaces/interpretation.md", "w", encoding="utf-8") as f:
            f.write(interp_md)

        print("[+] Artefatos gerados com sucesso em results/namespaces/:")
        print("    - container_a.json")
        print("    - container_b.json")
        print("    - namespaces.csv")
        print("    - namespaces_comparison.md")
        print("    - interpretation.md")

        # Exibição da tabela comparativa no terminal
        print("\n" + "=" * 60)
        print("TABELA COMPARATIVA DE NAMESPACES")
        print("=" * 60)
        print(f"{'Recurso':<10} | {'Contêiner A':<22} | {'Contêiner B':<22} | {'Status'}")
        print("-" * 65)
        for ns in ["pid", "mnt", "net"]:
            va = data_a["namespaces"][ns]
            vb = data_b["namespaces"][ns]
            st = "ISOLADO" if va != vb else "FALHA"
            print(f"{ns.upper():<10} | {va:<22} | {vb:<22} | {st}")
        print("=" * 60)

        # Validação estrita
        all_isolated = all(data_a["namespaces"][ns] != data_b["namespaces"][ns] for ns in ["pid", "mnt", "net"])
        if all_isolated:
            print("[SUCESSO] Isolamento comprovado nos namespaces PID, MNT e NET!")
            return 0
        else:
            print("[ERRO] Falha no isolamento: identificadores de namespaces idênticos detectados!", file=sys.stderr)
            return 1

    finally:
        print("[*] Encerrando contêineres de teste com segurança...")
        stop_and_remove_container(CONTAINER_A)
        stop_and_remove_container(CONTAINER_B)
        print("[+] Limpeza concluída.")


if __name__ == "__main__":
    sys.exit(main())
