# Declaração de Uso de Inteligência Artificial (AI Usage)

Em conformidade com as diretrizes acadêmicas da disciplina de Sistemas Operacionais, este documento registra a transparência metodológica do suporte computacional por modelos de linguagem durante o desenvolvimento da solução da **Atividade 3**.

---

## 1. Identificação do Modelo e Ferramentas

- **Ferramenta / Modelo Utilizado:** Google Antigravity Assistant (Gemini 3.8 Flash High).
- **Ambiente de Execução:** Antigravity CLI integrado ao ambiente Linux de desenvolvimento.
- **Finalidade:** Auxílio no planejamento da arquitetura de automação, estruturação do boilerplate de scripts Python, elaboração de comandos do Docker CLI e formatação dos relatórios em Markdown e PDF.
- **Regra Fundamental Respeitada:** Nenhuma saída textual ou heurística gerada pela IA foi utilizada como resultado ou evidência experimental. Todas as métricas, tempos, *inodes* de namespaces e identificadores numéricos foram obtidos exclusivamente por meio da execução de comandos reais no sistema operacional Linux e no Docker Engine.

---

## 2. Prompts Relevantes Utilizados

### Prompt 1 — Estruturação do Worker Determinístico e Medição de Cgroups v2
> *"Desenvolva uma rotina de carga CPU-bound em Python puro, baseada em gerador linear congruente com operações inteiras e máscara de 32 bits, que seja estritamente determinística e independente de bibliotecas externas. A rotina deve calcular wall time com `time.perf_counter()`, CPU time com `time.process_time()` e capturar snapshots dos pseudo-arquivos de Cgroups v2 em `/sys/fs/cgroup/cpu.stat`, calculando os deltas de `usage_usec` e `throttled_usec`."*

### Prompt 2 — Desacoplamento entre DAC e VFS no Teste Read-Only
> *"Como estruturar um teste automatizado no Docker que comprove que a negação de escrita decorre especificamente da flag de montagem readonly do VFS do kernel e não de permissões tradicionais POSIX (DAC)? Proponha um mecanismo que distinga o código de erro EROFS de EACCES."*

### Prompt 3 — Pipeline Automatizado de Consolidação e Gráficos
> *"Implemente um script de agregação que processe os JSONs individuais das 6 execuções de cgroups, calcule a mediana e dispersão do tempo de execução e taxa de trabalho, e gere gráficos em alta resolução no Matplotlib destacando a mediana e as barras de erro empíricas."*

---

## 3. Sugestões Adotadas, Corrigidas ou Rejeitadas

| Sugestão da IA | Decisão | Justificativa / Adaptação Realizada |
|---|---|---|
| Uso de laço simples `sum(range(N))` para o worker | **Rejeitada** | Otimizadores internos do CPython e tipos inteiros de precisão arbitrária poderiam introduzir não-linearidades ou atalhos. Foi adotado o gerador linear congruente com aritmética de 32 bits (`& 0xFFFFFFFF`), garantindo passos uniformes de CPU. |
| Teste de escrita em arquivo pré-existente no teste read-only | **Rejeitada** | Tentar escrever em arquivo existente poderia disparar checagem de permissão de escrita do arquivo (`EACCES`). A solução correta foi tentar criar um novo arquivo (`/dados/novo.txt`) em diretório propositalmente aberto com permissão `777`, garantindo que apenas a restrição de superbloco de montagem (`EROFS`) atuasse. |
| Coleta de handles de namespaces via `/proc/1/ns/` com `readlink` | **Adotada e Verificada** | Verificada diretamente com `readlink /proc/1/ns/{pid,mnt,net}` dentro dos contêineres, confirmando a extração exata dos identificadores de *inode* do kernel. |
| Formatação de gráficos com estilo moderno do Matplotlib | **Adotada com Correções** | Ajustado para utilizar fallbacks elegantes caso o tema `seaborn` estivesse indisponível, garantindo compatibilidade direta com a biblioteca padrão. |

---

## 4. Métodos de Verificação das Implementações

Todas as implementações propostas foram submetidas aos seguintes procedimentos de verificação empírica:
1. **Inspeção de Códigos de Retorno do Kernel:** Validação de que erros de escrita retornavam estritamente o código `30` (`EROFS`).
2. **Conferência Criptográfica de Checksums:** Comparação dos hashes das seis execuções independentes de cgroups para comprovar a invariância matemática da carga de trabalho.
3. **Validação Cruzada de Métricas:** Conferência matemática de que o *wall time* correspondia à soma do *CPU time* com o tempo de *throttling* registrado pelo kernel.
