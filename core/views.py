from django.http.response import HttpResponse
from django.shortcuts import render
from django.http import JsonResponse
# Create your views here.
from django.views.decorators.csrf import csrf_exempt
import json
from core.utils import send_message, process_message, mensagem_Bemvindo, process_dialog, keyboard


@csrf_exempt
def event(requests):
	json_list = json.loads(requests.body)
	print(json_list)
	chat_id = json_list['message']['chat']['id']

	if 'text' not in json_list['message']:
		command = ""
	else:
		command = json_list['message']['text']

	nome = json_list['message']['chat']['first_name']
	mensagem_Bemvindo(nome, chat_id)
	#keyboard(chat_id, 'teste', contem
	output = process_message(command, chat_id)

	

	if output != "":
		send_message(output, chat_id)
		keyboard(chat_id, 'Confirmar Pedido?', '[["SIM", "NÃO"]]','true')
	else: 
		print('nada enviado !')

	return HttpResponse()
            
	