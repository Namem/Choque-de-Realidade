import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Importando nosso motor de análise
from .circuit import parse_netlist, solve_circuit_mna

# Esta view serve a página principal com a interface
def index_view(request):
    return render(request, 'analyzer/index.html')

# Esta é a nossa nova view de API
@require_POST
def analyze_api_view(request):
    """
    Recebe uma netlist via POST, executa a análise e retorna os resultados em JSON.
    """
    try:
        # Pega o corpo da requisição (que será a string da netlist)
        data = json.loads(request.body)
        netlist_str = data.get('netlist')

        if not netlist_str:
            return JsonResponse({'error': 'A netlist não pode estar vazia.'}, status=400)

        # Executa o pipeline de análise que já testamos
        parsed_components = parse_netlist(netlist_str)
        analysis_results = solve_circuit_mna(parsed_components)
        
        # O resultado do numpy pode conter tipos que não são JSON-serializáveis por padrão.
        # Vamos converter os fasores complexos para strings para garantir.
        for key, value in analysis_results.items():
            if 'phasor' in value:
                value['phasor_str'] = f"{value['phasor'].real:.4f} + {value['phasor'].imag:.4f}j"
                del value['phasor'] # Remove o objeto complexo

        return JsonResponse({'success': True, 'results': analysis_results})

    except Exception as e:
        # Captura qualquer erro do nosso parser ou solver e retorna uma resposta de erro clara
        return JsonResponse({'error': f'Ocorreu um erro na análise: {str(e)}'}, status=400)