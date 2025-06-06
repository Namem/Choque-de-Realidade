import cmath
import math
from collections import defaultdict

def parse_netlist(netlist_str):
    lines = netlist_str.strip().splitlines()
    elements = []
    frequency = 60  # padrão se não for informado

    for line in lines:
        line = line.strip()
        if not line or line.startswith('*'):
            continue
        parts = line.split()
        kind = parts[0][0].upper()

        if kind == 'V':  # Fonte de tensão senoidal
            name, n1, n2, magnitude, phase, freq = parts
            elements.append({
                'type': 'VS',
                'name': name,
                'n1': int(n1),
                'n2': int(n2),
                'value': float(magnitude),
                'phase': float(phase),
            })
            frequency = float(freq)
        elif kind == 'I':  # Fonte de corrente senoidal
            name, n1, n2, magnitude, phase, freq = parts
            elements.append({
                'type': 'IS',
                'name': name,
                'n1': int(n1),
                'n2': int(n2),
                'value': float(magnitude),
                'phase': float(phase),
            })
            frequency = float(freq)
        elif kind == 'R':
            name, n1, n2, value = parts
            elements.append({
                'type': 'R',
                'name': name,
                'n1': int(n1),
                'n2': int(n2),
                'value': float(value)
            })
        elif kind == 'L':
            name, n1, n2, value = parts
            elements.append({
                'type': 'L',
                'name': name,
                'n1': int(n1),
                'n2': int(n2),
                'value': float(value)
            })
        elif kind == 'C':
            name, n1, n2, value = parts
            elements.append({
                'type': 'C',
                'name': name,
                'n1': int(n1),
                'n2': int(n2),
                'value': float(value)
            })

    return {'frequency': frequency, 'elements': elements}

def solve_circuit_mna(netlist_data):
    freq = netlist_data['frequency']
    omega = 2 * math.pi * freq
    elements = netlist_data['elements']

    # Lista de nós
    node_set = set()
    for e in elements:
        node_set.add(e['n1'])
        node_set.add(e['n2'])
    node_list = sorted(node_set - {0})  # exceto terra
    node_index = {node: idx for idx, node in enumerate(node_list)}

    N = len(node_list)
    M = sum(1 for e in elements if e['type'] in ['VS', 'IS'])  # número de fontes
    size = N + M

    import numpy as np
    A = np.zeros((size, size), dtype=complex)
    z = np.zeros(size, dtype=complex)

    voltage_sources = []
    vs_count = 0
    source_index = {}

    for e in elements:
        n1 = node_index.get(e['n1'], -1)
        n2 = node_index.get(e['n2'], -1)

        if e['type'] == 'R':
            value = e['value']
            admittance = 1 / value
            if n1 != -1: A[n1, n1] += admittance
            if n2 != -1: A[n2, n2] += admittance
            if n1 != -1 and n2 != -1:
                A[n1, n2] -= admittance
                A[n2, n1] -= admittance

        elif e['type'] == 'L':
            value = e['value']
            impedance = complex(0, omega * value)
            admittance = 1 / impedance
            if n1 != -1: A[n1, n1] += admittance
            if n2 != -1: A[n2, n2] += admittance
            if n1 != -1 and n2 != -1:
                A[n1, n2] -= admittance
                A[n2, n1] -= admittance

        elif e['type'] == 'C':
            value = e['value']
            impedance = complex(0, -1 / (omega * value))
            admittance = 1 / impedance
            if n1 != -1: A[n1, n1] += admittance
            if n2 != -1: A[n2, n2] += admittance
            if n1 != -1 and n2 != -1:
                A[n1, n2] -= admittance
                A[n2, n1] -= admittance

        elif e['type'] == 'IS':
            phasor = cmath.rect(e['value'], math.radians(e['phase']))
            if n1 != -1: z[n1] -= phasor
            if n2 != -1: z[n2] += phasor

        elif e['type'] == 'VS':
            idx = N + vs_count
            source_index[e['name']] = idx
            phasor = cmath.rect(e['value'], math.radians(e['phase']))
            if n1 != -1:
                A[idx, n1] = 1
                A[n1, idx] = 1
            if n2 != -1:
                A[idx, n2] = -1
                A[n2, idx] = -1
            z[idx] = phasor
            vs_count += 1
            voltage_sources.append((e['name'], n1, n2, phasor))

    x = np.linalg.solve(A, z)

    voltages = {}
    for node, idx in node_index.items():
        v = x[idx]
        voltages[f"V({node})"] = {
            'phasor': v,
            'magnitude': abs(v),
            'phase_deg': math.degrees(cmath.phase(v))
        }

    currents = {}
    for e in elements:
        if e['type'] in ['R', 'L', 'C']:
            n1 = node_index.get(e['n1'], -1)
            n2 = node_index.get(e['n2'], -1)
            v1 = x[n1] if n1 != -1 else 0
            v2 = x[n2] if n2 != -1 else 0
            vdiff = v1 - v2
            if e['type'] == 'R':
                i = vdiff / e['value']
            elif e['type'] == 'L':
                i = vdiff / (complex(0, omega * e['value']))
            elif e['type'] == 'C':
                i = vdiff / (complex(0, -1 / (omega * e['value'])))
            currents[f"I({e['name']})"] = {
                'phasor': i,
                'magnitude': abs(i),
                'phase_deg': math.degrees(cmath.phase(i))
            }

    for name, n1, n2, phasor in voltage_sources:
        currents[f"I({name})"] = {
            'phasor': -phasor / voltages[f"V({n1})"]['phasor'] if n1 in node_index else 0,
            'magnitude': abs(-phasor / voltages[f"V({n1})"]['phasor']) if n1 in node_index else 0,
            'phase_deg': math.degrees(cmath.phase(-phasor / voltages[f"V({n1})"]['phasor'])) if n1 in node_index else 0,
        }

    # Impedância equivalente, potências, fator de potência
    Vtotal = next((v['phasor'] for k, v in voltages.items() if k == "V(1)"), 0)
    Itotal = next((i['phasor'] for k, i in currents.items() if k == "I(VS)"), 0)
    Zeq = Vtotal / Itotal if Itotal != 0 else 0
    S = Vtotal * Itotal.conjugate()
    P = S.real
    Q = S.imag
    FP = P / abs(S) if abs(S) > 0 else 0
    FP_type = "atrasado (indutivo)" if Q > 0 else "adiantado (capacitivo)" if Q < 0 else "unitário"

    return {
        'node_voltages': voltages,
        'branch_currents': currents,
        'frequency': freq,
        'system_summary': {
            'equivalent_impedance': {
                'phasor': Zeq,
                'magnitude': abs(Zeq),
                'phase_deg': math.degrees(cmath.phase(Zeq)),
            },
            'complex_power': {
                'S': abs(S),
                'P': P,
                'Q': Q,
                'phasor': S
            },
            'power_factor': {
                'value': FP,
                'type': FP_type
            }
        },
        'derived_calculations': calculate_component_impedances(elements, omega)
    }

def calculate_component_impedances(elements, omega):
    results = []
    for e in elements:
        if e['type'] == 'R':
            z = complex(e['value'], 0)
            results.append({
                'id': e['name'],
                'type': 'Resistor',
                'value': e['value'],
                'impedance_rect': f"{z.real:.2f} + j{z.imag:.2f}",
                'impedance_polar': f"{abs(z):.2f} ∠ {math.degrees(cmath.phase(z)):.2f}°"
            })
        elif e['type'] == 'L':
            xl = omega * e['value']
            z = complex(0, xl)
            results.append({
                'id': e['name'],
                'type': 'Inductor',
                'value': e['value'],
                'reactance': xl,
                'impedance_rect': f"{z.real:.2f} + j{z.imag:.2f}",
                'impedance_polar': f"{abs(z):.2f} ∠ {math.degrees(cmath.phase(z)):.2f}°"
            })
        elif e['type'] == 'C':
            xc = 1 / (omega * e['value'])
            z = complex(0, -xc)
            results.append({
                'id': e['name'],
                'type': 'Capacitor',
                'value': e['value'],
                'reactance': xc,
                'impedance_rect': f"{z.real:.2f} + j{z.imag:.2f}",
                'impedance_polar': f"{abs(z):.2f} ∠ {math.degrees(cmath.phase(z)):.2f}°"
            })
    return results
