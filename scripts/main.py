#!/usr/bin/env python3
"""
Orquestrador Geral e Ponto Único de Entrada — Atividade 3 (Seção 11).
Sistemas Operacionais | Virtualização, Contêineres, Namespaces e Cgroups v2

Comandos disponíveis:
  python scripts/main.py check        # Verifica ambiente e pré-requisitos
  python scripts/main.py environment  # Coleta informações da infraestrutura
  python scripts/main.py namespaces   # Executa o experimento de namespaces
  python scripts/main.py pilot        # Executa teste piloto da carga de CPU
  python scripts/main.py cgroups      # Executa as 6 medições oficiais
  python scripts/main.py readonly     # Executa experimento de menor privilégio e read-only
  python scripts/main.py analyze      # Consolida dados em CSV, estatísticas e gráficos
  python scripts/main.py report       # Gera o relatório técnico em Markdown e PDF
  python scripts/main.py cleanup      # Limpeza segura de contêineres do projeto
  python scripts/main.py validate     # Validação final automática de conformidade
  python scripts/main.py all          # Executa o pipeline completo de ponta a ponta
"""

import argparse
import os
import subprocess
import sys
from typing import List


def run_script(script_name: str, extra_args: List[str] = None) -> int:
    cmd = [sys.executable, os.path.join("scripts", script_name)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd)
    return proc.returncode


def cmd_check(args) -> int:
    return run_script("check_environment.py")


def cmd_environment(args) -> int:
    return run_script("collect_environment.py")


def cmd_namespaces(args) -> int:
    return run_script("run_namespaces.py")


def cmd_pilot(args) -> int:
    return run_script("run_cgroups.py", ["--pilot"])


def cmd_cgroups(args) -> int:
    return run_script("run_cgroups.py", ["--run-all"])


def cmd_readonly(args) -> int:
    return run_script("run_readonly.py")


def cmd_analyze(args) -> int:
    c1 = run_script("generate_results.py")
    if c1 != 0:
        return c1
    return run_script("generate_graphs.py")


def cmd_report(args) -> int:
    return run_script("generate_report.py")


def cmd_cleanup(args) -> int:
    return run_script("cleanup.py")


def cmd_validate(args) -> int:
    return run_script("verify_all.py")


def cmd_all(args) -> int:
    print("=" * 65)
    print("    INÍCIO DA EXECUÇÃO COMPLETA DO PIPELINE (OPÇÃO 'ALL')")
    print("=" * 65)

    steps = [
        ("1. Verificação de Pré-requisitos", "check_environment.py", None),
        ("2. Documentação do Ambiente e Arquitetura", "collect_environment.py", None),
        ("3. Experimento de Namespaces", "run_namespaces.py", None),
        ("4. Teste Piloto e Congelamento de Iterações", "run_cgroups.py", ["--pilot"]),
    ]

    for label, script, extra in steps:
        print(f"\n>>> Executando Etapa: {label}...")
        rc = run_script(script, extra)
        if rc != 0:
            print(f"\n[ERRO CRÍTICO] Falha na etapa '{label}' (Código de saída: {rc}).", file=sys.stderr)
            print("Interrompendo pipeline para preservar integridade.", file=sys.stderr)
            return rc

    # Confirmação antes das 6 medições oficiais
    print("\n" + "-" * 65)
    print("PRÉ-CONDIÇÕES ATENDIDAS E ITERAÇÕES CONGELADAS COM SUCESSO!")
    print("A próxima etapa executará as 6 medições oficiais alternadas (C1 e C2).")
    print("-" * 65)

    if not getattr(args, "yes", False):
        try:
            answer = input("Deseja prosseguir com as 6 medições oficiais? [S/n]: ").strip().lower()
            if answer in ["n", "nao", "não", "no"]:
                print("[*] Execução interrompida pelo usuário antes das medições oficiais.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Operação abortada.")
            return 1

    remaining_steps = [
        ("5. Seis Medições Oficiais de Cgroups v2", "run_cgroups.py", ["--run-all"]),
        ("6. Experimento Read-Only e Menor Privilégio", "run_readonly.py", None),
        ("7. Consolidação de Resultados CSV e Estatísticas", "generate_results.py", None),
        ("8. Geração de Gráficos em Alta Resolução", "generate_graphs.py", None),
        ("9. Geração do Relatório Técnico (Markdown e PDF)", "generate_report.py", None),
        ("10. Validação Final Automática dos Resultados", "verify_all.py", None),
    ]

    for label, script, extra in remaining_steps:
        print(f"\n>>> Executando Etapa: {label}...")
        rc = run_script(script, extra)
        if rc != 0:
            print(f"\n[ERRO CRÍTICO] Falha na etapa '{label}' (Código de saída: {rc}).", file=sys.stderr)
            return rc

    print("\n" + "=" * 65)
    print("    PIPELINE COMPLETO EXECUTADO COM SUCESSO ABSOLUTO!")
    print("    Todos os relatórios, gráficos e evidências estão prontos.")
    print("=" * 65)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ponto único de orquestração para os experimentos da Atividade 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exemplos de uso:\n"
               "  python scripts/main.py check\n"
               "  python scripts/main.py all --yes\n"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcomando a executar")

    subparsers.add_parser("check", help="Verifica o ambiente e pré-requisitos").set_defaults(func=cmd_check)
    subparsers.add_parser("environment", help="Coleta metadados da infraestrutura").set_defaults(func=cmd_environment)
    subparsers.add_parser("namespaces", help="Executa experimento de namespaces").set_defaults(func=cmd_namespaces)
    subparsers.add_parser("pilot", help="Executa teste piloto da carga de CPU").set_defaults(func=cmd_pilot)
    subparsers.add_parser("cgroups", help="Executa as seis medições oficiais").set_defaults(func=cmd_cgroups)
    subparsers.add_parser("readonly", help="Executa experimento read-only").set_defaults(func=cmd_readonly)
    subparsers.add_parser("analyze", help="Consolida dados e gera gráficos").set_defaults(func=cmd_analyze)
    subparsers.add_parser("report", help="Gera relatório em Markdown e PDF").set_defaults(func=cmd_report)
    subparsers.add_parser("cleanup", help="Limpa contêineres do projeto com segurança").set_defaults(func=cmd_cleanup)
    subparsers.add_parser("validate", help="Executa validação final de integridade").set_defaults(func=cmd_validate)

    p_all = subparsers.add_parser("all", help="Executa a sequência completa de experimentos")
    p_all.add_argument("-y", "--yes", action="store_true", help="Confirma automaticamente as 6 medições sem prompt interativo")
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
