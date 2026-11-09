#!/usr/bin/env python3
"""
Módulo de Verificação de Montagem Somente Leitura e Menor Privilégio (Módulo D).
Configura diretório sintético dados_demo/ com permissão 777 para isolar a política
de permissão de arquivos da restrição de montagem do kernel.
Executa contêiner com UID/GID 1000, --cap-drop=ALL, no-new-privileges:true, --network none
e bind mount com flag readonly.
Coleta e valida a leitura bem-sucedida e o bloqueio estrito de escrita com código EROFS.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Tuple


CONFIG_FILE = "config/experiment.json"
DADOS_DEMO_DIR = os.path.abspath("dados_demo")
TEXTO_FILE = os.path.join(DADOS_DEMO_DIR, "texto.txt")
RESULTS_DIR = "results/readonly"


def run_cmd(cmd: list) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def prepare_synthetic_directory() -> None:
    os.makedirs(DADOS_DEMO_DIR, exist_ok=True)
    with open(TEXTO_FILE, "w", encoding="utf-8") as f:
        f.write("Documento sintetico\n")
    # Concede permissão total na pasta sintética para garantir que eventual bloqueio seja do mount readonly
    os.chmod(DADOS_DEMO_DIR, 0o777)
    os.chmod(TEXTO_FILE, 0o644)


def generate_interpretation_markdown(data: Dict[str, Any]) -> str:
    source_path = data['mount_configuration']['source']
    try:
        source_display = os.path.relpath(source_path, os.getcwd())
    except Exception:
        source_display = source_path

    return f"""# Análise e Interpretação de Segurança: Montagem Read-Only e Menor Privilégio

Este documento formaliza as evidências experimentais da execução sob o princípio do menor privilégio e isolamento de sistemas de arquivos via montagem somente leitura (*read-only bind mount*).

## 1. Evidências Empíricas Coletadas

- **Usuário e Identidade Efetiva:** UID `{data['security_profile']['uid']}` / GID `{data['security_profile']['gid']}` (não-root).
- **Remoção de Privilégios (*Capabilities*):** `{data['security_profile']['cap_drop']}`.
- **Proteção contra Escalação:** `no-new-privileges:true` (impede transição via binários *setuid/setgid*).
- **Pilha de Rede:** `{data['security_profile']['network']}` (completamente desabilitada).
- **Ponto de Montagem:** Bind mount de `{source_display}` para `{data['mount_configuration']['target']}` com flag `readonly=true`.
- **Resultado do Teste de Leitura:**
  - Status: **{data['results']['read_status']}**
  - Conteúdo verificado: `"{data['results']['read_content']}"`
- **Resultado do Teste de Escrita:**
  - Status: **{data['results']['write_status']}**
  - Código de Erro do Kernel: **`{data['results']['error_code']}`** (`errno {data['results']['errno']}`) — *{data['results']['error_message']}*

---

## 2. Fundamentação Teórica e Diferenciação Arquitetural

### 2.1. Diferença entre Mount Namespace e Montagem Somente Leitura
- O **Mount Namespace** (`CLONE_NEWNS`) provê a **visibilidade isolada** dos pontos de montagem. Ele permite que o contêiner tenha uma árvore de diretórios própria (`/`, `/dados`, `/proc`) sem que novas montagens ou desmontagens afetem o host.
- A **Montagem Somente Leitura** (*Read-only Mount*) é um atributo do *VFS (Virtual File System)* que impõe uma **política estrita de acesso** àquele nó da árvore. Mesmo que o processo tenha visão do diretório montado, o kernel rejeita na raiz qualquer chamada de sistema de mutação (`open(O_WRONLY|O_CREAT)`, `unlink`, `rename`, `chmod`).

### 2.2. Permissões Tradicionais (DAC) vs. Bloqueio Read-only do Kernel
- No teste realizado, o diretório hospedeiro `dados_demo` foi propositalmente configurado com permissão POSIX aberta (`chmod 777`).
- Se a restrição fosse apenas baseada no DAC (*Discretionary Access Control* - usuário/grupo), o usuário UID 1000 conseguiria criar o arquivo `novo.txt` sem obstáculos.
- O fato de a chamada de sistema ter retornado o código de erro **`EROFS` (Read-only file system - errno 30)**, e **não** `EACCES` (Permission denied - errno 13), comprova categoricamente que o bloqueio ocorreu na camada do VFS/Superbloco de montagem gerenciado pelo kernel Linux, independente de permissões de arquivo.

### 2.3. O Papel do Princípio do Menor Privilégio
A combinação de:
1. Execução como usuário comum (`UID 1000`);
2. Descarte de todas as capacidades de superusuário (`--cap-drop=ALL`), desativando privilégios como `CAP_DAC_OVERRIDE`, `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`;
3. Bloqueio de novas capacidades (`no-new-privileges:true`);
4. Montagens sensíveis em modo somente leitura (`readonly`);

estabelece uma estratégia de **Defesa em Profundidade** (*Defense in Depth*). Mesmo que uma aplicação vulnerável sofra injeção de código arbitrário ou execução de payload malicioso, o atacante é incapaz de alterar arquivos de configuração, sobrescrever artefatos ou escalar privilégios no sistema.

### 2.4. Limitações: Por que Read-only não é Isolamento Absoluto?
Uma montagem *read-only* impede modificações em disco no caminho montado, mas **não** protege contra:
- **Exaustão de Recursos de Memória ou CPU:** Ataques de negação de serviço (DoS) locais precisam ser mitigados via *Cgroups*.
- **Vazamento de Informações Confidenciais:** Leitura não autorizada de dados caso segredos sejam indevidamente montados no diretório.
- **Vulnerabilidades de Kernel:** Falhas no próprio subsistema VFS do kernel Linux que permitam contorno de flags de montagem.
"""


def main() -> int:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 60)
    print("   EXECUÇÃO DO EXPERIMENTO DE MONTAGEM READ-ONLY (PARTE D)")
    print("=" * 60)

    # 1. Preparação da pasta sintética
    print("[*] Preparando diretório sintético 'dados_demo/' com chmod 777...")
    prepare_synthetic_directory()

    # Leitura da imagem configurada
    image_tag = "so-atividade3:latest"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                image_tag = cfg.get("custom_image_tag", image_tag)
        except Exception:
            pass

    container_name = "so-atividade3-readonly-test"
    run_cmd(["docker", "rm", "-f", container_name])

    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--label", "project=so-atividade3",
        "--label", "module=readonly",
        "--network", "none",
        "--user", "1000:1000",
        "--cap-drop=ALL",
        "--security-opt", "no-new-privileges:true",
        "--mount", f"type=bind,source={DADOS_DEMO_DIR},target=/dados,readonly",
        image_tag,
        "python", "/app/test_readonly.py"
    ]

    print(f"[*] Executando contêiner com menor privilégio e montagem readonly...")
    code, stdout, stderr = run_cmd(docker_cmd)

    log_path = os.path.join(RESULTS_DIR, "readonly_test.log")
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write("=== LOG DE EXECUÇÃO: TESTE DE MONTAGEM SOMENTE LEITURA ===\n")
        lf.write(f"Data UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
        lf.write(f"Código de Saída: {code}\n")
        lf.write(f"Comando Executado: {' '.join(docker_cmd)}\n\n")
        lf.write("--- STDOUT ---\n")
        lf.write(stdout + "\n\n")
        lf.write("--- STDERR ---\n")
        lf.write(stderr + "\n")

    # Extrai o JSON gerado pelo worker de teste interno
    test_json_data = None
    if "--- RESUMO DO TESTE ---" in stdout:
        try:
            json_part = stdout.split("--- RESUMO DO TESTE ---")[1].strip()
            test_json_data = json.loads(json_part)
        except Exception as e:
            sys.stderr.write(f"Aviso ao extrair JSON do resumo: {e}\n")

    read_ok = test_json_data.get("read_test", {}).get("success", False) if test_json_data else False
    read_content = test_json_data.get("read_test", {}).get("content", "") if test_json_data else ""
    write_denied = test_json_data.get("write_test", {}).get("write_denied", False) if test_json_data else False
    err_code = test_json_data.get("write_test", {}).get("error_code") if test_json_data else ""
    err_no = test_json_data.get("write_test", {}).get("errno") if test_json_data else None
    err_msg = test_json_data.get("write_test", {}).get("error_message") if test_json_data else ""

    overall_status = "PASS" if (code == 0 and read_ok and write_denied and err_code == "EROFS") else "FAIL"

    evidence_record = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "overall_status": overall_status,
        "security_profile": {
            "user": "1000:1000",
            "uid": test_json_data.get("uid", 1000) if test_json_data else 1000,
            "gid": test_json_data.get("gid", 1000) if test_json_data else 1000,
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "network": "none"
        },
        "mount_configuration": {
            "type": "bind",
            "source": DADOS_DEMO_DIR,
            "target": "/dados",
            "readonly": True,
            "host_dir_permissions": "0777 (aberto propositalmente para validar restrição do VFS)"
        },
        "results": {
            "read_status": "Sucesso" if read_ok else "Falha",
            "read_content": read_content,
            "write_status": "Bloqueado pelo Kernel" if write_denied else "Permitido (Inseguro)",
            "error_code": err_code,
            "errno": err_no,
            "error_message": err_msg,
            "exit_code": code
        }
    }

    json_path = os.path.join(RESULTS_DIR, "readonly_test.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(evidence_record, jf, indent=2)

    interp_md = generate_interpretation_markdown(evidence_record)
    interp_path = os.path.join(RESULTS_DIR, "interpretation.md")
    with open(interp_path, "w", encoding="utf-8") as mf:
        mf.write(interp_md)

    print(f"\n[+] Resultados salvos em {RESULTS_DIR}:")
    print(f"    - readonly_test.json")
    print(f"    - readonly_test.log")
    print(f"    - interpretation.md")

    print("\n" + "=" * 60)
    print(f"STATUS DO EXPERIMENTO READ-ONLY: [{overall_status}]")
    print(f"Leitura: {evidence_record['results']['read_status']} (Conteúdo: '{read_content}')")
    print(f"Escrita: {evidence_record['results']['write_status']} ({err_code} / errno {err_no} - {err_msg})")
    print("=" * 60)

    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
