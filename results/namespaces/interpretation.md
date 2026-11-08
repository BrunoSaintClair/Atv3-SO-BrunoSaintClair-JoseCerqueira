# Análise e Interpretação de Isolamento por Namespaces

Este documento analisa os dados empíricos coletados durante a execução simultânea dos contêineres `so-atividade3-ns-a` e `so-atividade3-ns-b`.

## 1. Tabela Comparativa de Identificadores Reais

| Recurso / Namespace | Contêiner A (`so-atividade3-ns-a`) | Contêiner B (`so-atividade3-ns-b`) | Resultado Observado |
|---|---|---|---|
| **PID do Host (Daemon)** | `160574` | `160668` | Diferente (Processos distintos no host) |
| **PID 1 Interno (`comm`)** | `sleep` (PID 1) | `sleep` (PID 1) | Ambos são PID 1 localmente |
| **PID Namespace** | `pid:[4026533481]` | `pid:[4026533542]` | **Diferente (Isolado)** |
| **Mount (MNT) Namespace** | `mnt:[4026533478]` | `mnt:[4026533539]` | **Diferente (Isolado)** |
| **Network (NET) Namespace** | `net:[4026533483]` | `net:[4026533544]` | **Diferente (Isolado)** |
| **IPC Namespace** | `ipc:[4026533480]` | `ipc:[4026533541]` | Diferente (Filas/Memória Compartilhada isoladas) |
| **UTS Namespace** | `uts:[4026533479]` | `uts:[4026533540]` | Diferente (Hostnames independentes) |

---

## 2. Respostas Fundamentadas às Questões Obrigatórias

### 2.1. O que é o Namespace PID?
O namespace PID (*Process ID Namespace*) virtualiza a árvore de processos do Linux. Ele garante que os processos dentro de um determinado contêiner visualizem apenas os seus próprios descendentes, iniciando a numeração a partir de 1 (`init`/processo raiz do contêiner). Ele oculta totalmente os processos do sistema operacional hospedeiro e de outros contêineres.

### 2.2. O que é o Namespace Mount (MNT)?
O namespace MNT isola a tabela de pontos de montagem do sistema de arquivos (*mount points*). Cada contêiner possui sua própria raiz virtual (`/`), podendo montar, desmontar ou alterar sistemas de arquivos (como `/proc`, `/sys`, *rootfs* overlay) sem que essas modificações sejam propagadas ou visíveis para o host ou para contêineres vizinhos.

### 2.3. O que é o Namespace Network (NET)?
O namespace NET virtualiza a pilha de rede completa do kernel: interfaces de rede (loopback, veth), tabelas de roteamento, regras de firewall (iptables/nftables) e portas de sockets (TCP/UDP). Mesmo configurados com `--network none`, os contêineres possuem pilhas de rede separadas (apenas com sua interface de loopback isolada), garantindo que conexões ou vinculações de portas não conflitem.

### 2.4. O que cada identificador demonstra?
No Linux, os links simbólicos em `/proc/[pid]/ns/` apontam para objetos especiais do kernel no formato `tipo:[inode_number]`.
- O contêiner A possui `pid:pid:[4026533481]` e o contêiner B possui `pid:pid:[4026533542]`.
- O número de inode diferente comprova matematicamente que o kernel alocou estruturas de dados `struct nsproxy` e `struct pid_namespace` distintas na memória do kernel para cada um dos contêineres.

### 2.5. Por que os dois contêineres possuem PID 1 internamente?
Porque cada contêiner reside em seu próprio namespace PID. No momento em que um namespace PID é criado (`CLONE_NEWPID`), o primeiro processo criado torna-se o processo raiz do namespace e recebe obrigatoriamente o PID 1. Esse processo atua como o inicializador local, adotando processos órfãos dentro daquele namespace.

### 2.6. Por que o PID 1 interno não equivale ao PID do host?
A numeração de processos é relativa à hierarquia de namespaces. No namespace global do hospedeiro, todos os processos de todos os contêineres são visíveis e recebem identificadores únicos globais. 
O processo do contêiner A possui PID `160574` no host, enquanto o processo do contêiner B possui PID `160668`. Ambos são enxergados como processos convencionais gerenciados pelo escalonador do kernel Linux hospedeiro.

### 2.7. Por que namespaces diferentes não significam kernels independentes?
Namespaces não realizam emulação de hardware nem executam instâncias isoladas de sistemas operacionais. Eles são simplesmente filtros lógicos de visibilidade dentro do mesmo e único kernel Linux (`Linux 7.0.0-38-generic`). 
Se houver uma pane de kernel (*kernel panic*), exaustão de descritores de arquivo ou uma vulnerabilidade crítica em uma chamada de sistema (*syscall*), todos os contêineres que compartilham aquele kernel são afetados.

### 2.8. Quais aspectos não podem ser comprovados apenas pelos handles?
Os identificadores de inode comprovam a separação das tabelas de controle, mas **não** comprovam:
1. Limitação ou divisão de recursos físicos de hardware (função exclusiva dos *Cgroups*).
2. Políticas de segurança, restrição de *capabilities* ou filtros de chamadas de sistema (*seccomp* / AppArmor).
3. Existência de canais ocultos (*covert channels*) como concorrência de cache L3 da CPU ou acesso a informações temporais globais.

### 2.9. Relação entre PID do Host e Ambientes Virtualizados
No ambiente em teste (*Bare-metal Linux*), o comando `docker inspect` retorna o PID direto do processo no `/proc` local. Caso o experimento fosse executado no Docker Desktop (Windows/macOS) ou WSL2, o PID retornado pertenceria à máquina virtual Linux interna do Docker e não estaria presente no gerenciador de tarefas do sistema operacional hospedeiro externo.
