#!/usr/bin/env python3
"""
Módulo de Geração de Gráficos Técnicos (Módulo C).
Lê os dados reais consolidados de results/cgroups/csv/results.csv
e gera gráficos profissionais em results/graphs/:
1. work_per_second.png: Throughput mediano (iterações/s) com barras de dispersão e anotações.
2. wall_time_comparison.png: Comparação temporal direta por repetição (C1 vs C2).
"""

import csv
import os
import sys

# Auto-detecção de ambiente virtual para garantir acesso ao matplotlib
try:
    import matplotlib
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    venv_python = os.path.abspath(".venv/bin/python3")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        import subprocess
        result = subprocess.run([venv_python] + sys.argv)
        sys.exit(result.returncode)
    else:
        sys.stderr.write("Erro: biblioteca 'matplotlib' não encontrada. Instale-a via requirements.txt\n")
        sys.exit(1)


CSV_PATH = "results/cgroups/csv/results.csv"
OUTPUT_DIR = "results/graphs"


def load_csv_data():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {CSV_PATH}")

    c1_records = []
    c2_records = []

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] != "success":
                continue
            item = {
                "repetition": int(row["repetition"]),
                "wall_time": float(row["wall_time_seconds"]),
                "cpu_time": float(row["process_cpu_time_seconds"]),
                "work_per_sec": float(row["work_per_second"]),
                "throttled_usec": float(row["throttled_usec_delta"]) if row["throttled_usec_delta"] else 0.0
            }
            if row["condition"] == "C1":
                c1_records.append(item)
            elif row["condition"] == "C2":
                c2_records.append(item)

    c1_records.sort(key=lambda x: x["repetition"])
    c2_records.sort(key=lambda x: x["repetition"])
    return c1_records, c2_records


def generate_graphs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    c1_data, c2_data = load_csv_data()

    if len(c1_data) < 3 or len(c2_data) < 3:
        sys.stderr.write("Aviso: dados insuficientes no CSV (mínimo de 3 repetições válidas por condição).\n")
        sys.exit(1)

    matplotlib.use("Agg")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # Gráfico 1: Trabalho Concluído por Segundo (Mediana + Dispersão)
    # -------------------------------------------------------------
    c1_wps = [d["work_per_sec"] for d in c1_data]
    c2_wps = [d["work_per_sec"] for d in c2_data]

    c1_median = sorted(c1_wps)[len(c1_wps) // 2]
    c2_median = sorted(c2_wps)[len(c2_wps) // 2]

    c1_err_low = c1_median - min(c1_wps)
    c1_err_high = max(c1_wps) - c1_median
    c2_err_low = c2_median - min(c2_wps)
    c2_err_high = max(c2_wps) - c2_median

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    conditions = ["C1 (0.5 CPU Quota)", "C2 (1.0 CPU Quota)"]
    medians = [c1_median, c2_median]
    errors = [[c1_err_low, c2_err_low], [c1_err_high, c2_err_high]]
    colors = ["#3498db", "#2ecc71"]

    bars = ax.bar(conditions, medians, yerr=errors, capsize=8, color=colors, width=0.52, edgecolor="#2c3e50", linewidth=1.2)

    for bar, val in zip(bars, medians):
        height = bar.get_height()
        ax.annotate(f"{val:,.0f} op/s\n(Mediana de 3 repetições)",
                    xy=(bar.get_x() + bar.get_width() / 2, height / 2),
                    xytext=(0, 0), textcoords="offset points",
                    ha='center', va='center',
                    fontsize=11, fontweight='bold', color='white',
                    bbox=dict(boxstyle="round,pad=0.3", fc="#2c3e50", alpha=0.85))

    speedup = c2_median / c1_median
    ax.set_title("Gráfico 1 — Taxa de Processamento (Trabalho/Segundo)\nCgroups v2: Condição C1 (0.5 CPU) vs C2 (1.0 CPU)",
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_ylabel("Throughput Computacional (Iterações / Segundo)", fontsize=11, labelpad=10)
    ax.set_xlabel(f"Condição Experimental (N = 3 repetições válidas cada | Razão observada: {speedup:.2f}x)",
                  fontsize=11, labelpad=10)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    graph1_path = os.path.join(OUTPUT_DIR, "work_per_second.png")
    fig.tight_layout()
    fig.savefig(graph1_path)
    plt.close(fig)
    print(f"[+] Gráfico 1 gerado: {graph1_path}")

    # -------------------------------------------------------------
    # Gráfico 2: Wall Time por Repetição (C1 vs C2)
    # -------------------------------------------------------------
    reps = [d["repetition"] for d in c1_data]
    c1_wall = [d["wall_time"] for d in c1_data]
    c2_wall = [d["wall_time"] for d in c2_data]

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    width = 0.35
    x = [r for r in reps]
    x_c1 = [i - width/2 for i in x]
    x_c2 = [i + width/2 for i in x]

    rects1 = ax.bar(x_c1, c1_wall, width, label='C1 (0.5 CPU)', color='#3498db', edgecolor='#1a5276', linewidth=1.2)
    rects2 = ax.bar(x_c2, c2_wall, width, label='C2 (1.0 CPU)', color='#2ecc71', edgecolor='#196f3d', linewidth=1.2)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f'{h:.2f}s',
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f'{h:.2f}s',
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_title("Gráfico 2 — Tempo Real Transcorrido (Wall Time) por Repetição\nComparação entre Limites de Quota de CPU",
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Número da Repetição Oficial", fontsize=11, labelpad=10)
    ax.set_ylabel("Tempo de Execução (Segundos)", fontsize=11, labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Repetição {r}" for r in reps], fontsize=10)
    ax.legend(loc="upper right", frameon=True, fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_ylim(0, max(c1_wall) * 1.18)

    graph2_path = os.path.join(OUTPUT_DIR, "wall_time_comparison.png")
    fig.tight_layout()
    fig.savefig(graph2_path)
    plt.close(fig)
    print(f"[+] Gráfico 2 gerado: {graph2_path}")


def main() -> int:
    generate_graphs()
    return 0


if __name__ == "__main__":
    sys.exit(main())
