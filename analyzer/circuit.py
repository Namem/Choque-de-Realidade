import cmath
import numpy as np

def parse_netlist(netlist_str):
    """
    Analisa uma string de netlist e a converte em uma lista de componentes.
    Agora com suporte para TODOS os tipos de fontes controladas.
    """
    components = []
    lines = netlist_str.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('*'):
            continue
        parts = line.split()
        comp_id = parts[0]
        comp_type = comp_id[0].upper()

        try:
            if comp_type in ['R', 'L', 'C']:
                n1, n2, val = int(parts[1]), int(parts[2]), float(parts[3])
                type_map = {'R': 'Resistor', 'L': 'Inductor', 'C': 'Capacitor'}
                components.append({'id': comp_id, 'type': type_map[comp_type], 'nodes': (n1, n2), 'value': val})
            
            elif comp_type == 'V':
                n1, n2, mag, phase, freq = int(parts[1]), int(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
                phasor = cmath.rect(mag, np.deg2rad(phase))
                components.append({'id': comp_id, 'type': 'VoltageSource', 'nodes': (n1, n2), 
                                   'magnitude': mag, 'phase_deg': phase, 'frequency': freq, 'phasor': phasor})
            
            elif comp_type == 'G': # VCCS: G id n+ n- nc+ nc- ganho
                n1, n2, nc1, nc2, gain = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), float(parts[5])
                components.append({'id': comp_id, 'type': 'VCCS', 'nodes': (n1, n2), 'control_nodes': (nc1, nc2), 'gain': gain})

            elif comp_type == 'E': # VCVS: E id n+ n- nc+ nc- ganho
                n1, n2, nc1, nc2, gain = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), float(parts[5])
                components.append({'id': comp_id, 'type': 'VCVS', 'nodes': (n1, n2), 'control_nodes': (nc1, nc2), 'gain': gain})

            elif comp_type == 'F': # CCCS: F id n+ n- Vsensora ganho
                n1, n2, v_sensor_id, gain = int(parts[1]), int(parts[2]), parts[3], float(parts[4])
                components.append({'id': comp_id, 'type': 'CCCS', 'nodes': (n1, n2), 'sensor_id': v_sensor_id, 'gain': gain})
            
            elif comp_type == 'H': # CCVS: H id n+ n- Vsensora ganho
                n1, n2, v_sensor_id, gain = int(parts[1]), int(parts[2]), parts[3], float(parts[4])
                components.append({'id': comp_id, 'type': 'CCVS', 'nodes': (n1, n2), 'sensor_id': v_sensor_id, 'gain': gain})

        except (ValueError, IndexError) as e:
            raise ValueError(f"Erro ao parsear a linha '{line}': {e}")
    return components


def solve_circuit_mna(components):
    if not components: return None
    
    # Encontra frequência e define omega
    frequency = 0
    for c in components:
        if 'frequency' in c:
            frequency = c['frequency']
            break
    if frequency == 0:
        raise ValueError("Circuito precisa de pelo menos uma fonte com frequência definida.")
    omega = 2 * np.pi * frequency

    # Identifica nós e fontes que adicionam colunas/linhas à matriz (V, E, H)
    nodes = set()
    v_sources = [] 
    for comp in components:
        nodes.update(comp.get('nodes', []))
        nodes.update(comp.get('control_nodes', []))
        if comp['type'] in ['VoltageSource', 'VCVS', 'CCVS']:
            v_sources.append(comp)
    
    node_list = sorted([n for n in nodes if n != 0])
    node_map = {node: i for i, node in enumerate(node_list)}
    num_nodes = len(node_list)
    num_v_sources = len(v_sources)
    matrix_size = num_nodes + num_v_sources

    A = np.zeros((matrix_size, matrix_size), dtype=np.complex128)
    b = np.zeros(matrix_size, dtype=np.complex128)
    
    # Mapeia ID de fontes de tensão para seu índice na matriz (para F e H)
    v_source_map = {vs['id']: i for i, vs in enumerate(v_sources)}

    # Estampagem dos componentes na matriz A e vetor b
    for comp in components:
        n1, n2 = comp['nodes']
        idx1 = node_map.get(n1, -1)
        idx2 = node_map.get(n2, -1)
        comp_type = comp['type']

        if comp_type in ['Resistor', 'Inductor', 'Capacitor']:
            admittance = 0
            if comp_type == 'Resistor': admittance = 1 / comp['value']
            elif comp_type == 'Inductor': admittance = 1 / (1j * omega * comp['value'])
            elif comp_type == 'Capacitor': admittance = 1 / (1j * omega * comp['value']) if omega * comp['value'] != 0 else float('inf')
            
            if idx1 != -1: A[idx1, idx1] += admittance
            if idx2 != -1: A[idx2, idx2] += admittance
            if idx1 != -1 and idx2 != -1: A[idx1, idx2] -= admittance; A[idx2, idx1] -= admittance
        
        elif comp_type == 'VCCS':
            nc1, nc2 = comp['control_nodes']; gain = comp['gain']
            idx_c1, idx_c2 = node_map.get(nc1, -1), node_map.get(nc2, -1)
            if idx1 != -1 and idx_c1 != -1: A[idx1, idx_c1] += gain
            if idx2 != -1 and idx_c2 != -1: A[idx2, idx_c2] += gain
            if idx1 != -1 and idx_c2 != -1: A[idx1, idx_c2] -= gain
            if idx2 != -1 and idx_c1 != -1: A[idx2, idx_c1] -= gain
        
        elif comp_type == 'CCCS':
            sensor_idx = v_source_map.get(comp['sensor_id'])
            if sensor_idx is None: raise ValueError(f"Fonte sensora '{comp['sensor_id']}' não encontrada para {comp['id']}.")
            k = num_nodes + sensor_idx
            gain = comp['gain']
            if idx1 != -1: A[idx1, k] += gain
            if idx2 != -1: A[idx2, k] -= gain

        elif comp_type in ['VoltageSource', 'VCVS', 'CCVS']:
            vs_idx = v_source_map[comp['id']]
            k = num_nodes + vs_idx
            if idx1 != -1: A[k, idx1] = 1; A[idx1, k] = 1
            if idx2 != -1: A[k, idx2] = -1; A[idx2, k] = -1

            if comp_type == 'VoltageSource': b[k] = comp['phasor']
            elif comp_type == 'VCVS':
                nc1, nc2 = comp['control_nodes']; gain = comp['gain']
                idx_c1, idx_c2 = node_map.get(nc1, -1), node_map.get(nc2, -1)
                if idx_c1 != -1: A[k, idx_c1] -= gain
                if idx_c2 != -1: A[k, idx_c2] += gain
            elif comp_type == 'CCVS':
                sensor_idx = v_source_map.get(comp['sensor_id'])
                if sensor_idx is None: raise ValueError(f"Fonte sensora '{comp['sensor_id']}' não encontrada para {comp['id']}.")
                j_idx = num_nodes + sensor_idx
                gain = comp['gain']
                A[k, j_idx] -= gain

    try:
        solution = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        raise RuntimeError("Matriz singular. Verifique as conexões do circuito ou se ele está aterrado.")
    
    # --- PÓS-PROCESSAMENTO ---
    
    voltages_map = {0: 0j}
    node_voltages = {}
    for i, node_num in enumerate(node_list):
        phasor = solution[i]
        node_voltages[f'V({node_num})'] = {'phasor': phasor, 'magnitude': abs(phasor), 'phase_deg': np.rad2deg(np.angle(phasor))}
        voltages_map[node_num] = phasor

    branch_currents = {}
    for comp in components:
        comp_type = comp['type']
        if comp_type in ['VoltageSource', 'VCVS', 'CCVS']: continue
        n1, n2 = comp['nodes']
        v1, v2 = voltages_map.get(n1, 0j), voltages_map.get(n2, 0j)
        
        phasor = 0j
        if comp_type in ['Resistor', 'Inductor', 'Capacitor']:
            impedance = 0
            if comp_type == 'Resistor': impedance = comp['value']
            elif comp_type == 'Inductor': impedance = 1j * omega * comp['value']
            elif comp_type == 'Capacitor': impedance = 1 / (1j * omega * comp['value']) if omega * comp['value'] != 0 else float('inf')
            phasor = (v1 - v2) / impedance if impedance != 0 else 0j
        
        elif comp_type == 'VCCS': 
            nc1, nc2 = comp['control_nodes']
            v_control = voltages_map.get(nc1, 0j) - voltages_map.get(nc2, 0j)
            phasor = comp['gain'] * v_control
        
        elif comp_type == 'CCCS':
            sensor_idx = v_source_map.get(comp['sensor_id'])
            j_control = solution[num_nodes + sensor_idx]
            phasor = comp['gain'] * j_control

        branch_currents[f'I({comp["id"]})'] = {'phasor': phasor, 'magnitude': abs(phasor), 'phase_deg': np.rad2deg(np.angle(phasor))}

    for i, v_source in enumerate(v_sources):
        current_phasor = solution[num_nodes + i]
        branch_currents[f'I({v_source["id"]})'] = {'phasor': current_phasor, 'magnitude': abs(current_phasor), 'phase_deg': np.rad2deg(np.angle(current_phasor))}

    system_summary = {}
    main_v_source = next((c for c in components if c['type'] == 'VoltageSource'), None)
    if main_v_source:
        main_v_source_idx = v_source_map.get(main_v_source['id'])
        if main_v_source_idx is not None:
            source_current_phasor = solution[num_nodes + main_v_source_idx]
            source_voltage_phasor = main_v_source['phasor']

            if abs(source_current_phasor) > 1e-12:
                 equivalent_impedance = source_voltage_phasor / source_current_phasor
            else:
                 equivalent_impedance = complex(float('inf'), float('inf'))

            complex_power = 0.5 * source_voltage_phasor * np.conj(source_current_phasor)
            power_factor_val = np.cos(np.angle(equivalent_impedance))
            fp_lead_lag = 'atrasado (indutivo)' if np.angle(equivalent_impedance) > 0 else 'adiantado (capacitivo)'
            
            system_summary = {
                'equivalent_impedance': {'phasor': equivalent_impedance, 'magnitude': abs(equivalent_impedance), 'phase_deg': np.rad2deg(np.angle(equivalent_impedance))},
                'complex_power': {'phasor': complex_power, 'S': abs(complex_power), 'P': complex_power.real, 'Q': complex_power.imag},
                'power_factor': {'value': power_factor_val, 'type': fp_lead_lag}
            }
    
    final_results = {
        'node_voltages': node_voltages,
        'branch_currents': branch_currents,
        'system_summary': system_summary,
        'frequency': frequency
    }
    
    return final_results