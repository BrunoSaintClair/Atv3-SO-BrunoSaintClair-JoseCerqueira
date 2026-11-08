#!/usr/bin/env python3
"""
Módulo de Execução Experimental de Cgroups v2 (Módulo C).
Aplica limites de CPU (quota), memória e tarefas via Docker e cgroups v2.
Suporta execução do teste piloto e das 6 execuções oficiais alternadas (C1 e C2).
Coleta, valida e preserva integralmente os dados brutos e logs.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple


CONFIG_FILE = "config/experiment.json"
RAW_DIR = "results/cgroups/raw"
LOGS_DIR = os.path.join(RAW_DIR, "logs")


def load_config() -> Dict[str, Any]:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def run_cmd(cmd: List[str], timeout_sec: Optional[int] = None) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Execução interrompida por TIMEOUT ({timeout_sec}s atingido)."
    except Exception as e:
        return 1, "", str(e)


def run_single_measurement(
    condition: str,
    repetition: int,
    iterations: int,
    config: Dict[str, Any],
    is_pilot: bool = False
) -> Dict[str, Any]:
    """Executa uma medição em um contêiner independente com limites cgroups v2 rigorosos."""
    cond_cfg = config["conditions"][condition]
    cpu_quota = cond_cfg["cpu_quota"]
    cpu_period = config["cpu_period"]
    memory_limit = config["memory_limit"]
    memory_swap = config["memory_swap"]
    pids_limit = config["pids_limit"]
    max_timeout = config.get("max_execution_seconds", 90)
    image_tag = config.get("custom_image_tag", "so-atividade3:latest")

    run_tag = f"{condition}_pilot" if is_pilot else f"{condition}_rep{repetition}"
    container_name = f"so-atividade3-cg-{run_tag.lower()}"

    # Assegurar limpeza de contêiner prévio caso tenha permanecido
    run_cmd(["docker", "rm", "-f", container_name])

    start_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t_start = time.perf_counter()

    docker_run_cmd = [
        "docker", "run",
        "--name", container_name,
        "--label", "project=so-atividade3",
        "--label", f"condition={condition}",
        "--label", f"repetition={repetition}",
        "--network", "none",
        f"--cpu-period={cpu_period}",
        f"--cpu-quota={cpu_quota}",
        f"--memory={memory_limit}",
        f"--memory-swap={memory_swap}",
        f"--pids-limit={pids_limit}",
        image_tag,
        "python", "/app/worker.py",
        "--condition", condition,
        "--repetition", str(repetition),
        "--iterations", str(iterations)
    ]

    print(f"[*] Executando [{run_tag}]: quota={cpu_quota}/{cpu_period} ({cond_cfg['cpus']} CPU), iter={iterations}...")
    code, stdout, stderr = run_cmd(docker_run_cmd, timeout_sec=max_timeout)
    t_end = time.perf_counter()
    end_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    total_elapsed = t_end - t_start

    # Inspeciona estado final do contêiner (ex: OOMKilled, ExitCode)
    inspect_code, inspect_json_str, _ = run_cmd(["docker", "inspect", container_name])
    oom_killed = False
    container_exit_code = code
    if inspect_code == 0:
        try:
            inspect_data = json.loads(inspect_json_str)[0]
            oom_killed = inspect_data.get("State", {}).get("OOMKilled", False)
            container_exit_code = inspect_data.get("State", {}).get("ExitCode", code)
        except Exception:
            pass

    # Remoção do contêiner
    run_cmd(["docker", "rm", "-f", container_name])

    # Gravação do log de execução
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file_path = os.path.join(LOGS_DIR, f"{run_tag}.log")
    with open(log_file_path, "w", encoding="utf-8") as lf:
        lf.write(f"=== EXECUÇÃO: {run_tag} ===\n")
        lf.write(f"Início: {start_time_iso}\n")
        lf.write(f"Término: {end_time_iso}\n")
        lf.write(f"Duração Total Observada: {total_elapsed:.4f}s\n")
        lf.write(f"Código de Saída: {code} (Container ExitCode: {container_exit_code})\n")
        lf.write(f"OOMKilled: {oom_killed}\n")
        lf.write(f"Comando Docker: {' '.join(docker_run_cmd)}\n\n")
        lf.write("--- STDOUT ---\n")
        lf.write(stdout + "\n\n")
        lf.write("--- STDERR ---\n")
        lf.write(stderr + "\n")

    # Parsing do resultado JSON emitido pelo worker.py
    parsed_worker_data = None
    parse_error = None
    if stdout:
        try:
            parsed_worker_data = json.loads(stdout)
        except json.JSONDecodeError as je:
            parse_error = f"Erro de decodificação JSON do worker: {je}"

    # Validação rigorosa dos limites de Cgroup esperados
    expected_cpu_max = f"{cpu_quota} {cpu_period}"
    expected_mem_max = 256 * 1024 * 1024
    expected_pids_max = pids_limit

    validation_errors = []
    if code != 0:
        validation_errors.append(f"Código de encerramento não nulo ({code}). Stderr: {stderr}")
    if oom_killed:
        validation_errors.append("Contêiner foi encerrado por OOM (Out Of Memory).")
    if parse_error:
        validation_errors.append(parse_error)

    if parsed_worker_data:
        actual_cpu_max = parsed_worker_data.get("cpu", {}).get("cpu_max")
        actual_mem_max = parsed_worker_data.get("memory", {}).get("memory_max")
        actual_pids_max = parsed_worker_data.get("pids", {}).get("pids_max")

        if actual_cpu_max != expected_cpu_max:
            validation_errors.append(f"cpu.max divergente! Esperado '{expected_cpu_max}', obtido '{actual_cpu_max}'")
        if actual_mem_max != expected_mem_max:
            validation_errors.append(f"memory.max divergente! Esperado {expected_mem_max}, obtido {actual_mem_max}")
        if actual_pids_max != expected_pids_max:
            validation_errors.append(f"pids.max divergente! Esperado {expected_pids_max}, obtido {actual_pids_max}")

    status = "success" if (not validation_errors and parsed_worker_data) else "failure"

    execution_record: Dict[str, Any] = {
        "condition": condition,
        "repetition": repetition,
        "is_pilot": is_pilot,
        "run_tag": run_tag,
        "container_name": container_name,
        "start_time_utc": start_time_iso,
        "end_time_utc": end_time_iso,
        "total_elapsed_seconds": round(total_elapsed, 6),
        "exit_code": code,
        "oom_killed": oom_killed,
        "status": status,
        "validation_errors": validation_errors,
        "iterations": iterations,
        "checksum": parsed_worker_data.get("checksum") if parsed_worker_data else None,
        "wall_time_seconds": parsed_worker_data.get("wall_time_seconds") if parsed_worker_data else round(total_elapsed, 6),
        "process_cpu_time_seconds": parsed_worker_data.get("process_cpu_time_seconds") if parsed_worker_data else None,
        "work_per_second": parsed_worker_data.get("work_per_second") if parsed_worker_data else None,
        "cpu": parsed_worker_data.get("cpu") if parsed_worker_data else {
            "cpu_max": f"{cpu_quota} {cpu_period}",
            "usage_usec_delta": None,
            "nr_throttled_delta": None,
            "throttled_usec_delta": None
        },
        "memory": parsed_worker_data.get("memory") if parsed_worker_data else {
            "memory_max": expected_mem_max,
            "memory_current_before": None,
            "memory_current_after": None,
            "memory_peak": None,
            "memory_swap_max": 0
        },
        "pids": parsed_worker_data.get("pids") if parsed_worker_data else {
            "pids_max": expected_pids_max,
            "pids_current": None
        },
        "log_file": log_file_path
    }

    # Salva o arquivo JSON da execução individual
    json_filename = f"{run_tag}.json"
    json_path = os.path.join(RAW_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(execution_record, jf, indent=2)

    print(f"[{status.upper()}] {run_tag}: wall_time={execution_record['wall_time_seconds']}s, "
          f"checksum={execution_record['checksum']}, "
          f"throttled_usec={execution_record['cpu'].get('throttled_usec_delta')}")
    if validation_errors:
        for err in validation_errors:
            print(f"    ! Erro de validação: {err}", file=sys.stderr)

    return execution_record


def run_pilot(config: Dict[str, Any]) -> int:
    print("=" * 60)
    print("      EXECUÇÃO DO TESTE PILOTO (PARTE C)")
    print("=" * 60)
    initial_iterations = config.get("initial_iterations", 20000000)
    print(f"[*] Testando condição C1 (0.5 CPU) com {initial_iterations:,} iterações...")

    pilot_record = run_single_measurement("C1", 0, initial_iterations, config, is_pilot=True)
    wall_t = pilot_record["wall_time_seconds"]

    print("\n--- AVALIAÇÃO DO PILOTO ---")
    print(f"Tempo transcorrido no C1: {wall_t:.2f} segundos.")

    # Critério de proteção operacional: deve terminar confortavelmente entre 4s e 60s (limite de 90s)
    if wall_t > 80:
        print("[!] Tempo de execução muito próximo ao limite máximo de 90s. Ajustando iterações...", file=sys.stderr)
        adjusted_iterations = int(initial_iterations * (15.0 / wall_t))
        justification = (
            f"Iterações ajustadas de {initial_iterations} para {adjusted_iterations} "
            f"porque o tempo piloto ({wall_t:.2f}s) ultrapassou a margem de segurança de 80s."
        )
    elif wall_t < 1.0:
        print("[!] Tempo muito curto para gerar contagem consistente de throttling. Ajustando iterações...", file=sys.stderr)
        adjusted_iterations = int(initial_iterations * (10.0 / max(wall_t, 0.1)))
        justification = (
            f"Iterações aumentadas de {initial_iterations} para {adjusted_iterations} "
            f"para obter janela temporal suficiente de amostragem de CFS throttling."
        )
    else:
        adjusted_iterations = initial_iterations
        justification = (
            f"Quantidade de {initial_iterations:,} iterações confirmada e congelada. "
            f"O tempo de execução ({wall_t:.2f}s em C1) é perfeitamente adequado: "
            f"longo o bastante para produzir amostragem consistente de CFS throttling (milhares de microssegundos) "
            f"e muito abaixo do teto de proteção operacional de 90 segundos."
        )

    # Congelamento no experiment.json
    config["frozen_iterations"] = adjusted_iterations
    config["pilot_justification"] = justification
    config["pilot_date_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    config["pilot_wall_time_seconds"] = wall_t
    config["pilot_checksum"] = pilot_record.get("checksum")
    save_config(config)

    # Gravar arquivo dedicado do piloto
    pilot_summary_path = os.path.join(RAW_DIR, "pilot_summary.json")
    with open(pilot_summary_path, "w", encoding="utf-8") as pf:
        json.dump({
            "pilot_record": pilot_record,
            "frozen_iterations": adjusted_iterations,
            "justification": justification
        }, pf, indent=2)

    print(f"[+] Decisão do Piloto:")
    print(f"    - Iterações Congeladas: {adjusted_iterations:,}")
    print(f"    - Justificativa: {justification}")
    print(f"    - Configuração atualizada e congelada em: {CONFIG_FILE}")
    print("=" * 60)
    return 0 if pilot_record["status"] == "success" else 1


def run_official_measurements(config: Dict[str, Any]) -> int:
    print("=" * 60)
    print("   EXECUÇÃO DAS 6 MEDIÇÕES OFICIAIS DE CGROUPS (C1 e C2)")
    print("=" * 60)

    frozen_iterations = config.get("frozen_iterations")
    if not frozen_iterations:
        print("[ERRO] Teste piloto não foi executado ou iterações não foram congeladas!", file=sys.stderr)
        print("Execute primeiro: python scripts/main.py pilot", file=sys.stderr)
        return 1

    print(f"[*] Iterações congeladas: {frozen_iterations:,}")
    print("[*] Sequência alternada obrigatória: C1_rep1, C2_rep1, C1_rep2, C2_rep2, C1_rep3, C2_rep3")

    execution_plan = [
        ("C1", 1),
        ("C2", 1),
        ("C1", 2),
        ("C2", 2),
        ("C1", 3),
        ("C2", 3),
    ]

    results = []
    checksums = set()
    all_success = True

    for idx, (cond, rep) in enumerate(execution_plan, 1):
        print(f"\n[{idx}/6] Iniciando medição oficial {cond} - Repetição {rep}...")
        res = run_single_measurement(cond, rep, frozen_iterations, config, is_pilot=False)
        results.append(res)
        if res["status"] != "success":
            all_success = False
        if res.get("checksum"):
            checksums.add(res["checksum"])

    print("\n" + "=" * 60)
    print("            RESUMO DAS 6 MEDIÇÕES OFICIAIS")
    print("=" * 60)
    print(f"{'Execução':<10} | {'Status':<8} | {'Wall Time (s)':<14} | {'CPU Time (s)':<14} | {'Throttled (µs)':<14} | {'Checksum'}")
    print("-" * 82)
    for r in results:
        wt = f"{r['wall_time_seconds']:.4f}" if r.get('wall_time_seconds') else "N/A"
        ct = f"{r['process_cpu_time_seconds']:.4f}" if r.get('process_cpu_time_seconds') else "N/A"
        thr = str(r['cpu'].get('throttled_usec_delta', 'N/A'))
        print(f"{r['run_tag']:<10} | {r['status'].upper():<8} | {wt:<14} | {ct:<14} | {thr:<14} | {r['checksum']}")
    print("=" * 60)

    # Verificação de integridade de checksums
    if len(checksums) == 1:
        print(f"[SUCESSO] Integridade matemática confirmada! Checksum determinístico idêntico em todas as 6 execuções: {list(checksums)[0]}")
    else:
        print(f"[ERRO CRÍTICO] Checksums divergentes detectados entre as execuções: {checksums}", file=sys.stderr)
        all_success = False

    return 0 if all_success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestrador de Experimentos de Cgroups v2")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pilot", action="store_true", help="Executa o teste piloto para calibrar e congelar iterações")
    group.add_argument("--run-all", action="store_true", help="Executa as 6 medições oficiais alternadas")
    args = parser.parse_args()

    config = load_config()
    if args.pilot:
        return run_pilot(config)
    elif args.run_all:
        return run_official_measurements(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
