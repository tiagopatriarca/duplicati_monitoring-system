"""
Script de Simulação de Webhooks do Duplicati
Dispara requisições HTTP POST para testar o recebimento de dados e os alertas de jobs pendentes.
"""

import requests
import json
import time
from datetime import datetime

WEBHOOK_URL = "http://localhost:5000/api/webhook/duplicati"

# Payloads de Exemplo Simulando o Duplicati
payloads_teste = [
    {
        "Extra": {
            "BackupName": "Alfa-DB-Backup"
        },
        "ParsedResult": "Success",
        "Main": {
            "SizeOfAddedFiles": 18450000000,
            "Duration": "00:25:40.000"
        }
    },
    {
        "Extra": {
            "BackupName": "Beta-ERP-Daily"
        },
        "ParsedResult": "Warning",
        "Main": {
            "SizeOfAddedFiles": 9200000000,
            "Duration": "00:35:12.000"
        }
    },
    {
        "Extra": {
            "BackupName": "Gama-Prontuarios-Full"
        },
        "ParsedResult": "Error",
        "Main": {
            "SizeOfAddedFiles": 0,
            "Duration": "00:01:05.000"
        }
    }
]

def run_simulation():
    print(f"🚀 Iniciando simulação de envio de webhooks para {WEBHOOK_URL}...\n")
    for i, payload in enumerate(payloads_teste, 1):
        backup_name = payload["Extra"]["BackupName"]
        result = payload["ParsedResult"]
        print(f"[{i}/{len(payloads_teste)}] Enviando backup '{backup_name}' (Status: {result})...")
        
        try:
            response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Sucesso! Resposta do Servidor: {response.json().get('message')}")
            else:
                print(f"   ❌ Erro Status Code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"   ⚠️ Falha ao conectar no servidor (O app.py está rodando?): {e}")

        time.sleep(1)

    print("\n🎉 Simulação concluída! Acesse http://localhost:5000 no seu navegador para ver os resultados.")

if __name__ == "__main__":
    run_simulation()
