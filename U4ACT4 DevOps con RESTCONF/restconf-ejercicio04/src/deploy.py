"""Aplica la configuración por RESTCONF. --check = prueba en seco."""
import argparse
import sys
import yaml
from payloads import build_items, is_subset
from restconf_client import RestconfClient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/vars.yml")
    ap.add_argument("--check", action="store_true", help="no modifica el equipo")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    client = RestconfClient(cfg["host"], cfg.get("port", 443))
    items = build_items(cfg)
    changes = 0

    # Separa Loopback (PUT individual, funciona) de SNMP.
    # SNMP: el PUT individual a community-config=DEVOPS-RO da 400
    # "inconsistent value: Device refused one or more commands"
    # en el Catalyst 9300, con y sin permission. En CAT9K la forma
    # que funciona es un solo PUT al nivel superior (/restconf/data
    # con el contenedor native completo), con los 3 recursos juntos.
    # Ver Cisco Community: "It is working by run PUT use the upper
    # tier of the API".
    snmp_pending = []
    snmp_body = {}
    for path, payload in items:
        if "/snmp-server/" not in path:
            current = client.get(path)
            if current is not None and is_subset(payload, current):
                print(f"[OK]       sin cambios  -> {path}")
                continue
            changes += 1
            if args.check:
                print(f"[CAMBIO]   se aplicaría -> {path}")
            else:
                code = client.put(path, payload)
                print(f"[APLICADO] HTTP {code}  -> {path}")
        else:
            current = client.get(path)
            if current is not None and is_subset(payload, current):
                print(f"[OK]       sin cambios  -> {path}")
                continue
            changes += 1
            snmp_pending.append((path, payload))
            # Acumula el contenido SNMP para el PUT combinado.
            for key, value in payload.items():
                # community-config va como lista en el contenedor.
                if "community-config" in key:
                    snmp_body[key] = [value]
                else:
                    snmp_body[key] = value
            if args.check:
                print(f"[CAMBIO]   se aplicaría -> {path}")

    if snmp_pending and not args.check:
        combined = {"Cisco-IOS-XE-native:native": {
            "snmp-server": snmp_body}}
        code = client.put("Cisco-IOS-XE-native:native", combined)
        for path, _payload in snmp_pending:
            print(f"[APLICADO] HTTP {code}  -> {path}")

    estado = "pendiente(s)" if args.check else "aplicado(s)"
    print(f"\nResumen: {changes} cambio(s) {estado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
