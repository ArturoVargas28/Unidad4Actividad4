"""Construye los payloads YANG a partir de config/vars.yml."""
NATIVE = "Cisco-IOS-XE-native:native"


def build_items(cfg):
    lb, snmp = cfg["loopback"], cfg["snmp"]
    return [
        (
            f"{NATIVE}/interface/Loopback={lb['id']}",
            {"Cisco-IOS-XE-native:Loopback": {
                "name": lb["id"],
                "description": lb["description"],
                "ip": {"address": {"primary": {
                    "address": lb["ip"], "mask": lb["mask"]}}},
            }},
        ),
        # CORREGIDO v3 2026-11-18 para Catalyst 9300 IOS XE 17.12:
        # Revisado en el modelo YANG oficial Cisco-IOS-XE-snmp:
        # - augment "/ios:native/ios:snmp-server" usa
        #   config-snmp-server-grouping (modulo snmp, no native).
        # - list "community" esta deprecated, la vigente es
        #   "community-config" con leaf "permission" enum ro/rw.
        # Por eso el PUT a .../community=DEVOPS-RO daba 404, y tambien
        # el intento con .../snmp-server/community=... daba 404.
        # location y contact SI son del modulo snmp, se revierten ahi.
        (
            f"{NATIVE}/snmp-server/Cisco-IOS-XE-snmp:community-config={snmp['community']}",
            # v5 2026-11-18: v4 sin permission tambien dio 400
            # "inconsistent value: Device refused one or more commands".
            # Se vuelve a poner permission="ro". El problema no era
            # ese leaf, sino el PUT individual a la entrada de la lista.
            # deploy.py ahora manda los 3 de SNMP juntos en un solo
            # PUT al contenedor native (nivel superior), que es la
            # forma que funciona en CAT9K segun Cisco Community.
            {"Cisco-IOS-XE-snmp:community-config": {
                "name": snmp["community"], "permission": "ro"}},
        ),
        (
            f"{NATIVE}/snmp-server/Cisco-IOS-XE-snmp:location",
            {"Cisco-IOS-XE-snmp:location": snmp["location"]},
        ),
        (
            f"{NATIVE}/snmp-server/Cisco-IOS-XE-snmp:contact",
            {"Cisco-IOS-XE-snmp:contact": snmp["contact"]},
        ),
    ]


def is_subset(desired, current):
    """True si todo lo deseado ya existe en la configuración actual."""
    # CORREGIDO 2026-11-18: el 9300 devuelve Loopback como lista de 1
    # elemento ([{...}]), no como dict. Sin esto, deploy.py siempre dice
    # [CAMBIO] y verify.py siempre dice [FAIL] aunque ya esté bien.
    # Es el mismo bug de lista vs dict de U4ACT02.
    if isinstance(current, list):
        if isinstance(desired, list):
            return len(desired) == len(current) and all(
                is_subset(d, c) for d, c in zip(desired, current))
        return any(is_subset(desired, item) for item in current)
    if isinstance(desired, dict):
        return isinstance(current, dict) and all(
            k in current and is_subset(v, current[k]) for k, v in desired.items())
    if isinstance(desired, list):
        return isinstance(current, list) and len(desired) == len(current)
    return str(desired) == str(current)
