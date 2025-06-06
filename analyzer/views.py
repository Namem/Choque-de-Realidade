import json
import traceback
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Importando nosso motor de análise
from .circuit import parse_netlist, solve_circuit_mna, calculate_component_impedances

# Esta view serve a página principal com a interface
def index_view(request):
    return render(request, 'analyzer/index.html')

# Esta é a nossa view de API
@require_POST
def analyze_api_view(request):
    """
    Recebe uma netlist via POST, executa a análise completa e retorna os resultados em JSON.
    """
    try:
        data = json.loads(request.body)
        netlist_str = data.get('netlist')
        if not netlist_str:
            return JsonResponse({'error': 'A netlist não pode estar vazia.'}, status=400)

        # 1. Parser + Solução MNA
        parsed_circuit = parse_netlist(netlist_str)
        analysis_results = solve_circuit_mna(parsed_circuit)

        # 2. Cálculo adicional de impedâncias e reatâncias (mantendo formas de onda funcionando)
        omega = 2 * 3.141592653589793 * analysis_results.get('frequency', 60)
        derived_calcs = calculate_component_impedances(parsed_circuit['elements'], omega)


        # 3. Serialização de fasores (para evitar problemas no JSON)
        def serialize_phasors(data_dict):
            if not isinstance(data_dict, dict):
                return data_dict
            serialized_dict = {}
            for key, value in data_dict.items():
                if isinstance(value, dict) and 'phasor' in value:
                    new_value = value.copy()
                    new_value['phasor_str'] = f"{new_value['phasor'].real:.4f} + {new_value['phasor'].imag:.4f}j"
                    del new_value['phasor']
                    serialized_dict[key] = new_value
                else:
                    serialized_dict[key] = value
            return serialized_dict

        # 4. Montagem do JSON de retorno
        results_to_send = {
            'node_voltages': serialize_phasors(analysis_results.get('node_voltages', {})),
            'branch_currents': serialize_phasors(analysis_results.get('branch_currents', {})),
            'system_summary': serialize_phasors(analysis_results.get('system_summary', {})),
            'frequency': analysis_results.get('frequency', 0),
            'derived_calculations': derived_calcs
        }

        return JsonResponse({'success': True, 'results': results_to_send})

    except Exception as e:
        traceback.print_exc()  # Log no terminal
        return JsonResponse({'error': f'Ocorreu um erro na análise: {str(e)}'}, status=400)
