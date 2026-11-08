#!/usr/bin/env python3
"""
Módulo de Consolidação de Resultados e Análise Estatística (Módulo C).
Lê os arquivos JSON brutos das 6 medições oficiais em results/cgroups/raw/,
gera o CSV consolidado em results/cgroups/csv/results.csv e calcula
as estatísticas descritivas (mediana, média, min, max, desvio padrão)
em results/cgroups/summary/statistics.json e summary.md.
"""

import csv
import json
import math
import os
import sys
from typing import Any, Dict, List


RAW_DIR = "results/cgroups/raw"
CSV_PATH = "results/cgroups/csv/results.csv"
SUMMARY_DIR = "results/cgroups/summary"
STATS_JSON_PATH = os.path.join(SUMMARY_DIR, "statistics.json")
SUMMARY_MD_PATH = os.path.join(SUMMARY_DIR, "summary.md")


def calculate_median(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    mid = n // 2
    if n % 2 == 1:
        return sorted_v[mid]
    return (sorted_v[mid - 1] + sorted_v[mid]) / 2.0


def calculate_stddev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def consolidate_results() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    expected_runs = [
        ("C1", 1),
        ("C2", 1),
        ("C1", 2),
        ("C2", 2),
        ("C1", 3),
        ("C2", 3)
    ]

    records = []
    missing_files = []

    for cond, rep in expected_runs:
        fname = f"{cond}_rep{rep}.json"
        fpath = os.path.join(RAW_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                records.append(data)
        else:
            missing_files.append(fname)
            records.append({
                "condition": cond,
                "repetition": rep,
                "iterations": None,
                "checksum": None,
                "status": "missing",
                "wall_time_seconds": None,
                "process_cpu_time_seconds": None,
                "work_per_second": None,
                "cpu": {},
                "memory": {},
                "pids": {}
            })

    # Gravação do CSV
    csv_headers = [
        "condition",
        "repetition",
        "iterations",
        "checksum",
        "status",
        "wall_time_seconds",
        "process_cpu_time_seconds",
        "work_per_second",
        "cpu_max",
        "usage_usec_delta",
        "nr_throttled_delta",
        "throttled_usec_delta",
        "memory_max",
        "memory_current_before",
        "memory_current_after",
        "memory_peak",
        "memory_swap_max",
        "pids_max",
        "pids_current"
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_headers)
        writer.writeheader()
        for r in records:
            cpu = r.get("cpu", {})
            mem = r.get("memory", {})
            pids = r.get("pids", {})
            writer.writerow({
                "condition": r.get("condition"),
                "repetition": r.get("repetition"),
                "iterations": r.get("iterations"),
                "checksum": r.get("checksum"),
                "status": r.get("status"),
                "wall_time_seconds": r.get("wall_time_seconds"),
                "process_cpu_time_seconds": r.get("process_cpu_time_seconds"),
                "work_per_second": r.get("work_per_second"),
                "cpu_max": cpu.get("cpu_max"),
                "usage_usec_delta": cpu.get("usage_usec_delta"),
                "nr_throttled_delta": cpu.get("nr_throttled_delta"),
                "throttled_usec_delta": cpu.get("throttled_usec_delta"),
                "memory_max": mem.get("memory_max"),
                "memory_current_before": mem.get("memory_current_before"),
                "memory_current_after": mem.get("memory_current_after"),
                "memory_peak": mem.get("memory_peak"),
                "memory_swap_max": mem.get("memory_swap_max"),
                "pids_max": pids.get("pids_max"),
                "pids_current": pids.get("pids_current_after", pids.get("pids_current"))
            })

    # Estatísticas por condição
    stats_by_cond: Dict[str, Any] = {}
    for target_cond in ["C1", "C2"]:
        cond_records = [r for r in records if r["condition"] == target_cond]
        valid_records = [r for r in cond_records if r.get("status") == "success"]
        failures = len(cond_records) - len(valid_records)

        wall_times = [r["wall_time_seconds"] for r in valid_records if r.get("wall_time_seconds") is not None]
        cpu_times = [r["process_cpu_time_seconds"] for r in valid_records if r.get("process_cpu_time_seconds") is not None]
        work_rates = [r["work_per_second"] for r in valid_records if r.get("work_per_second") is not None]
        throttled_usecs = [
            r["cpu"]["throttled_usec_delta"] for r in valid_records
            if r.get("cpu", {}).get("throttled_usec_delta") is not None
        ]
        nr_throttled = [
            r["cpu"]["nr_throttled_delta"] for r in valid_records
            if r.get("cpu", {}).get("nr_throttled_delta") is not None
        ]

        stats_by_cond[target_cond] = {
            "total_attempts": len(cond_records),
            "valid_runs": len(valid_records),
            "failed_runs": failures,
            "wall_time": {
                "median": round(calculate_median(wall_times), 4),
                "mean": round(sum(wall_times) / len(wall_times), 4) if wall_times else 0.0,
                "min": round(min(wall_times), 4) if wall_times else 0.0,
                "max": round(max(wall_times), 4) if wall_times else 0.0,
                "stddev": round(calculate_stddev(wall_times), 4),
                "raw_values": [round(x, 4) for x in wall_times]
            },
            "cpu_time": {
                "median": round(calculate_median(cpu_times), 4),
                "mean": round(sum(cpu_times) / len(cpu_times), 4) if cpu_times else 0.0,
                "min": round(min(cpu_times), 4) if cpu_times else 0.0,
                "max": round(max(cpu_times), 4) if cpu_times else 0.0,
                "raw_values": [round(x, 4) for x in cpu_times]
            },
            "work_per_second": {
                "median": round(calculate_median(work_rates), 2),
                "mean": round(sum(work_rates) / len(work_rates), 2) if work_rates else 0.0,
                "min": round(min(work_rates), 2) if work_rates else 0.0,
                "max": round(max(work_rates), 2) if work_rates else 0.0,
                "raw_values": [round(x, 2) for x in work_rates]
            },
            "throttling": {
                "median_throttled_usec": round(calculate_median(throttled_usecs), 0),
                "mean_throttled_usec": round(sum(throttled_usecs) / len(throttled_usecs), 0) if throttled_usecs else 0,
                "median_nr_throttled": round(calculate_median(nr_throttled), 0),
                "raw_throttled_usec": throttled_usecs
            }
        }

    # Razões de comparação entre C2 e C1
    c1_stat = stats_by_cond.get("C1", {})
    c2_stat = stats_by_cond.get("C2", {})
    c1_median_wps = c1_stat.get("work_per_second", {}).get("median", 0.0)
    c2_median_wps = c2_stat.get("work_per_second", {}).get("median", 0.0)
    c1_median_wt = c1_stat.get("wall_time", {}).get("median", 0.0)
    c2_median_wt = c2_stat.get("wall_time", {}).get("median", 0.0)

    speedup_ratio = round(c1_median_wt / c2_median_wt, 3) if c2_median_wt > 0 else 0.0
    throughput_ratio = round(c2_median_wps / c1_median_wps, 3) if c1_median_wps > 0 else 0.0

    comparison_summary = {
        "speedup_ratio_wall_time (C1/C2)": speedup_ratio,
        "throughput_ratio_work_per_sec (C2/C1)": throughput_ratio,
        "theoretical_quota_ratio": 2.0,
        "divergence_from_theoretical_percentage": round(abs(throughput_ratio - 2.0) / 2.0 * 100, 2)
    }

    full_stats = {
        "conditions": stats_by_cond,
        "comparison": comparison_summary,
        "records": records
    }

    with open(STATS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(full_stats, f, indent=2)

    # Geração do sumário Markdown
    with open(SUMMARY_MD_PATH, "w", encoding="utf-8") as mf:
        mf.write("# Sumário Estatístico das Medições de Cgroups v2\n\n")
        mf.write("## 1. Tabela das 6 Execuções Oficiais\n\n")
        mf.write("| Condição | Repetição | Status | Wall Time (s) | CPU Time (s) | Trabalho/s | Throttled (µs) | Checksum |\n")
        mf.write("|---|---|---|---:|---:|---:|---:|---|\n")
        for r in records:
            c = r.get("cpu", {})
            wt = f"{r['wall_time_seconds']:.4f}" if r.get('wall_time_seconds') else "N/A"
            ct = f"{r['process_cpu_time_seconds']:.4f}" if r.get('process_cpu_time_seconds') else "N/A"
            wps = f"{r['work_per_second']:,.0f}" if r.get('work_per_second') else "N/A"
            thr = f"{c.get('throttled_usec_delta', 'N/A'):,}" if isinstance(c.get('throttled_usec_delta'), (int, float)) else "N/A"
            mf.write(f"| {r['condition']} | {r['repetition']} | {r['status']} | {wt} | {ct} | {wps} | {thr} | `{r['checksum']}` |\n")

        mf.write("\n## 2. Estatísticas Agregadas por Condição\n\n")
        mf.write("| Métrica | Condição C1 (0.5 CPU) | Condição C2 (1.0 CPU) |\n")
        mf.write("|---|---:|---:|\n")
        mf.write(f"| Execuções Válidas | {c1_stat['valid_runs']}/{c1_stat['total_attempts']} | {c2_stat['valid_runs']}/{c2_stat['total_attempts']} |\n")
        mf.write(f"| Mediana Wall Time | {c1_stat['wall_time']['median']:.4f} s | {c2_stat['wall_time']['median']:.4f} s |\n")
        mf.write(f"| Média Wall Time | {c1_stat['wall_time']['mean']:.4f} s | {c2_stat['wall_time']['mean']:.4f} s |\n")
        mf.write(f"| Variação (Min - Max) | [{c1_stat['wall_time']['min']:.4f} - {c1_stat['wall_time']['max']:.4f}] s | [{c2_stat['wall_time']['min']:.4f} - {c2_stat['wall_time']['max']:.4f}] s |\n")
        mf.write(f"| Desvio Padrão Amostral | {c1_stat['wall_time']['stddev']:.4f} s | {c2_stat['wall_time']['stddev']:.4f} s |\n")
        mf.write(f"| Mediana Trabalho/s | {c1_stat['work_per_second']['median']:,.0f} op/s | {c2_stat['work_per_second']['median']:,.0f} op/s |\n")
        mf.write(f"| Mediana CPU Time | {c1_stat['cpu_time']['median']:.4f} s | {c2_stat['cpu_time']['median']:.4f} s |\n")
        mf.write(f"| Mediana Throttled | {c1_stat['throttling']['median_throttled_usec']:,.0f} µs | {c2_stat['throttling']['median_throttled_usec']:,.0f} µs |\n\n")

        mf.write("## 3. Comparativo de Desempenho Real\n\n")
        mf.write(f"- **Razão de Throughput (C2 / C1):** `{throughput_ratio:.3f}x`\n")
        mf.write(f"- **Razão de Redução de Tempo (C1 / C2):** `{speedup_ratio:.3f}x`\n")
        mf.write(f"- **Razão Teórica da Quota:** `2.000x` (Divergência empírica: `{comparison_summary['divergence_from_theoretical_percentage']}%`)\n")

    print(f"[+] CSV consolidado salvo em: {CSV_PATH}")
    print(f"[+] Estatísticas salvas em: {STATS_JSON_PATH} e {SUMMARY_MD_PATH}")
    return full_stats


def main() -> int:
    consolidate_results()
    return 0


if __name__ == "__main__":
    sys.exit(main())
