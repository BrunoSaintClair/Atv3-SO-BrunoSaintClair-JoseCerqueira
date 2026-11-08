# Sumário Estatístico das Medições de Cgroups v2

## 1. Tabela das 6 Execuções Oficiais

| Condição | Repetição | Status | Wall Time (s) | CPU Time (s) | Trabalho/s | Throttled (µs) | Checksum |
|---|---|---|---:|---:|---:|---:|---|
| C1 | 1 | success | 13.7155 | 6.8633 | 1,458,207 | 6,834,273 | `0xfeb38a80` |
| C2 | 1 | success | 5.9715 | 5.9654 | 3,349,247 | 2,137 | `0xfeb38a80` |
| C1 | 2 | success | 13.0738 | 6.5209 | 1,529,772 | 6,539,270 | `0xfeb38a80` |
| C2 | 2 | success | 6.5358 | 6.5314 | 3,060,052 | 2,343 | `0xfeb38a80` |
| C1 | 3 | success | 11.3856 | 5.6837 | 1,756,605 | 5,692,836 | `0xfeb38a80` |
| C2 | 3 | success | 6.1143 | 6.1103 | 3,271,014 | 2,566 | `0xfeb38a80` |

## 2. Estatísticas Agregadas por Condição

| Métrica | Condição C1 (0.5 CPU) | Condição C2 (1.0 CPU) |
|---|---:|---:|
| Execuções Válidas | 3/3 | 3/3 |
| Mediana Wall Time | 13.0738 s | 6.1143 s |
| Média Wall Time | 12.7250 s | 6.2072 s |
| Variação (Min - Max) | [11.3856 - 13.7155] s | [5.9715 - 6.5358] s |
| Desvio Padrão Amostral | 1.2035 s | 0.2934 s |
| Mediana Trabalho/s | 1,529,772 op/s | 3,271,014 op/s |
| Mediana CPU Time | 6.5209 s | 6.1103 s |
| Mediana Throttled | 6,539,270 µs | 2,343 µs |

## 3. Comparativo de Desempenho Real

- **Razão de Throughput (C2 / C1):** `2.138x`
- **Razão de Redução de Tempo (C1 / C2):** `2.138x`
- **Razão Teórica da Quota:** `2.000x` (Divergência empírica: `6.9%`)
