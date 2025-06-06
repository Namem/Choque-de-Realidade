import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Importando nosso motor de análise
from .circuit import parse_netlist, solve_circuit_mna

# Esta view serve a página principal com a interface
def index_view(request):
    return render(request, 'analyzer/index.html')

# Esta é a nossa view de API
@require_POST
def analyze_api_view(request):
    """
    Recebe uma netlist via POST, executa a análise e retorna os resultados em JSON.
    """
    try:
        data = json.loads(request.body)
        netlist_str = data.get('netlist')

        if not netlist_str:
            return JsonResponse({'error': 'A netlist não pode estar vazia.'}, status=400)

        parsed_components = parse_netlist(netlist_str)
        analysis_results = solve_circuit_mna(parsed_components)
        
        # --- CORREÇÃO APLICADA AQUI ---
        # Itera sobre os resultados para converter tipos de dados não-JSON
        for key, value in analysis_results.items():
            # Apenas tenta processar o valor se ele for um dicionário (ignorando 'frequency' e 'nodes')
            if isinstance(value, dict) and 'phasor' in value:
                value['phasor_str'] = f"{value['phasor'].real:.4f} + {value['phasor'].imag:.4f}j"
                del value['phasor'] # Remove o objeto complexo que não é serializável

        return JsonResponse({'success': True, 'results': analysis_results})

    except Exception as e:
        # Captura qualquer erro do nosso parser ou solver e retorna uma resposta de erro clara
        return JsonResponse({'error': f"Ocorreu um erro na análise: {str(e)}"}, status=400)