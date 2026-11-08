#!/usr/bin/env python3
"""
Módulo de Limpeza Segura e Controlada (Módulo de Operações).
Identifica e remove exclusivamente contêineres e recursos criados por este projeto,
utilizando labels específicas (project=so-atividade3) e prefixos de nomes padronizados (so-atividade3-).
Nunca executa remoções globais (como docker system prune) e preserva integralmente
os arquivos de resultados, gráficos e relatórios gerados.
"""

import subprocess
import sys
from typing import List, Tuple


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def cleanup_containers() -> int:
    print("=" * 60)
    print("   LIMPEZA SEGURA DE CONTÊINERES DO PROJETO (ATIVIDADE 3)")
    print("=" * 60)

    # 1. Busca por label
    code, out_label, _ = run_cmd(["docker", "ps", "-a", "--filter", "label=project=so-atividade3", "--format", "{{.ID}} {{.Names}}"])
    
    # 2. Busca complementar por prefixo de nome seguro
    code, out_prefix, _ = run_cmd(["docker", "ps", "-a", "--filter", "name=so-atividade3-", "--format", "{{.ID}} {{.Names}}"])

    targets = {}
    for line in (out_label + "\n" + out_prefix).splitlines():
        line = line.strip()
        if line:
            parts = line.split()
            if len(parts) >= 2:
                cid, cname = parts[0], parts[1]
                targets[cid] = cname

    if not targets:
        print("[+] Nenhum contêiner remanescente do projeto encontrado em execução ou parado.")
        print("[+] O ambiente já está limpo!")
        print("=" * 60)
        return 0

    print(f"[*] Foram localizados {len(targets)} contêiner(es) pertencentes ao projeto:")
    for cid, cname in targets.items():
        print(f"    - ID: {cid[:12]} | Nome: {cname}")

    print("[*] Encerrando e removendo contêineres com segurança...")
    removed_count = 0
    for cid, cname in targets.items():
        run_cmd(["docker", "stop", "-t", "2", cid])
        code, _, err = run_cmd(["docker", "rm", "-f", cid])
        if code == 0:
            print(f"    [OK] Removido: {cname}")
            removed_count += 1
        else:
            print(f"    [ERRO] Falha ao remover {cname}: {err}", file=sys.stderr)

    print("=" * 60)
    print(f"[+] Limpeza concluída: {removed_count} contêiner(es) removido(s) com sucesso.")
    print("[+] Observação: Todos os logs, CSVs, dados brutos e relatórios foram preservados.")
    print("=" * 60)
    return 0


def main() -> int:
    return cleanup_containers()


if __name__ == "__main__":
    sys.exit(main())
