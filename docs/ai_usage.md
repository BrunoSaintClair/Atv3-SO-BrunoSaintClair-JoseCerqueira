# Declaração de Uso de Inteligência Artificial (AI Usage)

Em conformidade com as diretrizes acadêmicas da disciplina de Sistemas Operacionais, este documento registra a transparência metodológica do suporte computacional por modelos de linguagem durante o desenvolvimento da solução da **Atividade 3**.

---

## 1. Identificação do Modelo e Ferramentas

- **Ferramenta / Modelo Utilizado:** Google Antigravity Assistant (Gemini 3.8 Flash High e Medium).
- **Ambiente de Execução:** Antigravity CLI integrado ao ambiente Linux de desenvolvimento.
- **Finalidade:** Auxílio no planejamento da automação dos experimentos, estruturação de scripts em Python, elaboração de comandos do Docker CLI, tratamento estatístico dos dados e apoio na geração de gráficos.
- **Regra Fundamental Respeitada:** Nenhuma saída textual ou heurística gerada pela IA foi utilizada como resultado ou evidência experimental. Todas as métricas, tempos, *inodes* de namespaces e identificadores numéricos foram obtidos exclusivamente por meio da execução de comandos reais no sistema operacional Linux e no Docker Engine.

---

## 2. Prompts Relevantes Utilizados

### Prompt 1 — Implementação da Carga de CPU e Leitura de Cgroups v2
> *"Preciso criar um script em Python para rodar dentro de um container Docker e testar limites de CPU com cgroups v2. A carga precisa ser puramente computacional (sem depender de rede ou disco) e precisa ser determinística, fazendo exatamente as mesmas operações a cada execução para comparar os tempos de forma justa. Como posso implementar esse loop e ler as métricas de tempo e throttling direto dos arquivos do cgroups v2?"*

### Prompt 2 — Inspeção e Comprovação de Namespaces
> *"Como posso inspecionar os identificadores reais de namespaces (PID, rede e montagem) de dois containers rodando no Docker para demonstrar o isolamento? Tem como ler direto do `/proc` de cada container para comparar os IDs numéricos dos namespaces?"*

### Prompt 3 — Desacoplamento entre DAC e VFS no Teste Read-Only
> *"Na atividade prática, preciso montar uma pasta como somente leitura no container com usuário não-root. Mas o professor exige que o teste comprove que o bloqueio de escrita aconteceu por causa da montagem read-only do kernel, e não porque o usuário não tinha permissão no arquivo (chmod). Como posso montar um cenário de teste automatizado que diferencie o erro EROFS de um EACCES?"*

### Prompt 4 — Agregação dos Resultados e Gráficos
> *"Tenho os arquivos JSON das execuções alternadas do experimento de cgroups (3 repetições para C1 e 3 para C2). Preciso de um script para consolidar esses dados em um CSV, calcular média, mediana e desvio padrão, e gerar gráficos no Matplotlib comparando o tempo de execução e a taxa de trabalho por segundo."*

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
