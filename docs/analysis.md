# Análise Técnica e Interpretação dos Resultados de Cgroups v2

Este relatório apresenta a discussão detalhada dos resultados quantitativos obtidos no experimento de gerenciamento e restrição de recursos via **Cgroups v2** (Módulo C).

---

## 1. Dados Empíricos Consolidados

A tabela a seguir consolida as métricas observadas nas seis execuções oficiais alternadas (com 20.000.000 de iterações congeladas e carga determinística inteira com checksum invariante `0xfeb38a80`):

| Execução | Condição | Quota Efetiva | Repetição | Wall Time (s) | CPU Time (s) | Trabalho/s (op/s) | Throttled (µs) | nr_throttled | Checksum |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| **C1_rep1** | C1 | 50000 / 100000 | 1 | 13,7155 | 6,8633 | 1.458.207 | 6.834.273 | 137 | `0xfeb38a80` |
| **C2_rep1** | C2 | 100000 / 100000 | 1 | 5,9715 | 5,9654 | 3.349.247 | 2.137 | 1 | `0xfeb38a80` |
| **C1_rep2** | C1 | 50000 / 100000 | 2 | 13,0738 | 6,5209 | 1.529.772 | 6.539.270 | 131 | `0xfeb38a80` |
| **C2_rep2** | C2 | 100000 / 100000 | 2 | 6,5358 | 6,5314 | 3.060.052 | 2.343 | 1 | `0xfeb38a80` |
| **C1_rep3** | C1 | 50000 / 100000 | 3 | 11,3856 | 5,6837 | 1.756.605 | 5.692.836 | 114 | `0xfeb38a80` |
| **C2_rep3** | C2 | 100000 / 100000 | 3 | 6,1143 | 6,1103 | 3.271.014 | 2.566 | 1 | `0xfeb38a80` |

### Tabela Estatística Resumida

| Parâmetro Estatístico | Condição C1 (0,5 CPU Quota) | Condição C2 (1,0 CPU Quota) | Razão Empírica (C2 / C1) |
|---|---:|---:|---:|
| **Mediana Wall Time** | **13,0738 s** | **6,1143 s** | **0,468x** (Redução de 2,138x) |
| **Média Wall Time** | 12,7250 s | 6,2072 s | 0,488x |
| **Desvio Padrão Amostral** | 1,2035 s | 0,2934 s | — |
| **Intervalo [Min - Max]** | [11,3856 - 13,7155] s | [5,9715 - 6,5358] s | — |
| **Mediana Throughput** | **1.529.772 op/s** | **3.271.014 op/s** | **2,138x** |
| **Mediana Throttled (µs)** | **6.539.270 µs** (~6,54 s) | **2.343 µs** (~0,002 s) | **0,00035x** |

---

## 2. Respostas às Questões Obrigatórias da Análise

### 2.1. Qual condição teve maior mediana de trabalho por segundo?
A **Condição C2 (1,0 CPU)** obteve a maior mediana de trabalho concluído por segundo: **3.271.014 operações/segundo**, comparada a **1.529.772 operações/segundo** na Condição C1 (0,5 CPU).

### 2.2. Qual condição apresentou menor wall time?
A **Condição C2** apresentou o menor *wall time* (tempo de relógio transcorrido), registrando mediana de **6,1143 segundos**, enquanto a Condição C1 registrou mediana de **13,0738 segundos**.

### 2.3. Qual foi a diferença observada?
A diferença observada no tempo de relógio foi de **6,9595 segundos** (redução de 53,2% no tempo de execução ao migrar de C1 para C2). Em termos de throughput, a Condição C2 processou **2,138 vezes mais trabalho por segundo** do que a Condição C1.

### 2.4. Como variaram os resultados das três repetições?
- Na **Condição C1**, o *wall time* variou entre 11,3856s e 13,7155s (amplitude de 2,33s, desvio padrão de 1,20s). Essa maior oscilação é característica de processos sujeitos a CFS throttling, pois a cada período de 100ms em que a cota se esgota, o processo é forçado a dormir (*sleep state*), tornando-o mais suscetível a pequenas variações de alinhamento com os ticks do relógio do escalonador.
- Na **Condição C2**, o *wall time* foi extremamente homogêneo, oscilando apenas entre 5,9715s e 6,5358s (amplitude de 0,56s, desvio padrão de 0,29s), refletindo a continuidade de execução na CPU sem bloqueios forçados.

### 2.5. Se houve throttling?
Sim, houve **throttling expressivo e contínuo na Condição C1** e **throttling residual/nulo na Condição C2**:
- Em C1, o contador `throttled_usec_delta` registrou uma mediana de **6.539.270 microssegundos** (aproximadamente 6,54 segundos de suspensão forçada) e uma média de 127 eventos de estrangulamento (`nr_throttled_delta`).
- Em C2, o contador registrou apenas **2.343 microssegundos** (cerca de 2,3 milissegundos) e apenas 1 evento no momento inicial de warm-up.

### 2.6. Como os contadores se relacionam com o tempo de execução?
A relação física é comprovada pela decomposição:
$$\text{Wall Time} \approx \text{CPU Time} + \text{Throttled Time} + \text{Latência de Agendamento do Host}$$

Tomando a mediana de C1:
- $\text{Wall Time} = 13,0738\text{ s}$
- $\text{CPU Time} = 6,5209\text{ s}$
- $\text{Throttled Time} = 6,5393\text{ s}$
- Soma $(\text{CPU} + \text{Throttled}) = 6,5209 + 6,5393 = 13,0602\text{ s}$
A soma do tempo de CPU com o tempo estrangulado pelo cgroup explica **99,9% do tempo real transcorrido**. Os 0,0136s restantes correspondem à latência natural de troca de contexto e despacho do escalonador do Linux.

### 2.7. Se os limites foram confirmados?
Sim. Antes de cada execução, foram inspecionados os nós virtuais do cgroup v2 dentro de cada contêiner:
- Condição C1: `cpu.max` = `50000 100000` (quota de 50.000 µs por período de 100.000 µs, ou seja, 0,5 núcleo lógico).
- Condição C2: `cpu.max` = `100000 100000` (quota de 100.000 µs por período de 100.000 µs, ou seja, 1,0 núcleo lógico).
- Memória máxima: `memory.max` = `268435456` bytes (exatos 256 MiB).
- Limite de swap: `memory.swap.max` = `0` (desabilitando swap adicional).
- Limite de tarefas: `pids.max` = `64`.
Todas as seis execuções validaram e confirmaram esses valores efetivos no kernel.

### 2.8. Quais fatores podem ter influenciado os resultados?
1. **Frequência Dinâmica da CPU (DVFS - Dynamic Voltage and Frequency Scaling):** Em processadores modernos (Intel Core / AMD Ryzen), núcleos sob carga sustentada podem elevar temporariamente o clock (Turbo Boost) ou reduzi-lo sob aquecimento térmico (*thermal throttling*). A execução alternada C1-C2 minimizou o viés cumulativo térmico.
2. **Caches L1/L2/L3 Compartilhados e Troca de Núcleo:** O escalonador do Linux pode migrar a thread do worker entre núcleos lógicos durante as pausas forçadas de throttling de C1, gerando eventuais *cache misses* no retorno.
3. **Ruído em Segundo Plano do Host:** Processos concorrentes do sistema operacional (daemons, interface gráfica, I/O de disco) podem introduzir ruídos no tempo de resposta do escalonador.

### 2.9. Por que o desempenho não precisa apresentar uma relação exatamente proporcional às quotas?
A quota de CPU (`cpu.max`) impõe um **teto superior de alocação de tempo no relógio do agendador**, mas **não é uma garantia de vazão proporcional de instruções**.
Embora a razão teórica de cotas seja $1,0 / 0,5 = 2,00$, a razão empírica obtida foi de **$2,138$** (divergência de 6,9%). As razões para essa não-linearidade incluem:
- **Sobrecarga de Interrupção e Troca de Contexto:** Em C1, o processo foi suspenso e retomado mais de 120 vezes (`nr_throttled`). Cada ciclo de throttling exige que o kernel desassocie a tarefa da fila de prontos (*runqueue*), arme um *timer* de alta resolução (*hrtimer*) para o próximo período e execute uma troca de contexto, incorrendo em penalidades adicionais de latência ausentes em C2.
- **Efeitos de Localidade de Cache:** No contêiner C2, o processo permaneceu executando de forma ininterrupta, preservando linhas quentes de cache nos níveis L1 e L2 do núcleo, potencializando a taxa de instruções por ciclo (IPC).
"""
,Path: