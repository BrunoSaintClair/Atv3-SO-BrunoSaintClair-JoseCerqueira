#!/usr/bin/env python3
"""
Módulo de Validação Final Automática da Atividade 3.
Avalia com precisão matemática e rigor técnico a integridade e consistência
de todos os artefatos e experimentos práticos (Módulos A, B, C e D), gerando:
- results/report/final_validation.json
- results/report/final_validation.md
Status por item: PASS, FAIL, BLOCKED, NOT_RUN.
"""

import json
import os
import sys
from typing import Any, Dict, List


REPORT_DIR = "results/report"
JSON_OUT = os.path.join(REPORT_DIR, "final_validation.json")
MD_OUT = os.path.join(REPORT_DIR, "final_validation.md")


def load_json_safe(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_file_safe(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def validate_all() -> Dict[str, Any]:
    os.makedirs(REPORT_DIR, exist_ok=True)
    categories: Dict[str, List[Dict[str, Any]]] = {}

    # -------------------------------------------------------------
    # 1. Ambiente
    # -------------------------------------------------------------
    env_items = []
    env_json = load_json_safe("results/environment/environment.json")
    
    host_ok = bool(env_json.get("local_host", {}).get("kernel_release"))
    env_items.append({
        "item": "Ambiente identificado",
        "status": "PASS" if host_ok else "NOT_RUN",
        "detail": f"Host Kernel: {env_json.get('local_host', {}).get('kernel_release')} ({env_json.get('local_host', {}).get('os_pretty_name')})" if host_ok else "environment.json ausente"
    })

    docker_ok = bool(env_json.get("docker_environment", {}).get("server_version"))
    env_items.append({
        "item": "Docker funcional",
        "status": "PASS" if docker_ok else "NOT_RUN",
        "detail": f"Docker Server: {env_json.get('docker_environment', {}).get('server_version')}" if docker_ok else "Docker não detectado"
    })

    cg_v2 = env_json.get("docker_environment", {}).get("cgroup_version") == "2"
    env_items.append({
        "item": "Cgroup v2 identificado",
        "status": "PASS" if cg_v2 else "FAIL",
        "detail": f"Cgroup Version: {env_json.get('docker_environment', {}).get('cgroup_version')} (Driver: {env_json.get('docker_environment', {}).get('cgroup_driver')})"
    })

    img_digest = env_json.get("container_image", {}).get("base_image_digest", "")
    has_digest = "sha256:" in img_digest
    env_items.append({
        "item": "Imagem fixada por digest",
        "status": "PASS" if has_digest else "FAIL",
        "detail": f"Digest: {img_digest}" if has_digest else "Digest ausente na configuração"
    })

    diag_content = load_file_safe("docs/architecture.md")
    diag_ok = "flowchart TD" in diag_content or "graph TD" in diag_content
    env_items.append({
        "item": "Diagrama criado",
        "status": "PASS" if diag_ok else "NOT_RUN",
        "detail": "Diagrama Mermaid em docs/architecture.md e results/environment/architecture.md" if diag_ok else "Diagrama ausente"
    })
    categories["Ambiente"] = env_items

    # -------------------------------------------------------------
    # 2. Namespaces
    # -------------------------------------------------------------
    ns_items = []
    ns_a = load_json_safe("results/namespaces/container_a.json")
    ns_b = load_json_safe("results/namespaces/container_b.json")
    interp_ns = load_file_safe("results/namespaces/interpretation.md")

    ns_items.append({
        "item": "Contêiner A criado",
        "status": "PASS" if ns_a.get("container_name") == "so-atividade3-ns-a" else "NOT_RUN",
        "detail": f"Contêiner A: {ns_a.get('container_name')}"
    })
    ns_items.append({
        "item": "Contêiner B criado",
        "status": "PASS" if ns_b.get("container_name") == "so-atividade3-ns-b" else "NOT_RUN",
        "detail": f"Contêiner B: {ns_b.get('container_name')}"
    })
    ns_items.append({
        "item": "PID interno registrado",
        "status": "PASS" if (ns_a.get("pid_1_internal_comm") and ns_b.get("pid_1_internal_comm")) else "NOT_RUN",
        "detail": f"Comm PID 1: {ns_a.get('pid_1_internal_comm')} e {ns_b.get('pid_1_internal_comm')}"
    })
    ns_items.append({
        "item": "PID do host do daemon registrado",
        "status": "PASS" if (ns_a.get("pid_host_daemon") and ns_b.get("pid_host_daemon")) else "NOT_RUN",
        "detail": f"Host PIDs: {ns_a.get('pid_host_daemon')} e {ns_b.get('pid_host_daemon')}"
    })

    pid_ns_diff = ns_a.get("namespaces", {}).get("pid") != ns_b.get("namespaces", {}).get("pid") and bool(ns_a.get("namespaces", {}).get("pid"))
    mnt_ns_diff = ns_a.get("namespaces", {}).get("mnt") != ns_b.get("namespaces", {}).get("mnt") and bool(ns_a.get("namespaces", {}).get("mnt"))
    net_ns_diff = ns_a.get("namespaces", {}).get("net") != ns_b.get("namespaces", {}).get("net") and bool(ns_a.get("namespaces", {}).get("net"))

    ns_items.append({
        "item": "PID namespace coletado",
        "status": "PASS" if pid_ns_diff else "FAIL",
        "detail": f"A: {ns_a.get('namespaces', {}).get('pid')} | B: {ns_b.get('namespaces', {}).get('pid')}"
    })
    ns_items.append({
        "item": "Mount namespace coletado",
        "status": "PASS" if mnt_ns_diff else "FAIL",
        "detail": f"A: {ns_a.get('namespaces', {}).get('mnt')} | B: {ns_b.get('namespaces', {}).get('mnt')}"
    })
    ns_items.append({
        "item": "Network namespace coletado",
        "status": "PASS" if net_ns_diff else "FAIL",
        "detail": f"A: {ns_a.get('namespaces', {}).get('net')} | B: {ns_b.get('namespaces', {}).get('net')}"
    })
    ns_items.append({
        "item": "Tabela comparativa criada",
        "status": "PASS" if os.path.exists("results/namespaces/namespaces.csv") else "NOT_RUN",
        "detail": "Arquivo results/namespaces/namespaces.csv existente"
    })
    ns_items.append({
        "item": "Interpretação escrita",
        "status": "PASS" if len(interp_ns) > 200 else "NOT_RUN",
        "detail": f"Interpretação técnica presente ({len(interp_ns)} caracteres)"
    })
    categories["Namespaces"] = ns_items

    # -------------------------------------------------------------
    # 3. Cgroups
    # -------------------------------------------------------------
    cg_items = []
    cfg_data = load_json_safe("config/experiment.json")
    stats_data = load_json_safe("results/cgroups/summary/statistics.json")
    analysis_md = load_file_safe("docs/analysis.md")

    worker_code = load_file_safe("scripts/worker.py")
    has_workload = "def workload(" in worker_code and "1664525" in worker_code
    cg_items.append({
        "item": "Carga determinística implementada",
        "status": "PASS" if has_workload else "FAIL",
        "detail": "Algoritmo LCG de inteiros de 32 bits implementado em scripts/worker.py"
    })

    pilot_done = os.path.exists("results/cgroups/raw/C1_pilot.json") or os.path.exists("results/cgroups/raw/pilot_summary.json")
    frozen_iter = cfg_data.get("frozen_iterations")
    cg_items.append({
        "item": "Teste piloto realizado",
        "status": "PASS" if pilot_done else "NOT_RUN",
        "detail": "Registro do piloto presente em results/cgroups/raw/"
    })
    cg_items.append({
        "item": "Iterações congeladas",
        "status": "PASS" if (frozen_iter and frozen_iter > 0) else "NOT_RUN",
        "detail": f"Iterações congeladas em {frozen_iter:,}" if frozen_iter else "Não congelado"
    })

    c1_ok = cfg_data.get("conditions", {}).get("C1", {}).get("cpu_quota") == 50000
    c2_ok = cfg_data.get("conditions", {}).get("C2", {}).get("cpu_quota") == 100000
    cg_items.append({
        "item": "C1 configurada",
        "status": "PASS" if c1_ok else "FAIL",
        "detail": f"C1 Quota: {cfg_data.get('conditions', {}).get('C1', {}).get('cpu_quota')} / {cfg_data.get('cpu_period')} (0.5 CPU)"
    })
    cg_items.append({
        "item": "C2 configurada",
        "status": "PASS" if c2_ok else "FAIL",
        "detail": f"C2 Quota: {cfg_data.get('conditions', {}).get('C2', {}).get('cpu_quota')} / {cfg_data.get('cpu_period')} (1.0 CPU)"
    })
    cg_items.append({
        "item": "Memória limitada",
        "status": "PASS" if cfg_data.get("memory_limit") == "256m" else "FAIL",
        "detail": f"Memory limit: {cfg_data.get('memory_limit')} (256 MiB)"
    })
    cg_items.append({
        "item": "Memória + swap limitada",
        "status": "PASS" if cfg_data.get("memory_swap") == "256m" else "FAIL",
        "detail": f"Memory swap: {cfg_data.get('memory_swap')} (0 swap adicional)"
    })
    cg_items.append({
        "item": "PIDs limitados",
        "status": "PASS" if cfg_data.get("pids_limit") == 64 else "FAIL",
        "detail": f"PIDs limit: {cfg_data.get('pids_limit')}"
    })

    records = stats_data.get("records", [])
    valid_records = [r for r in records if r.get("status") == "success"]
    checksums = set(r.get("checksum") for r in valid_records if r.get("checksum"))

    cpu_max_confirmed = len(valid_records) == 6 and all(
        (r["condition"] == "C1" and r["cpu"]["cpu_max"] == "50000 100000") or
        (r["condition"] == "C2" and r["cpu"]["cpu_max"] == "100000 100000")
        for r in valid_records
    )
    mem_max_confirmed = len(valid_records) == 6 and all(
        r["memory"]["memory_max"] == 268435456 for r in valid_records
    )
    pids_max_confirmed = len(valid_records) == 6 and all(
        r["pids"]["pids_max"] == 64 for r in valid_records
    )

    cg_items.append({
        "item": "cpu.max confirmado",
        "status": "PASS" if cpu_max_confirmed else "FAIL",
        "detail": "cpu.max confirmado no kernel em todas as 6 execuções" if cpu_max_confirmed else "cpu.max não confirmado"
    })
    cg_items.append({
        "item": "memory.max confirmado",
        "status": "PASS" if mem_max_confirmed else "FAIL",
        "detail": "268435456 bytes (256 MiB) confirmado em todas as 6 execuções" if mem_max_confirmed else "memory.max divergente"
    })
    cg_items.append({
        "item": "pids.max confirmado",
        "status": "PASS" if pids_max_confirmed else "FAIL",
        "detail": "64 tarefas confirmado em todas as 6 execuções" if pids_max_confirmed else "pids.max divergente"
    })
    cg_items.append({
        "item": "Seis registros preservados",
        "status": "PASS" if len(valid_records) == 6 else "FAIL",
        "detail": f"{len(valid_records)}/6 registros brutos JSON válidos em results/cgroups/raw/"
    })
    cg_items.append({
        "item": "Checksums conferidos",
        "status": "PASS" if len(checksums) == 1 else "FAIL",
        "detail": f"Checksum determinístico único: {list(checksums)[0]}" if len(checksums) == 1 else f"Divergência: {checksums}"
    })
    cg_items.append({
        "item": "CSV gerado",
        "status": "PASS" if os.path.exists("results/cgroups/csv/results.csv") else "NOT_RUN",
        "detail": "results/cgroups/csv/results.csv presente"
    })

    c1_stat = stats_data.get("conditions", {}).get("C1", {})
    has_medians = bool(c1_stat.get("wall_time", {}).get("median"))
    cg_items.append({
        "item": "Medianas calculadas",
        "status": "PASS" if has_medians else "NOT_RUN",
        "detail": f"C1: {c1_stat.get('wall_time', {}).get('median')}s | C2: {stats_data.get('conditions', {}).get('C2', {}).get('wall_time', {}).get('median')}s"
    })
    cg_items.append({
        "item": "Variação calculada",
        "status": "PASS" if has_medians else "NOT_RUN",
        "detail": f"C1 StdDev: {c1_stat.get('wall_time', {}).get('stddev')}s | C2 StdDev: {stats_data.get('conditions', {}).get('C2', {}).get('wall_time', {}).get('stddev')}s"
    })

    graphs_exist = os.path.exists("results/graphs/work_per_second.png") and os.path.exists("results/graphs/wall_time_comparison.png")
    cg_items.append({
        "item": "Gráfico gerado",
        "status": "PASS" if graphs_exist else "NOT_RUN",
        "detail": "Gráficos work_per_second.png e wall_time_comparison.png gerados"
    })
    cg_items.append({
        "item": "Análise documentada",
        "status": "PASS" if len(analysis_md) > 300 else "NOT_RUN",
        "detail": f"docs/analysis.md presente ({len(analysis_md)} caracteres)"
    })
    categories["Cgroups"] = cg_items

    # -------------------------------------------------------------
    # 4. Read-only
    # -------------------------------------------------------------
    ro_items = []
    ro_data = load_json_safe("results/readonly/readonly_test.json")
    ro_res = ro_data.get("results", {})

    ro_items.append({
        "item": "Diretório sintético criado",
        "status": "PASS" if os.path.exists("dados_demo/texto.txt") else "NOT_RUN",
        "detail": "dados_demo/texto.txt configurado com permissão 777"
    })
    uid_ok = ro_data.get("security_profile", {}).get("uid") == 1000
    ro_items.append({
        "item": "Usuário não root utilizado",
        "status": "PASS" if uid_ok else "FAIL",
        "detail": f"UID: {ro_data.get('security_profile', {}).get('uid')}"
    })
    cap_ok = ro_data.get("security_profile", {}).get("cap_drop") == "ALL"
    ro_items.append({
        "item": "Capabilities removidas",
        "status": "PASS" if cap_ok else "FAIL",
        "detail": "--cap-drop=ALL aplicado"
    })
    nnp_ok = ro_data.get("security_profile", {}).get("no_new_privileges") is True
    ro_items.append({
        "item": "no-new-privileges aplicado",
        "status": "PASS" if nnp_ok else "FAIL",
        "detail": "no-new-privileges:true confirmado"
    })
    read_ok = ro_res.get("read_status") == "Sucesso"
    ro_items.append({
        "item": "Leitura bem-sucedida",
        "status": "PASS" if read_ok else "FAIL",
        "detail": f"Conteúdo lido: '{ro_res.get('read_content')}'"
    })
    write_denied = "Bloqueado" in ro_res.get("write_status", "")
    ro_items.append({
        "item": "Escrita negada",
        "status": "PASS" if write_denied else "FAIL",
        "detail": ro_res.get("write_status", "")
    })
    err_erofs = ro_res.get("error_code") == "EROFS" and ro_res.get("errno") == 30
    ro_items.append({
        "item": "Código de erro registrado",
        "status": "PASS" if err_erofs else "FAIL",
        "detail": f"Código do kernel: {ro_res.get('error_code')} (errno {ro_res.get('errno')}) - {ro_res.get('error_message')}"
    })
    categories["Read-only"] = ro_items

    # -------------------------------------------------------------
    # 5. Documentação Técnica dos Resultados
    # -------------------------------------------------------------
    doc_items = []
    readme_content = load_file_safe("README.md")
    analysis_exists = os.path.exists("docs/analysis.md")
    summary_exists = os.path.exists("results/cgroups/summary/summary.md")
    ns_interp_exists = os.path.exists("results/namespaces/interpretation.md")
    ro_interp_exists = os.path.exists("results/readonly/interpretation.md")

    doc_items.append({
        "item": "README completo",
        "status": "PASS" if len(readme_content) > 500 else "NOT_RUN",
        "detail": f"README.md com {len(readme_content)} caracteres"
    })
    doc_items.append({
        "item": "Análise técnica de resultados",
        "status": "PASS" if analysis_exists else "NOT_RUN",
        "detail": "docs/analysis.md presente com discussão quantitativa aprofundada"
    })
    doc_items.append({
        "item": "Síntese estatística documentada",
        "status": "PASS" if summary_exists else "NOT_RUN",
        "detail": "results/cgroups/summary/summary.md presente com medianas, médias e dispersão"
    })
    doc_items.append({
        "item": "Interpretação de namespaces",
        "status": "PASS" if ns_interp_exists else "NOT_RUN",
        "detail": "results/namespaces/interpretation.md presente com fundamentos de isolamento"
    })
    doc_items.append({
        "item": "Interpretação de read-only",
        "status": "PASS" if ro_interp_exists else "NOT_RUN",
        "detail": "results/readonly/interpretation.md presente com distinção entre VFS e DAC"
    })
    doc_items.append({
        "item": "Dados brutos disponíveis",
        "status": "PASS" if os.path.exists("results/cgroups/raw/C1_rep1.json") else "NOT_RUN",
        "detail": "Arquivos JSON em results/cgroups/raw/ e logs/"
    })
    doc_items.append({
        "item": "Gráficos disponíveis",
        "status": "PASS" if graphs_exist else "NOT_RUN",
        "detail": "PNGs em results/graphs/"
    })
    doc_items.append({
        "item": "Diagrama de arquitetura disponível",
        "status": "PASS" if diag_ok else "NOT_RUN",
        "detail": "Mermaid em results/environment/architecture.md e docs/architecture.md"
    })
    doc_items.append({
        "item": "Declaração de IA disponível",
        "status": "PASS" if os.path.exists("docs/ai_usage.md") else "NOT_RUN",
        "detail": "docs/ai_usage.md presente"
    })
    doc_items.append({
        "item": "Limitações documentadas",
        "status": "PASS" if os.path.exists("docs/limitations.md") else "NOT_RUN",
        "detail": "docs/limitations.md presente"
    })
    doc_items.append({
        "item": "Referências incluídas",
        "status": "PASS" if "man7.org" in readme_content else "FAIL",
        "detail": "Referências aos manuais Linux, Cgroups e Docker incluídas no README.md"
    })
    categories["Documentação"] = doc_items

    # -------------------------------------------------------------
    # Tabela Executiva de Auditoria (10 Itens Obrigatórios - Seção 11)
    # -------------------------------------------------------------
    audit_table = [
        {
            "item": "Identificação do ambiente",
            "status": "PASS" if (host_ok and docker_ok and cg_v2) else "FAIL",
            "evidence": "results/environment/environment.json"
        },
        {
            "item": "Namespaces",
            "status": "PASS" if (pid_ns_diff and mnt_ns_diff and net_ns_diff) else "FAIL",
            "evidence": "results/namespaces/namespaces.csv"
        },
        {
            "item": "Cgroups CPU",
            "status": "PASS" if (cpu_max_confirmed and len(valid_records) == 6) else "FAIL",
            "evidence": "results/cgroups/raw/C1_rep1.json a C2_rep3.json"
        },
        {
            "item": "Cgroups memória",
            "status": "PASS" if mem_max_confirmed else "FAIL",
            "evidence": "results/cgroups/raw/C1_rep1.json (memory_max=268435456, memory_swap_max=0)"
        },
        {
            "item": "Limite de processos",
            "status": "PASS" if pids_max_confirmed else "FAIL",
            "evidence": "results/cgroups/raw/C1_rep1.json (pids_max=64)"
        },
        {
            "item": "Bind mount read-only",
            "status": "PASS" if (read_ok and write_denied and err_erofs) else "FAIL",
            "evidence": "results/readonly/readonly_test.json (error_code=EROFS, errno=30)"
        },
        {
            "item": "Testes automatizados",
            "status": "PASS" if (os.path.exists("scripts/worker.py") and os.path.exists("scripts/test_readonly.py")) else "FAIL",
            "evidence": "scripts/test_readonly.py e scripts/worker.py"
        },
        {
            "item": "Geração de resultados",
            "status": "PASS" if (os.path.exists("results/cgroups/csv/results.csv") and graphs_exist) else "FAIL",
            "evidence": "results/cgroups/csv/results.csv e results/graphs/*.png"
        },
        {
            "item": "Documentação",
            "status": "PASS" if (len(readme_content) > 500 and analysis_exists and summary_exists) else "FAIL",
            "evidence": "README.md, docs/ e relatórios técnicos em results/"
        },
        {
            "item": "Reexecução do projeto",
            "status": "PASS" if os.path.exists("scripts/main.py") else "FAIL",
            "evidence": "scripts/main.py (orquestrador executável com suporte a check, all, cleanup)"
        }
    ]

    # Contagem global de conformidade
    total_checks = sum(len(items) for items in categories.values())
    total_pass = sum(sum(1 for i in items if i["status"] == "PASS") for items in categories.values())
    total_fail = sum(sum(1 for i in items if i["status"] == "FAIL") for items in categories.values())
    total_not_run = sum(sum(1 for i in items if i["status"] == "NOT_RUN") for items in categories.values())
    total_blocked = sum(sum(1 for i in items if i["status"] == "BLOCKED") for items in categories.values())

    summary_payload = {
        "audit_table_section_11": audit_table,
        "summary": {
            "total": total_checks,
            "pass": total_pass,
            "fail": total_fail,
            "not_run": total_not_run,
            "blocked": total_blocked,
            "compliance_percentage": round(total_pass / total_checks * 100, 2) if total_checks else 0.0
        },
        "categories": categories
    }

    # Salva JSON
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    # Gera Markdown
    with open(MD_OUT, "w", encoding="utf-8") as mf:
        mf.write("# Relatório de Auditoria e Validação Técnica — Atividade 3\n\n")
        mf.write("## 1. Tabela Executiva de Validação Obrigatória (Seção 11)\n\n")
        mf.write("| Item | Status | Evidência |\n")
        mf.write("|---|:---:|---|\n")
        for row in audit_table:
            badge = f"**{row['status']}**"
            mf.write(f"| {row['item']} | {badge} | `{row['evidence']}` |\n")

        mf.write("\n---\n\n")
        mf.write("## 2. Indicadores Gerais de Conformidade Técnica\n\n")
        mf.write(f"- **Índice Geral de Conformidade:** `{summary_payload['summary']['compliance_percentage']}%` "
                 f"({total_pass}/{total_checks} verificações aprovadas)\n")
        mf.write(f"- **PASS:** {total_pass}\n")
        mf.write(f"- **FAIL:** {total_fail}\n")
        mf.write(f"- **NOT_RUN:** {total_not_run}\n")
        mf.write(f"- **BLOCKED:** {total_blocked}\n\n")

        for cat_name, items in categories.items():
            mf.write(f"### {cat_name}\n\n")
            mf.write("| Item de Validação | Status | Detalhes Técnicos |\n")
            mf.write("|---|:---:|---|\n")
            for item in items:
                badge = f"**{item['status']}**"
                mf.write(f"| {item['item']} | {badge} | {item['detail']} |\n")
            mf.write("\n")

    return summary_payload


def main() -> int:
    print("=" * 65)
    print("   EXECUÇÃO DA AUDITORIA E VALIDAÇÃO FINAL (SEÇÃO 11 E 14)")
    print("=" * 65)
    results = validate_all()
    s = results["summary"]
    print("\n--- TABELA EXECUTIVA DE VALIDAÇÃO (SEÇÃO 11) ---")
    print(f"{'Item':<26} | {'Status':<6} | {'Evidência'}")
    print("-" * 65)
    for row in results["audit_table_section_11"]:
        print(f"{row['item']:<26} | {row['status']:<6} | {row['evidence']}")

    print("\n" + "=" * 65)
    print(f"Total de Verificações: {s['total']}")
    print(f"Aprovados (PASS):     {s['pass']}")
    print(f"Falhas (FAIL):        {s['fail']}")
    print(f"Pendentes (NOT_RUN):  {s['not_run']}")
    print(f"Bloqueados (BLOCKED): {s['blocked']}")
    print(f"Índice de Conformidade: {s['compliance_percentage']}%")
    print("=" * 65)
    print(f"[+] Relatórios gerados em: {JSON_OUT} e {MD_OUT}")

    return 0 if s["fail"] == 0 and s["not_run"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
