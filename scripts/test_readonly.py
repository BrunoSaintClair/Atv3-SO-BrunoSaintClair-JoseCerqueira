#!/usr/bin/env python3
"""
Script de teste para verificação do isolamento de montagem somente leitura (read-only).
Executado internamente no contêiner com privilégios reduzidos.
Verifica:
1. Leitura com sucesso do arquivo existente /dados/texto.txt.
2. Negação estrita de escrita com verificação de código EROFS (Read-only file system).
"""

import errno
import json
import os
import sys


def main() -> int:
    target_dir = "/dados"
    read_file_path = os.path.join(target_dir, "texto.txt")
    write_file_path = os.path.join(target_dir, "novo.txt")

    uid = os.getuid()
    gid = os.getgid()

    result = {
        "uid": uid,
        "gid": gid,
        "read_test": {
            "file": read_file_path,
            "success": False,
            "content": "",
            "error": None
        },
        "write_test": {
            "file": write_file_path,
            "write_denied": False,
            "errno": None,
            "error_code": None,
            "error_message": None
        },
        "status": "failure"
    }

    # 1. Teste de Leitura
    try:
        with open(read_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        result["read_test"]["success"] = True
        result["read_test"]["content"] = content.strip()
        print(f"[TESTE LEITURA] Sucesso. Conteúdo lido:\n{content.strip()}")
    except Exception as e:
        result["read_test"]["error"] = str(e)
        print(f"[TESTE LEITURA] Falha inesperada ao ler: {e}", file=sys.stderr)

    # 2. Teste de Escrita
    try:
        with open(write_file_path, "w", encoding="utf-8") as f:
            f.write("teste")
        # Se chegou aqui sem lançar exceção, a escrita foi permitida (falha do teste de segurança)
        result["write_test"]["write_denied"] = False
        print("[TESTE ESCRITA] FALHA: Escrita foi permitida em montagem read-only!", file=sys.stderr)
    except OSError as e:
        result["write_test"]["write_denied"] = True
        result["write_test"]["errno"] = e.errno
        result["write_test"]["error_code"] = errno.errorcode.get(e.errno, str(e.errno))
        result["write_test"]["error_message"] = os.strerror(e.errno)
        print(f"[TESTE ESCRITA] Sucesso: Escrita bloqueada pelo kernel.")
        print(f"Código de erro: {result['write_test']['error_code']} ({e.errno}) - {result['write_test']['error_message']}")

    # Validação geral
    # O teste só passa se a leitura teve sucesso E a escrita foi negada especificamente com EROFS
    if (result["read_test"]["success"] and
        result["write_test"]["write_denied"] and
        result["write_test"]["error_code"] == "EROFS"):
        result["status"] = "success"
    else:
        result["status"] = "failure"

    print("\n--- RESUMO DO TESTE ---")
    print(json.dumps(result, indent=2))

    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
