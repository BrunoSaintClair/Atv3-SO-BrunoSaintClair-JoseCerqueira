# Análise e Interpretação de Segurança: Montagem Read-Only e Menor Privilégio

Este documento formaliza as evidências experimentais da execução sob o princípio do menor privilégio e isolamento de sistemas de arquivos via montagem somente leitura (*read-only bind mount*).

## 1. Evidências Empíricas Coletadas

- **Usuário e Identidade Efetiva:** UID `1000` / GID `1000` (não-root).
- **Remoção de Privilégios (*Capabilities*):** `ALL`.
- **Proteção contra Escalação:** `no-new-privileges:true` (impede transição via binários *setuid/setgid*).
- **Pilha de Rede:** `none` (completamente desabilitada).
- **Ponto de Montagem:** Bind mount de `/home/bruno/Desktop/Faculdade/10/SO/Unidade 3/dados_demo` para `/dados` com flag `readonly=true`.
- **Resultado do Teste de Leitura:**
  - Status: **Sucesso**
  - Conteúdo verificado: `"Documento sintetico"`
- **Resultado do Teste de Escrita:**
  - Status: **Bloqueado pelo Kernel**
  - Código de Erro do Kernel: **`EROFS`** (`errno 30`) — *Read-only file system*

---

## 2. Fundamentação Teórica e Diferenciação Arquitetural

### 2.1. Diferença entre Mount Namespace e Montagem Somente Leitura
- O **Mount Namespace** (`CLONE_NEWNS`) provê a **visibilidade isolada** dos pontos de montagem. Ele permite que o contêiner tenha uma árvore de diretórios própria (`/`, `/dados`, `/proc`) sem que novas montagens ou desmontagens afetem o host.
- A **Montagem Somente Leitura** (*Read-only Mount*) é um atributo do *VFS (Virtual File System)* que impõe uma **política estrita de acesso** àquele nó da árvore. Mesmo que o processo tenha visão do diretório montado, o kernel rejeita na raiz qualquer chamada de sistema de mutação (`open(O_WRONLY|O_CREAT)`, `unlink`, `rename`, `chmod`).

### 2.2. Permissões Tradicionais (DAC) vs. Bloqueio Read-only do Kernel
- No teste realizado, o diretório hospedeiro `dados_demo` foi propositalmente configurado com permissão POSIX aberta (`chmod 777`).
- Se a restrição fosse apenas baseada no DAC (*Discretionary Access Control* - usuário/grupo), o usuário UID 1000 conseguiria criar o arquivo `novo.txt` sem obstáculos.
- O fato de a chamada de sistema ter retornado o código de erro **`EROFS` (Read-only file system - errno 30)**, e **não** `EACCES` (Permission denied - errno 13), comprova categoricamente que o bloqueio ocorreu na camada do VFS/Superbloco de montagem gerenciado pelo kernel Linux, independente de permissões de arquivo.

### 2.3. O Papel do Princípio do Menor Privilégio
A combinação de:
1. Execução como usuário comum (`UID 1000`);
2. Descarte de todas as capacidades de superusuário (`--cap-drop=ALL`), desativando privilégios como `CAP_DAC_OVERRIDE`, `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`;
3. Bloqueio de novas capacidades (`no-new-privileges:true`);
4. Montagens sensíveis em modo somente leitura (`readonly`);

estabelece uma estratégia de **Defesa em Profundidade** (*Defense in Depth*). Mesmo que uma aplicação vulnerável sofra injeção de código arbitrário ou execução de payload malicioso, o atacante é incapaz de alterar arquivos de configuração, sobrescrever artefatos ou escalar privilégios no sistema.

### 2.4. Limitações: Por que Read-only não é Isolamento Absoluto?
Uma montagem *read-only* impede modificações em disco no caminho montado, mas **não** protege contra:
- **Exaustão de Recursos de Memória ou CPU:** Ataques de negação de serviço (DoS) locais precisam ser mitigados via *Cgroups*.
- **Vazamento de Informações Confidenciais:** Leitura não autorizada de dados caso segredos sejam indevidamente montados no diretório.
- **Vulnerabilidades de Kernel:** Falhas no próprio subsistema VFS do kernel Linux que permitam contorno de flags de montagem.
