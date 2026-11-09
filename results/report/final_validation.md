# Relatório de Auditoria e Validação Técnica — Atividade 3

## 1. Tabela Executiva de Validação Obrigatória (Seção 11)

| Item | Status | Evidência |
|---|:---:|---|
| Identificação do ambiente | **PASS** | `results/environment/environment.json` |
| Namespaces | **PASS** | `results/namespaces/namespaces.csv` |
| Cgroups CPU | **PASS** | `results/cgroups/raw/C1_rep1.json a C2_rep3.json` |
| Cgroups memória | **PASS** | `results/cgroups/raw/C1_rep1.json (memory_max=268435456, memory_swap_max=0)` |
| Limite de processos | **PASS** | `results/cgroups/raw/C1_rep1.json (pids_max=64)` |
| Bind mount read-only | **PASS** | `results/readonly/readonly_test.json (error_code=EROFS, errno=30)` |
| Testes automatizados | **PASS** | `scripts/test_readonly.py e scripts/worker.py` |
| Geração de resultados | **PASS** | `results/cgroups/csv/results.csv e results/graphs/*.png` |
| Documentação | **PASS** | `README.md, docs/ e relatórios técnicos em results/` |
| Reexecução do projeto | **PASS** | `scripts/main.py (orquestrador executável com suporte a check, all, cleanup)` |

---

## 2. Indicadores Gerais de Conformidade Técnica

- **Índice Geral de Conformidade:** `100.0%` (50/50 verificações aprovadas)
- **PASS:** 50
- **FAIL:** 0
- **NOT_RUN:** 0
- **BLOCKED:** 0

### Ambiente

| Item de Validação | Status | Detalhes Técnicos |
|---|:---:|---|
| Ambiente identificado | **PASS** | Host Kernel: 7.0.0-38-generic (Ubuntu 24.04.5 LTS) |
| Docker funcional | **PASS** | Docker Server: 29.8.1 |
| Cgroup v2 identificado | **PASS** | Cgroup Version: 2 (Driver: systemd) |
| Imagem fixada por digest | **PASS** | Digest: python@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b |
| Diagrama criado | **PASS** | Diagrama Mermaid em docs/architecture.md e results/environment/architecture.md |

### Namespaces

| Item de Validação | Status | Detalhes Técnicos |
|---|:---:|---|
| Contêiner A criado | **PASS** | Contêiner A: so-atividade3-ns-a |
| Contêiner B criado | **PASS** | Contêiner B: so-atividade3-ns-b |
| PID interno registrado | **PASS** | Comm PID 1: sleep e sleep |
| PID do host do daemon registrado | **PASS** | Host PIDs: 329376 e 329454 |
| PID namespace coletado | **PASS** | A: pid:[4026533157] | B: pid:[4026533482] |
| Mount namespace coletado | **PASS** | A: mnt:[4026533138] | B: mnt:[4026533479] |
| Network namespace coletado | **PASS** | A: net:[4026533159] | B: net:[4026533484] |
| Tabela comparativa criada | **PASS** | Arquivo results/namespaces/namespaces.csv existente |
| Interpretação escrita | **PASS** | Interpretação técnica presente (5139 caracteres) |

### Cgroups

| Item de Validação | Status | Detalhes Técnicos |
|---|:---:|---|
| Carga determinística implementada | **PASS** | Algoritmo LCG de inteiros de 32 bits implementado em scripts/worker.py |
| Teste piloto realizado | **PASS** | Registro do piloto presente em results/cgroups/raw/ |
| Iterações congeladas | **PASS** | Iterações congeladas em 20,000,000 |
| C1 configurada | **PASS** | C1 Quota: 50000 / 100000 (0.5 CPU) |
| C2 configurada | **PASS** | C2 Quota: 100000 / 100000 (1.0 CPU) |
| Memória limitada | **PASS** | Memory limit: 256m (256 MiB) |
| Memória + swap limitada | **PASS** | Memory swap: 256m (0 swap adicional) |
| PIDs limitados | **PASS** | PIDs limit: 64 |
| cpu.max confirmado | **PASS** | cpu.max confirmado no kernel em todas as 6 execuções |
| memory.max confirmado | **PASS** | 268435456 bytes (256 MiB) confirmado em todas as 6 execuções |
| pids.max confirmado | **PASS** | 64 tarefas confirmado em todas as 6 execuções |
| Seis registros preservados | **PASS** | 6/6 registros brutos JSON válidos em results/cgroups/raw/ |
| Checksums conferidos | **PASS** | Checksum determinístico único: 0xfeb38a80 |
| CSV gerado | **PASS** | results/cgroups/csv/results.csv presente |
| Medianas calculadas | **PASS** | C1: 13.0738s | C2: 6.1143s |
| Variação calculada | **PASS** | C1 StdDev: 1.2035s | C2 StdDev: 0.2934s |
| Gráfico gerado | **PASS** | Gráficos work_per_second.png e wall_time_comparison.png gerados |
| Análise documentada | **PASS** | docs/analysis.md presente (7142 caracteres) |

### Read-only

| Item de Validação | Status | Detalhes Técnicos |
|---|:---:|---|
| Diretório sintético criado | **PASS** | dados_demo/texto.txt configurado com permissão 777 |
| Usuário não root utilizado | **PASS** | UID: 1000 |
| Capabilities removidas | **PASS** | --cap-drop=ALL aplicado |
| no-new-privileges aplicado | **PASS** | no-new-privileges:true confirmado |
| Leitura bem-sucedida | **PASS** | Conteúdo lido: 'Documento sintetico' |
| Escrita negada | **PASS** | Bloqueado pelo Kernel |
| Código de erro registrado | **PASS** | Código do kernel: EROFS (errno 30) - Read-only file system |

### Documentação

| Item de Validação | Status | Detalhes Técnicos |
|---|:---:|---|
| README completo | **PASS** | README.md com 12883 caracteres |
| Análise técnica de resultados | **PASS** | docs/analysis.md presente com discussão quantitativa aprofundada |
| Síntese estatística documentada | **PASS** | results/cgroups/summary/summary.md presente com medianas, médias e dispersão |
| Interpretação de namespaces | **PASS** | results/namespaces/interpretation.md presente com fundamentos de isolamento |
| Interpretação de read-only | **PASS** | results/readonly/interpretation.md presente com distinção entre VFS e DAC |
| Dados brutos disponíveis | **PASS** | Arquivos JSON em results/cgroups/raw/ e logs/ |
| Gráficos disponíveis | **PASS** | PNGs em results/graphs/ |
| Diagrama de arquitetura disponível | **PASS** | Mermaid em results/environment/architecture.md e docs/architecture.md |
| Declaração de IA disponível | **PASS** | docs/ai_usage.md presente |
| Limitações documentadas | **PASS** | docs/limitations.md presente |
| Referências incluídas | **PASS** | Referências aos manuais Linux, Cgroups e Docker incluídas no README.md |

