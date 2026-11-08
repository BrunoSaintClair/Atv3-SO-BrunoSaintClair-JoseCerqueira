# Sistemas Operacionais — Atividade 3
## Virtualização Leve, Contêineres, Namespaces e Cgroups v2

Este repositório contém a solução completa, automatizada e reproduzível para os experimentos práticos da **Atividade 3 de Sistemas Operacionais** (DCOMP / UFS), desenvolvida por **Bruno Saint Clair** e **Jose Cerqueira**.

A solução foi desenvolvida **do zero**, sem utilização de kits de apoio da disciplina, garantindo que 100% dos dados apresentados advenham de execuções reais em ambiente Linux nativo (*bare-metal*).

---

## Sumário

1. [Objetivos do Projeto](#1-objetivos-do-projeto)
2. [Identificação da Equipe](#2-identificação-da-equipe)
3. [Pré-requisitos e Ambiente Suportado](#3-pré-requisitos-e-ambiente-suportado)
4. [Estrutura do Repositório](#4-estrutura-do-repositório)
5. [Instalação Rápida](#5-instalação-rápida)
6. [Guia de Execução Passo a Passo](#6-guia-de-execução-passo-a-passo)
   - [6.1. Verificação do Ambiente (`check`)](#61-verificação-do-ambiente-check)
   - [6.2. Documentação da Infraestrutura (`environment`)](#62-documentação-da-infraestrutura-environment)
   - [6.3. Experimento de Namespaces (`namespaces`)](#63-experimento-de-namespaces-namespaces)
   - [6.4. Teste Piloto e Congelamento (`pilot`)](#64-teste-piloto-e-congelamento-pilot)
   - [6.5. Medições Oficiais de Cgroups (`cgroups`)](#65-medições-oficiais-de-cgroups-cgroups)
   - [6.6. Montagem Somente Leitura (`readonly`)](#66-montagem-somente-leitura-readonly)
   - [6.7. Consolidação e Gráficos (`analyze`)](#67-consolidação-e-gráficos-analyze)
   - [6.8. Geração do Relatório PDF e Markdown (`report`)](#68-geração-do-relatório-pdf-e-markdown-report)
   - [6.9. Validação Automática de Integridade (`validate`)](#69-validação-automática-de-integridade-validate)
   - [6.10. Execução Completa em Comando Único (`all`)](#610-execução-completa-em-comando-único-all)
7. [Limpeza Segura do Ambiente (`cleanup`)](#7-limpeza-segura-do-ambiente-cleanup)
8. [Localização dos Dados Brutos e Evidências](#8-localização-dos-dados-brutos-e-evidências)
9. [Como Interpretar os Gráficos](#9-como-interpretar-os-gráficos)
10. [Limitações Conhecidas](#10-limitações-conhecidas)
11. [Declaração de Uso de IA](#11-declaração-de-uso-de-ia)

---

## 1. Objetivos do Projeto

Implementar e validar experimentalmente:
- **Módulo A — Ambiente:** Identificar e documentar rigorosamente o sistema Linux e o Docker Engine, mapeando a arquitetura em diagrama Mermaid e fixando a imagem base por *digest* criptográfico.
- **Módulo B — Namespaces:** Comprovar a separação de visibilidade dos namespaces PID, MNT e NET em dois contêineres concorrentes.
- **Módulo C — Cgroups v2:** Aplicar cotas rígidas de tempo de CPU (`cpu.max`), limites de memória (`memory.max`), bloqueio de swap adicional (`memory.swap.max`) e restrição de processos (`pids.max`), executando uma carga puramente computacional determinística e medindo o impacto do *CFS throttling*.
- **Módulo D — Read-Only e Menor Privilégio:** Comprovar permissão de leitura e negação de escrita (`EROFS`) em montagem somente leitura com usuário não-root e remoção total de *capabilities*.

---

## 2. Identificação da Equipe

- **Instituição:** Universidade Federal de Sergipe (UFS) — Departamento de Computação (DCOMP)
- **Integrantes:**
  - **Bruno Saint Clair** (`brunosaint@dcomp.ufs.br`)
    - *Contribuição:* Concepção da arquitetura dos experimentos, desenvolvimento do orquestrador de cgroups v2 (`run_cgroups.py`), implementação da carga de trabalho determinística (`worker.py`), validação de contadores do escalonador do kernel e consolidação estatística.
  - **Jose Cerqueira**
    - *Contribuição:* Implementação do módulo de inspeção de namespaces (`run_namespaces.py`), módulo de menor privilégio e montagem read-only (`run_readonly.py`), calibração do piloto, pipeline de geração de gráficos em alta resolução e elaboração do relatório técnico.

---

## 3. Pré-requisitos e Ambiente Suportado

O projeto requer um ambiente Linux real com Cgroups v2 ativo:
- **Sistema Operacional:** Linux (testado e homologado em Ubuntu 24.04.5 LTS / Kernel 7.0.0-38-generic x86_64).
- **Docker Engine:** Versão 24+ com suporte a Cgroups v2 (`docker info --format '{{.CgroupVersion}}'` deve retornar `2`).
- **Python:** Python 3.10 ou superior.
- **Git:** Instalado e configurado no PATH.

---

## 4. Estrutura do Repositório

```text
atividade3/
│
├── README.md                           # Manual de reprodução e documentação técnica
├── requirements.txt                    # Dependências de visualização (matplotlib, reportlab)
├── .gitignore                          # Arquivos ignorados pelo controle de versão
│
├── config/
│   └── experiment.json                 # Parâmetros centrais e iterações congeladas
│
├── docker/
│   └── Dockerfile                      # Definição da imagem baseada em digest imutável
│
├── scripts/
│   ├── main.py                         # Ponto único de entrada e orquestração geral
│   ├── check_environment.py            # Verificador automático de pré-requisitos
│   ├── collect_environment.py          # Coletor de metadados da infraestrutura
│   ├── run_namespaces.py               # Executor do experimento de namespaces (Módulo B)
│   ├── run_cgroups.py                  # Executor do piloto e das 6 medições (Módulo C)
│   ├── run_readonly.py                 # Executor do experimento read-only (Módulo D)
│   ├── worker.py                       # Carga determinística inteira e medição cgroups
│   ├── test_readonly.py                # Script interno de validação read-only (EROFS)
│   ├── generate_results.py             # Consolidador de dados em CSV e estatísticas
│   ├── generate_graphs.py              # Gerador de gráficos em alta resolução (PNG)
│   ├── generate_report.py              # Gerador do relatório final (Markdown e PDF)
│   ├── verify_all.py                   # Validador automático de todos os critérios
│   └── cleanup.py                      # Limpeza segura e direcionada de contêineres
│
├── results/
│   ├── environment/                    # Metadados e diagrama da máquina hospedeira
│   ├── namespaces/                     # Evidências e comparação de inodes de namespaces
│   ├── cgroups/
│   │   ├── raw/                        # JSONs brutos e logs das 6 execuções
│   │   ├── csv/                        # results.csv consolidado
│   │   └── summary/                    # statistics.json e summary.md
│   ├── readonly/                       # Evidências de leitura permitida e escrita EROFS
│   ├── graphs/                         # work_per_second.png e wall_time_comparison.png
│   └── report/                         # relatorio.md, relatorio.pdf e validação final
│
└── docs/
    ├── architecture.md                 # Arquitetura detalhada e diagrama Mermaid
    ├── methodology.md                  # Desenho metodológico e controle de variáveis
    ├── analysis.md                     # Análise técnica aprofundada dos resultados
    ├── limitations.md                  # Limitações e ameaças à validade
    └── ai_usage.md                     # Declaração formal de uso de inteligência artificial
```

---

## 5. Instalação Rápida

Em seu terminal Linux, configure o ambiente virtual Python com as bibliotecas necessárias para geração de gráficos e PDF:

```bash
# 1. Criação e ativação do ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalação das dependências
pip install -r requirements.txt
```

---

## 6. Guia de Execução Passo a Passo

Todas as operações são executadas de forma padronizada através do script central `scripts/main.py`.

### 6.1. Verificação do Ambiente (`check`)
Valida automaticamente Python, Docker Daemon, suporte a Cgroups v2, controladores em `/sys/fs/cgroup/`, Git e permissões:
```bash
python scripts/main.py check
```

### 6.2. Documentação da Infraestrutura (`environment`)
Inspeciona os nós do host, fixa a imagem base `python:3.12-slim` pelo digest SHA-256 e constrói a imagem local `so-atividade3:latest`:
```bash
python scripts/main.py environment
```
*Artefatos gerados:* `results/environment/environment.json`, `environment.txt` e `architecture.md`.

### 6.3. Experimento de Namespaces (`namespaces`)
Inicia dois contêineres independentes (`so-atividade3-ns-a` e `so-atividade3-ns-b`), coleta os PIDs do host, PID 1 interno e os identificadores de *inode* dos namespaces PID, MNT e NET:
```bash
python scripts/main.py namespaces
```
*Artefatos gerados:* `results/namespaces/container_a.json`, `container_b.json`, `namespaces.csv`, `namespaces_comparison.md` e `interpretation.md`.

### 6.4. Teste Piloto e Congelamento (`pilot`)
Executa uma rodada na condição C1 para calibrar o tempo de execução e congelar o número de iterações em `config/experiment.json`:
```bash
python scripts/main.py pilot
```
*Artefatos gerados:* `results/cgroups/raw/C1_pilot.json`, `pilot_summary.json` e atualização do `config/experiment.json`.

### 6.5. Medições Oficiais de Cgroups (`cgroups`)
Executa as seis repetições oficiais na ordem alternada obrigatória (C1_rep1 $\rightarrow$ C2_rep1 $\rightarrow$ C1_rep2 $\rightarrow$ C2_rep2 $\rightarrow$ C1_rep3 $\rightarrow$ C2_rep3):
```bash
python scripts/main.py cgroups
```
*Artefatos gerados:* `results/cgroups/raw/C{1,2}_rep{1,2,3}.json` e seus respectivos arquivos de log em `results/cgroups/raw/logs/`.

### 6.6. Montagem Somente Leitura (`readonly`)
Executa o contêiner com UID 1000, `--cap-drop=ALL`, `no-new-privileges:true` e bind mount somente leitura da pasta sintética `dados_demo/` (preparada propositalmente com `chmod 777`):
```bash
python scripts/main.py readonly
```
*Artefatos gerados:* `results/readonly/readonly_test.json`, `readonly_test.log` e `interpretation.md`.

### 6.7. Consolidação e Gráficos (`analyze`)
Processa os dados brutos, consolida o arquivo `results.csv`, calcula medianas, médias e desvios padrões e gera os gráficos PNG em alta resolução:
```bash
python scripts/main.py analyze
```
*Artefatos gerados:* `results/cgroups/csv/results.csv`, `statistics.json`, `summary.md`, `results/graphs/work_per_second.png` e `results/graphs/wall_time_comparison.png`.

### 6.8. Geração do Relatório PDF e Markdown (`report`)
Gera o relatório técnico final completo com tabelas, figuras e respostas a todas as perguntas da atividade:
```bash
python scripts/main.py report
```
*Artefatos gerados:* `results/report/relatorio.md` e `results/report/relatorio.pdf`.

### 6.9. Validação Automática de Integridade (`validate`)
Verifica todos os requisitos do projeto e gera a matriz de conformidade técnica:
```bash
python scripts/main.py validate
```
*Artefatos gerados:* `results/report/final_validation.json` e `results/report/final_validation.md`.

### 6.10. Execução Completa em Comando Único (`all`)
Para reproduzir todo o fluxo sequencial com uma única instrução:
```bash
python scripts/main.py all --yes
```

---

## 7. Limpeza Segura do Ambiente (`cleanup`)

Para remover os contêineres de teste sem afetar contêineres de outros projetos ou apagar os dados experimentais coletados:
```bash
python scripts/main.py cleanup
```

---

## 8. Localização dos Dados Brutos e Evidências

Todos os dados brutos e registros de auditoria estão organizados em:
- **Metadados de Máquina:** [`results/environment/environment.json`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/environment/environment.json)
- **Namespaces Reais:** [`results/namespaces/container_a.json`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/namespaces/container_a.json) e [`container_b.json`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/namespaces/container_b.json)
- **Execuções Oficiais de Cgroups:** [`results/cgroups/raw/`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/cgroups/raw/)
- **CSV Consolidado:** [`results/cgroups/csv/results.csv`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/cgroups/csv/results.csv)
- **Estatísticas Agregadas:** [`results/cgroups/summary/statistics.json`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/cgroups/summary/statistics.json)
- **Evidências Read-Only:** [`results/readonly/readonly_test.json`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/readonly/readonly_test.json)
- **Relatório PDF:** [`results/report/relatorio.pdf`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/results/report/relatorio.pdf)

---

## 9. Como Interpretar os Gráficos

1. **`work_per_second.png` (Trabalho por Segundo):**
   - Apresenta a mediana do throughput computacional nas condições C1 (0,5 CPU) e C2 (1,0 CPU).
   - As barras de erro representam a dispersão entre o menor e o maior valor observado.
   - Observa-se que a Condição C2 alcançou **2,138x** a taxa de processamento de C1, comprovando a eficácia da quota imposta pelo escalonador.
2. **`wall_time_comparison.png` (Wall Time por Repetição):**
   - Ilustra a consistência dos tempos de execução em cada uma das três repetições oficiais.
   - Em C1, o tempo de execução foi de aproximadamente **13 segundos**, dos quais cerca de **6,5 segundos** foram decorrentes de estrangulamento forçado (*CFS throttling*).
   - Em C2, o tempo de execução foi de aproximadamente **6,1 segundos**, com throttling insignificante (~2 milissegundos).

---

## 10. Limitações Conhecidas

- **Instalação Bare-metal:** O projeto foi calibrado para execução em Linux nativo. Em ambientes virtualizados aninhados (como Docker Desktop ou WSL2), os PIDs inspecionados pertencem ao espaço da máquina virtual intermediária.
- **Variações Térmicas do Processador:** Escalonamento dinâmico de frequência (Turbo Boost) e ruído de fundo do sistema operacional podem causar desvios residuais de até ~7% em relação à razão teórica de cotas (2,00x).
- Detalhes completos constam em [`docs/limitations.md`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/docs/limitations.md).

---

## 11. Declaração de Uso de IA

O uso de ferramentas de inteligência artificial (Google Antigravity Assistant / Gemini 3.8 Flash High) foi estritamente restrito ao design de arquitetura de scripts e elaboração de relatórios. Nenhum resultado experimental foi sintetizado ou simulado por IA. Maiores detalhes constam em [`docs/ai_usage.md`](file:///home/bruno/Desktop/Faculdade/10/SO/Unidade%203/docs/ai_usage.md).
