"""Prueba diagnostica para SNMP en el 9300 (10.10.20.181).
No borra nada. Imprime el codigo y el cuerpo de error de cada intento,
para saber por que el PUT da 400/404.
Uso en PowerShell, con (.venv) y VPN conectado:
  $env:SANDBOX_USER="developer"; $env:SANDBOX_PASS="C1sco12345"
  python test_snmp_put.py
"""
import json
import os
import urllib3

import requests

urllib3.disable_warnings()

HOST = "10.10.20.181"
USER = os.environ.get("SANDBOX_USER", "developer")
PASS = os.environ.get("SANDBOX_PASS", "C1sco12345")
BASE = f"https://{HOST}/restconf/data/Cisco-IOS-XE-native:native"
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

def put(path, payload, label):
    print("=" * 70)
    print(label)
    print("PUT", path)
    print("BODY", json.dumps(payload))
    r = requests.put(
        path, auth=(USER, PASS), headers=HEADERS,
        json=payload, verify=False, timeout=30,
    )
    print("STATUS", r.status_code)
    print("RESPONSE", r.text[:2000])
    print()
    return r

# Intento A: el actual, community-config individual
put(
    f"{BASE}/snmp-server/Cisco-IOS-XE-snmp:community-config=DEVOPS-RO",
    {"Cisco-IOS-XE-snmp:community-config": {
        "name": "DEVOPS-RO", "permission": "ro"}},
    "A: community-config individual (actual en payloads.py)",
)

# Intento B: PUT al contenedor snmp-server completo, con los 3 recursos
put(
    f"{BASE}/snmp-server",
    {"Cisco-IOS-XE-native:snmp-server": {
        "Cisco-IOS-XE-snmp:community-config": [
            {"name": "DEVOPS-RO", "permission": "ro"}],
        "Cisco-IOS-XE-snmp:location": "Lab-DevNet",
        "Cisco-IOS-XE-snmp:contact": "equipo@ejemplo.com"}},
    "B: snmp-server completo (community-config como lista)",
)

# Verificacion final
print("=" * 70)
print("GET snmp-server despues de los intentos")
r = requests.get(f"{BASE}/snmp-server", auth=(USER, PASS),
                 headers={"Accept": "application/yang-data+json"},
                 verify=False, timeout=30)
print("STATUS", r.status_code)
print("RESPONSE", r.text[:2000])
