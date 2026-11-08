# Metodologia Experimental — Atividade 3

Este documento detalha o desenho metodológico, procedimentos de controle de variáveis, rastreabilidade e critérios de repetibilidade adotados em todos os experimentos da **Atividade 3 de Sistemas Operacionais**.

---

## 1. Princípios Metodológicos Fundamentais

1. **Execução Real e Empírica:** Todos os dados, tabelas e gráficos são gerados a partir de chamadas reais de sistema, arquivos de pseudossistemas de arquivos (`/proc` e `/sys/fs/cgroup`) e saídas do Docker Engine. Nenhum dado sintético fictício é utilizado para preencher resultados.
2. **Determinismo Computacional:** A carga de trabalho CPU-bound é matematicamente reprodutível, independente de bibliotecas externas de rede, GPUs ou I/O de disco volátil, validada por checksum criptográfico idêntico nas seis repetições oficiais.
3. **Imutabilidade e Rastreabilidade:** A imagem de contêiner é fixada por seu *digest* criptográfico SHA-256 (`python@sha256:...`), e todas as execuções possuem logs brutos e registros JSON individuais em disco antes de qualquer etapa de agregação estatística.
4. **Isolamento de Efeitos Cruzados:** Os contêineres são executados com `--network none` e com limpeza controlada entre execuções, e as condições C1 e C2 são alternadas para mitigar o viés de aquecimento térmico (*thermal throttling*) e ruído de fundo do hospedeiro.

---

## 2. Metodologia do Módulo A (Ambiente e Arquitetura)

- **Objetivo:** Identificar e documentar rigorosamente a topologia do sistema hospedeiro, daemon do Docker e mecanismos de virtualização leve.
- **Diferenciação Crítica:** Distinção entre o sistema operacional local e o ambiente do daemon do Docker. No ambiente inspecionado, foi constatado que o Docker executa em instalação nativa (*bare-metal*) no Linux Ubuntu 24.04 LTS com Kernel 7.0.0-38-generic, compartilhando o mesmo kernel diretamente sem máquinas virtuais intermediárias (diferente de arquiteturas baseadas em WSL2 ou Docker Desktop em macOS/Windows).
- **Fixação da Imagem:**
  1. Download e inspeção de `python:3.12-slim`.
  2. Extração do digest de repositório SHA-256.
  3. Construção da imagem derivada `so-atividade3:latest` injetando os scripts de workload e testes internos de segurança.

---

## 3. Metodologia do Módulo B (Namespaces)

- **Objetivo:** Comprovar a separação lógica de recursos entre dois contêineres concorrentes (`so-atividade3-ns-a` e `so-atividade3-ns-b`).
- **Procedimento:**
  1. Criação concorrente dos dois contêineres com a mesma imagem base e comando `sleep infinity`.
  2. Inspeção do processo externo via `docker inspect --format '{{.State.Pid}}'` para obter o PID do processo na visão global do kernel do hospedeiro.
  3. Inspeção interna via `docker exec [container] sh -c 'cat /proc/1/comm'` para constatar o PID 1 local.
  4. Leitura dos descritores virtuais do kernel via `readlink /proc/1/ns/{pid,mnt,net,ipc,uts,user}`.
  5. Comparação algorítmica: os identificadores no formato `tipo:[inode_number]` são comparados. A comprovação do isolamento ocorre quando os números de *inode* são estritamente diferentes entre os contêineres A e B.

---

## 4. Metodologia do Módulo C (Cgroups v2)

- **Objetivo:** Medir quantitativamente o impacto da imposição de quotas de tempo de CPU (`cpu.max`) sobre uma carga determinística.
- **Configurações Experimentais:**
  - **Condição C1 (0,5 CPU):** `--cpu-period=100000 --cpu-quota=50000 --memory=256m --memory-swap=256m --pids-limit=64`
  - **Condição C2 (1,0 CPU):** `--cpu-period=100000 --cpu-quota=100000 --memory=256m --memory-swap=256m --pids-limit=64`
- **Algoritmo da Carga:**
  Gerador linear congruente de 32 bits executando operações aritméticas puras de inteiros em loop:
  $$X_{n+1} = (X_n \times 1664525 + 1013904223 + i) \pmod{2^{32}}$$
- **Teste Piloto e Congelamento:**
  - Execução preliminar com 20.000.000 de iterações na condição mais restritiva (C1).
  - Verificação do tempo de relógio contra a janela de segurança (teto máximo de 90 segundos).
  - Confirmação do tempo de ~13 segundos, perfeitamente calibrado para acumular amostragem de CFS throttling sem estourar o limite.
  - Congelamento estrito do parâmetro `frozen_iterations = 20000000` em `config/experiment.json`.
- **Protocolo de Medição das 6 Execuções Oficiais:**
  - Ordem alternada: C1_rep1 $\rightarrow$ C2_rep1 $\rightarrow$ C1_rep2 $\rightarrow$ C2_rep2 $\rightarrow$ C1_rep3 $\rightarrow$ C2_rep3.
  - Medição temporal via `time.perf_counter()` (*wall time*) e `time.process_time()` (*process CPU time*).
  - Captura de snapshots do `/sys/fs/cgroup/cpu.stat` antes e depois da execução para calcular os deltas de tempo consumido e estrangulado.
  - Validação estrita de checksums: todos os 6 registros devem ser idênticos.
- **Tratamento Estatístico:**
  - Cálculo de mediana (métrica primária resistente a outliers), média aritmética, mínimo, máximo e desvio padrão amostral.

---

## 5. Metodologia do Módulo D (Menor Privilégio e Read-Only)

- **Objetivo:** Comprovar a negação de mutação de arquivos através da restrição de montagem do kernel, desacoplada de permissões de usuário (DAC).
- **Controle Metodológico Rigoroso:**
  - Criação de diretório sintético `dados_demo/` com arquivo `texto.txt`.
  - Atribuição deliberada de permissão POSIX total ao diretório hospedeiro (`chmod 777 dados_demo/`). Esse passo é crucial: com 777, qualquer processo de qualquer usuário poderia criar arquivos caso as permissões POSIX tradicionais fossem o único filtro.
  - Execução de contêiner não-root com UID/GID 1000:1000, `--cap-drop=ALL` (remoção de todas as *Linux capabilities*), `--security-opt no-new-privileges:true` e `--mount type=bind,source=...,target=/dados,readonly`.
- **Critério de Validação:**
  1. A leitura de `/dados/texto.txt` deve retornar o conteúdo com sucesso.
  2. A tentativa de abertura para escrita em `/dados/novo.txt` deve ser interceptada pelo VFS do kernel e resultar especificamente no erro **`EROFS` (Read-only file system - errno 30)**.
  3. Se o erro retornado fosse `EACCES` (Permission denied), a evidência seria rejeitada, pois decorreria de permissões de arquivo e não da política de montagem do kernel.
