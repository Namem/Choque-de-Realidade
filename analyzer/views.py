import json
import traceback
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Importando nosso motor de análise
from .circuit import parse_netlist, solve_circuit_mna

# Esta view serve a página principal com a interface
def index_view(request):
    return render(request, 'analyzer/index.html')

# Esta é a nossa view de API, agora atualizada
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

        # 1. Executa a análise (agora retorna um dicionário mais rico)
        analysis_results = solve_circuit_mna(parse_netlist(netlist_str))

        # 2. Função auxiliar para converter fasores (números complexos) para strings
        def serialize_phasors(data_dict):
            if not isinstance(data_dict, dict):
                return data_dict
            
            # Cria uma cópia para não modificar o dicionário original durante a iteração
            serialized_dict = data_dict.copy()
            for key, value in serialized_dict.items():
                if isinstance(value, dict) and 'phasor' in value:
                    value['phasor_str'] = f"{value['phasor'].real:.4f} + {value['phasor'].imag:.4f}j"
                    del value['phasor']
            return serialized_dict

        # 3. Serializa todos os dicionários que podem conter fasores
        results_to_send = {
            'node_voltages': serialize_phasors(analysis_results.get('node_voltages', {})),
            'branch_currents': serialize_phasors(analysis_results.get('branch_currents', {})),
            'system_summary': serialize_phasors(analysis_results.get('system_summary', {})),
            'frequency': analysis_results.get('frequency', 0)
        }

        return JsonResponse({'success': True, 'results': results_to_send})

    except Exception as e:
        traceback.print_exc() # Para depuração no terminal do servidor
        return JsonResponse({'error': f'Ocorreu um erro na análise: {str(e)}'}, status=400)