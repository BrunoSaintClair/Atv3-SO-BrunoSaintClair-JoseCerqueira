# Limitações Conhecidas e Ameaças à Validade Experimental

Este documento cataloga de forma explícita as limitações arquiteturais, restrições do ambiente e ameaças à validade científica identificadas durante o planejamento e execução dos experimentos da **Atividade 3**.

---

## 1. Limitações de Isolamento por Namespaces

1. **Compartilhamento de Kernel Único:** 
   Embora os namespaces PID, MNT e NET isolem a visibilidade de recursos, eles não executam um novo kernel. Uma falha de segurança no kernel do host (como uma vulnerabilidade de escalação local de privilégios ou *kernel panic*) afeta indistintamente todos os contêineres e o sistema hospedeiro.
2. **Canais Laterais (*Covert / Side Channels*):**
   Namespaces não impedem ataques de temporização (*timing attacks*) baseados em contenção de cache compartilhado L3 da CPU ou acesso a interfaces temporais globais do sistema (`CLOCK_MONOTONIC`).
3. **Visibilidade Global a Partir do Host:**
   O isolamento de PID é unidirecional (de fora para dentro). O host tem visibilidade e controle total sobre os processos do contêiner, podendo enviar sinais (`SIGKILL`) ou inspecionar memória via `/proc/[host_pid]/mem`.

---

## 2. Limitações e Ameaças na Medição de Cgroups v2

1. **Ruído de Fundo do Sistema Operacional Hospedeiro (*Host Noise*):**
   Os experimentos foram executados em uma estação de trabalho real (Linux Ubuntu 24.04 bare-metal com ambiente gráfico ativo). Processos de segundo plano do sistema operacional, navegadores e I/O de disco concorrentes podem disputar frações de tempo de CPU, causando pequenas flutuações nas medições (mitigadas pelo uso de 3 repetições e pelo cálculo da mediana).
2. **Variação de Frequência da CPU (*DVFS - Dynamic Voltage and Frequency Scaling*):**
   Processadores modernos x86_64 ajustam dinamicamente sua frequência de operação com base na carga e na temperatura (Intel Turbo Boost). Uma medição executada em um núcleo operando a 4.2 GHz terá um *throughput* instantâneo ligeiramente superior à mesma carga executada a 3.8 GHz. A estratégia de alternância das execuções (C1 $\rightarrow$ C2 $\rightarrow$ C1 $\rightarrow$ C2 $\rightarrow$ C1 $\rightarrow$ C2) foi adotada especificamente para neutralizar esse viés térmico acumulado.
3. **Granularidade do Período do CFS (*Completely Fair Scheduler*):**
   O período padrão adotado foi de 100.000 µs (100 ms). A alocação da quota ocorre em frações desse período. Se o processo esgota seus 50.000 µs logo no início da fatia, ele permanece suspenso até o fim do período de 100 ms. Essa dinâmica em rajadas (*burstiness*) introduz atrasos intrínsecos de agendamento que explicam por que o ganho de desempenho não é matematicamente igual a 2,00x.
4. **Resolução de Temporizadores e *Overhead* de Medição:**
   O worker Python utiliza chamadas nativas de alta precisão (`time.perf_counter()` e `time.process_time()`). No entanto, o custo intrínseco de inicialização do interpretador CPython e desmontagem do contêiner adiciona uma latência fixa de aproximadamente 150-300 ms, isolada ao medir o tempo estritamente ao redor da função `workload()`.

---

## 3. Limitações de Segurança e Montagem Read-Only

1. **Permissões de Arquivos em Volume Hospedeiro:**
   A montagem somente leitura (*read-only bind mount*) foi comprovada como eficaz contra alterações nos arquivos mapeados no diretório `/dados`. Contudo, essa restrição se limita ao nó da árvore de diretórios montado; ela não impede que o contêiner crie arquivos temporários na sua própria camada de escrita efêmera de contêiner (`/tmp` ou `/app`), caso o contêiner não tenha sua raiz montada com `--read-only`.
2. **Ausência de Quota de I/O em Bind Mounts:**
   Embora o Cgroups v2 possua o controlador `io`, o controle fino de IOPS e taxa de transferência em sistemas de arquivos compartilhados via *bind mount* depende da estrutura do subsistema de blocos do kernel hospedeiro, não sendo escopo dos limites estipulados nesta atividade.
