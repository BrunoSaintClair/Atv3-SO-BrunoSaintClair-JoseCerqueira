#!/usr/bin/env python3
"""
Worker determinístico para avaliação quantitativa de cgroups v2.
Executa uma carga puramente computacional em CPU e coleta métricas precisas
de tempo de execução (wall time e CPU time), memória (RSS e cgroup) e
contadores do escalonador de CPU (cgroup v2 cpu.stat).
"""

import argparse
import errno
import json
import os
import sys
import time
from typing import Any, Dict


def read_file_safe(path: str) -> str:
    """Lê um arquivo do sistema (/sys ou /proc) retornando string vazia em caso de ausência."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def read_kv_file(path: str) -> Dict[str, int]:
    """Lê arquivos chave-valor de cgroups v2 como cpu.stat."""
    content = read_file_safe(path)
    data: Dict[str, int] = {}
    if not content:
        return data
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            try:
                data[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return data


def get_proc_status_memory() -> Dict[str, Any]:
    """Coleta métricas de memória do processo a partir de /proc/self/status."""
    status_content = read_file_safe("/proc/self/status")
    result: Dict[str, Any] = {"vm_rss_kb": None, "vm_hwm_kb": None}
    if not status_content:
        return result
    for line in status_content.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    result["vm_rss_kb"] = int(parts[1])
                except ValueError:
                    pass
        elif line.startswith("VmHWM:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    result["vm_hwm_kb"] = int(parts[1])
                except ValueError:
                    pass
    return result


def collect_cgroup_snapshot() -> Dict[str, Any]:
    """Coleta snapshot do estado dos controladores de cgroup v2."""
    cgroup_dir = "/sys/fs/cgroup"
    cpu_stat = read_kv_file(f"{cgroup_dir}/cpu.stat")
    
    mem_curr = read_file_safe(f"{cgroup_dir}/memory.current")
    mem_peak = read_file_safe(f"{cgroup_dir}/memory.peak")
    mem_swap_curr = read_file_safe(f"{cgroup_dir}/memory.swap.current")
    pids_curr = read_file_safe(f"{cgroup_dir}/pids.current")
    
    return {
        "cpu_stat": cpu_stat,
        "memory_current": int(mem_curr) if mem_curr.isdigit() else None,
        "memory_peak": int(mem_peak) if mem_peak.isdigit() else None,
        "memory_swap_current": int(mem_swap_curr) if mem_swap_curr.isdigit() else None,
        "pids_current": int(pids_curr) if pids_curr.isdigit() else None,
    }


def workload(iterations: int) -> int:
    """
    Carga de trabalho matemática determinística inteira.
    Baseada em gerador linear congruente de 32 bits.
    """
    val = 0
    for i in range(iterations):
        val = (val * 1664525 + 1013904223 + i) & 0xFFFFFFFF
    return val


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker determinístico de CPU para testes de Cgroups")
    parser.add_argument("--condition", type=str, default="UNKNOWN", help="Identificador da condição (ex: C1 ou C2)")
    parser.add_argument("--repetition", type=int, default=1, help="Número da repetição")
    parser.add_argument("--iterations", type=int, required=True, help="Número de iterações do loop matemático")
    parser.add_argument("--output", type=str, default="", help="Caminho para salvar o JSON resultante (opcional)")
    args = parser.parse_args()

    # Leitura dos limites estáticos configurados no cgroup v2
    cgroup_dir = "/sys/fs/cgroup"
    cpu_max = read_file_safe(f"{cgroup_dir}/cpu.max")
    mem_max = read_file_safe(f"{cgroup_dir}/memory.max")
    mem_swap_max = read_file_safe(f"{cgroup_dir}/memory.swap.max")
    pids_max = read_file_safe(f"{cgroup_dir}/pids.max")

    proc_mem_before = get_proc_status_memory()
    cgroup_before = collect_cgroup_snapshot()

    # Início da medição de tempos de alta precisão
    start_wall = time.perf_counter()
    start_cpu = time.process_time()

    # Execução da carga determinística
    checksum_val = workload(args.iterations)

    # Fim da medição
    end_cpu = time.process_time()
    end_wall = time.perf_counter()

    cgroup_after = collect_cgroup_snapshot()
    proc_mem_after = get_proc_status_memory()

    wall_time_seconds = end_wall - start_wall
    process_cpu_time_seconds = end_cpu - start_cpu
    work_per_second = (args.iterations / wall_time_seconds) if wall_time_seconds > 0 else 0.0
    checksum_str = f"0x{checksum_val:08x}"

    # Cálculo dos deltas de cpu.stat
    cpu_before = cgroup_before["cpu_stat"]
    cpu_after = cgroup_after["cpu_stat"]

    usage_usec_delta = cpu_after.get("usage_usec", 0) - cpu_before.get("usage_usec", 0)
    nr_throttled_delta = cpu_after.get("nr_throttled", 0) - cpu_before.get("nr_throttled", 0)
    throttled_usec_delta = cpu_after.get("throttled_usec", 0) - cpu_before.get("throttled_usec", 0)
    nr_periods_delta = cpu_after.get("nr_periods", 0) - cpu_before.get("nr_periods", 0)

    result_payload: Dict[str, Any] = {
        "condition": args.condition,
        "repetition": args.repetition,
        "iterations": args.iterations,
        "checksum": checksum_str,
        "status": "success",
        "wall_time_seconds": round(wall_time_seconds, 6),
        "process_cpu_time_seconds": round(process_cpu_time_seconds, 6),
        "work_per_second": round(work_per_second, 2),
        "cpu": {
            "cpu_max": cpu_max,
            "usage_usec_before": cpu_before.get("usage_usec"),
            "usage_usec_after": cpu_after.get("usage_usec"),
            "usage_usec_delta": usage_usec_delta,
            "nr_periods_delta": nr_periods_delta,
            "nr_throttled_before": cpu_before.get("nr_throttled"),
            "nr_throttled_after": cpu_after.get("nr_throttled"),
            "nr_throttled_delta": nr_throttled_delta,
            "throttled_usec_before": cpu_before.get("throttled_usec"),
            "throttled_usec_after": cpu_after.get("throttled_usec"),
            "throttled_usec_delta": throttled_usec_delta,
        },
        "memory": {
            "memory_max": int(mem_max) if mem_max.isdigit() else mem_max,
            "memory_current_before": cgroup_before["memory_current"],
            "memory_current_after": cgroup_after["memory_current"],
            "memory_peak": cgroup_after["memory_peak"],
            "memory_swap_max": int(mem_swap_max) if mem_swap_max.isdigit() else mem_swap_max,
            "vm_rss_kb": proc_mem_after.get("vm_rss_kb"),
            "vm_hwm_kb": proc_mem_after.get("vm_hwm_kb"),
        },
        "pids": {
            "pids_max": int(pids_max) if pids_max.isdigit() else pids_max,
            "pids_current_before": cgroup_before["pids_current"],
            "pids_current_after": cgroup_after["pids_current"],
        },
    }

    output_json = json.dumps(result_payload, indent=2)
    print(output_json)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as out_f:
                out_f.write(output_json)
        except OSError as e:
            sys.stderr.write(f"Erro ao salvar arquivo de saída {args.output}: {e}\n")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
