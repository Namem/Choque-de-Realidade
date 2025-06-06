import cmath
import numpy as np

# --- PARSER (DA ETAPA ANTERIOR) ---
def parse_netlist(netlist_str):
    """Analisa uma string de netlist e a converte em uma lista de componentes."""
    components = []
    lines = netlist_str.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('*'):
            continue
        parts = line.split()
        comp_id = parts[0]
        comp_type = comp_id[0].upper()
        node1, node2 = int(parts[1]), int(parts[2])

        try:
            if comp_type == 'R':
                components.append({'id': comp_id, 'type': 'Resistor', 'nodes': (node1, node2), 'value': float(parts[3])})
            elif comp_type == 'L':
                components.append({'id': comp_id, 'type': 'Inductor', 'nodes': (node1, node2), 'value': float(parts[3])})
            elif comp_type == 'C':
                components.append({'id': comp_id, 'type': 'Capacitor', 'nodes': (node1, node2), 'value': float(parts[3])})
            elif comp_type == 'V':
                magnitude, phase_deg, frequency = float(parts[3]), float(parts[4]), float(parts[5])
                phasor = cmath.rect(magnitude, np.deg2rad(phase_deg))
                components.append({'id': comp_id, 'type': 'VoltageSource', 'nodes': (node1, node2), 
                                   'magnitude': magnitude, 'phase_deg': phase_deg, 'frequency': frequency, 'phasor': phasor})
        except (ValueError, IndexError) as e:
            raise ValueError(f"Erro ao parsear a linha '{line}': {e}")
    return components

# --- NOVO MOTOR MNA ---
def solve_circuit_mna(components):
    """Resolve o circuito usando Análise Nodal Modificada (MNA) para AC."""
    if not components:
        return None

    # Encontra a frequência do circuito (assume uma única frequência) e calcula omega
    frequency = next((c['frequency'] for c in components if c['type'] == 'VoltageSource'), 0)
    if frequency == 0:
        raise ValueError("Circuito sem fonte de tensão ou frequência zero não suportado para análise AC.")
    omega = 2 * np.pi * frequency

    # Identifica o número de nós e de fontes de tensão
    nodes = set()
    voltage_sources = []
    for comp in components:
        nodes.update(comp['nodes'])
        if comp['type'] == 'VoltageSource':
            voltage_sources.append(comp)
    
    # Mapeia os números dos nós para os índices da matriz (0 a n-1)
    # Nó 0 (terra) é a referência e não entra na matriz
    node_list = sorted([n for n in nodes if n != 0])
    node_map = {node: i for i, node in enumerate(node_list)}
    num_nodes = len(node_list)
    num_vs = len(voltage_sources)
    matrix_size = num_nodes + num_vs

    # Inicializa as matrizes A e o vetor b com zeros complexos
    A = np.zeros((matrix_size, matrix_size), dtype=np.complex128)
    b = np.zeros(matrix_size, dtype=np.complex128)

    # Estampa os componentes nas matrizes
    for comp in components:
        n1, n2 = comp['nodes']
        
        # Mapeia nós para índices, tratando o nó 0 (terra)
        idx1 = node_map.get(n1, -1)
        idx2 = node_map.get(n2, -1)

        if comp['type'] == 'Resistor':
            admittance = 1 / comp['value']
        elif comp['type'] == 'Inductor':
            admittance = 1 / (1j * omega * comp['value'])
        elif comp['type'] == 'Capacitor':
            admittance = 1j * omega * comp['value']
        elif comp['type'] == 'VoltageSource':
            vs_idx = voltage_sources.index(comp)
            k = num_nodes + vs_idx
            
            if idx1 != -1: A[k, idx1] = 1; A[idx1, k] = 1
            if idx2 != -1: A[k, idx2] = -1; A[idx2, k] = -1
            b[k] = comp['phasor']
            continue # Pula para o próximo componente
        else:
            continue

        # Estampagem para componentes passivos (R, L, C)
        if idx1 != -1: A[idx1, idx1] += admittance
        if idx2 != -1: A[idx2, idx2] += admittance
        if idx1 != -1 and idx2 != -1:
            A[idx1, idx2] -= admittance
            A[idx2, idx1] -= admittance

    # Resolve o sistema de equações lineares Ax = b
    try:
        solution = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        raise RuntimeError("Matriz singular. O circuito pode estar mal definido (ex: flutuando).")
    
    # Formata os resultados
    results = {'nodes': node_list}
    for i, node_num in enumerate(node_list):
        voltage_phasor = solution[i]
        magnitude = abs(voltage_phasor)
        phase_deg = np.rad2deg(np.angle(voltage_phasor))
        results[f'V({node_num})'] = {'phasor': voltage_phasor, 'magnitude': magnitude, 'phase_deg': phase_deg}
        
    return results

# --- Bloco de Teste Atualizado ---
if __name__ == '__main__':
    example_netlist = """
* Exemplo de Circuito RLC Série
VS 1 0 120 0 60
R1 1 2 10
L1 2 3 0.05
C1 3 0 0.0001
    """
    print("--- 1. Testando o Parser ---")
    parsed_components = parse_netlist(example_netlist)
    print("Componentes parseados com sucesso.")
    
    print("\n--- 2. Testando a Solução MNA ---")
    analysis_results = solve_circuit_mna(parsed_components)
    
    if analysis_results:
        print("Solução encontrada:")
        for key, value in analysis_results.items():
            if key != 'nodes':
                print(f"{key}: Magnitude = {value['magnitude']:.4f} V, Fase = {value['phase_deg']:.4f}°")