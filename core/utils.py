# - *- coding: utf- 8 - *-
import requests
import csv
import spacy
import re
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.naive_bayes import GaussianNB
from datetime import datetime
from core.models import Interaction
from django.core.exceptions import ObjectDoesNotExist

nlp = spacy.load('pt')
nlp2 = spacy.load('/workspace/my-chatbot/pedidos.md')


now = datetime.now()

TOKEN = 'token'

chave = {}

tabela = {
    'PIZZA' : { 'GRANDE' : {'BACON' : 20.00, 'CALABRESA' : 20.00, 'TOSCANA' : 20.00},
                'MEDIA' : {'BACON' : 15.00, 'CALABRESA' : 15.00, 'TOSCANA' : 15.00},
                'PEQUENA' : {'BACON' : 12.00, 'CALABRESA' : 12.00, 'TOSCANA' : 12.00}
              },
              
    'LANCHE' : {'X-BURGER' : 4.00, 'X-SALADA' : 6.00, 'X-FRANGO' : 6.00, 'X-BACON' : 7.00},

    'BEBIDA' : {'SUCO' : {'LARANJA' : 3.00, 'GOIABA' : 3.00, 'ACEROLA' : 3.00},
                'REFRIGERANTE' : {'SODA 2L' : 5.00, 'COCA-COLA 2L' : 6.00, 'GUARANÁ 2L' : 6.00}
               }
         }

def tokenize(text):
    # obtains tokens with a least 1 alphabet
    pattern = re.compile(r'[A-Za-z]+[\w^\']*|[\w^\']*[A-Za-z]+[\w^\']*')
    return pattern.findall(text.lower())

def mapping(tokens):
    word_to_id = dict()
    id_to_word = dict()

    for i, token in enumerate(set(tokens)):
        word_to_id[token] = i
        id_to_word[i] = token

    return word_to_id, id_to_word

def generate_test_data(tokens, word_to_id):
    pattern = [0] * len(word_to_id)

    for token in tokens:
        if token in word_to_id.keys():
            pattern[ word_to_id[token] ] = 1

    return pattern

def generate_training_data(tokens, word_to_id, window_size):
    N = len(tokens)
    X, Y = [], []

    for i in range(N):
        nbr_inds = list(range(max(0, i - window_size), i)) + \
                   list(range(i + 1, min(N, i + window_size + 1)))
        for j in nbr_inds:
            X.append(word_to_id[tokens[i]])
            Y.append(word_to_id[tokens[j]])
            
    X = np.array(X)
    X = np.expand_dims(X, axis=0)
    Y = np.array(Y)
    Y = np.expand_dims(Y, axis=0)

    return X, Y

def extrair_tokens(comando):
    doc = nlp(comando.lower())
    extract = lambda token : token.lemma_ if token.pos_ == 'VERB' else token.orth_
    tokens = set([extract(token) for token in doc])

    return list(tokens)

def mensagem_Bemvindo(nome, chat_id):
    global chave

    url = 'https://api.telegram.org/bot%s/sendMessage' % (TOKEN)
    saudia = ('Olá {}, Bom Dia ! Bem vindo ao Bot'.format(nome))
    sautard = ('Olá {}, Boa Tarde ! Bem vindo ao Bot'.format(nome))
    saunoit = ('Olá {}, Boa Noite ! Bem vindo ao Bot'.format(nome))
    hora = now.hour - 3
    minutos = now.minute
    if hora == 0 and minutos == 0:
        chave = {}
    else:
        if chat_id not in chave:
            if hora >= 6 and hora < 12:
                saud = {'chat_id':chat_id, 'text':saudia}
                response = requests.post(url, data=saud)
            elif hora >= 12 and hora < 18:
                saud = {'chat_id':chat_id, 'text':sautard}
                response = requests.post(url, data=saud)
            elif hora >= 18 and hora < 24 or hora >= 0 and hora < 6:
                saud = {'chat_id':chat_id, 'text':saunoit}
                response = requests.post(url, data=saud)
            chave[chat_id] = None

    print('usuario {} ja saudado!'.format(nome))

def process_dialog(comando):
    lista1 = []
    lista2 = []

    with open('dialogo.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=';')
        for coluna in spamreader:
            lista1 += [coluna[0]]
            lista2 += [coluna[1]]


    string2 = ', '.join(lista2)
    string1 = ', '.join(lista1)
    # extrair os tokens :)
    tokens = extrair_tokens(string1)

    word_to_id, id_to_word = mapping(tokens)

    tokens_frase = extrair_tokens(comando)

    Xt = generate_test_data(tokens_frase, word_to_id)

    le = LabelEncoder()
    L2 = le.fit(lista2).transform(lista2)


    clf = GaussianNB()

    X = [generate_test_data(extrair_tokens(comando), word_to_id) for comando in lista1]


    clf.fit(X, L2)

    tokens_frase = extrair_tokens(comando)

    Xt = generate_test_data(tokens_frase, word_to_id)
    saida = clf.predict(np.asarray(Xt).reshape(1, -1))
    proc = ''.join(le.inverse_transform(saida))

    return proc 

def process_message(command, chat_id):
    print('processando mensagem...')
    registro = []
    if command != "":
        comando = command.lower()
        chaveS = process_dialog(comando)
        print(chaveS)
        if chaveS == 'PEDIDO':
            df = []
            ldf = []
            comprovante = ''
            send_message('Processando pedido...', chat_id)
            registro = carrinho_compras(chat_id, command)
            i = 0
            while i < len(registro):
                df.append(pd.DataFrame(list(registro[i].items())))
                i = i + 1
            i = 0
            while i < len(df):
                ldf.append(df[i].to_string(index=False, header=False, justify='start'))
                comprovante += ldf[i] + ','
                i = i + 1
            comprovante = comprovante.replace(" ", "")
            comprovante = comprovante.replace(":", ":  ")
            comprovante = comprovante.replace(",", "\n\n")
            print(comprovante)

            output = comprovante
        else:
            print('(Key = ("text" não existe !)')

    return output

def send_message(text, chat_id):
        url = 'https://api.telegram.org/bot%s/sendMessage' % (TOKEN)
        data = {'chat_id':chat_id, 'text':text}
        print(url)
        print(data)
        response = requests.post(url, data=data)
        print(response.content)
        
# Adicionar botões: https://api.telegram.org/bot940961290:AAFE7aPlyzmTin7Nw_J9QbGLzXR85WrWlJA/sendMessage?chat_id=984283322&text=Choose&reply_markup={"keyboard":[["ultimo"]],"resize_keyboard":true}

def keyboard(chat_id, msg, buttons, resize):
    buttons_keyboard = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&reply_markup={"keyboard":%s,"resize_keyboard":%s}' % (TOKEN, chat_id, msg, buttons, resize)
    resp = requests.post(buttons_keyboard)

def send_location(chat_id, msg, buttons):
    key_local = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&reply_markup={"keyboard":%s},"request_location":true' % (TOKEN, chat_id, msg, buttons)
    lcal = requests.post(key_local)
    #https://api.telegram.org/bot940961290:AAFE7aPlyzmTin7Nw_J9QbGLzXR85WrWlJA/sendMessage?chat_id=984283322&text=Choose&reply_markup={"keyboard":[[{"text":"Enviar Localização","request_location":true}]]}

def process_keys(msg):
    x = msg
    doc2 = nlp2(x)
    k = [(entity.label_) for entity in doc2.ents]
    return k

def process_cont(msg):
    x = msg
    doc2 = nlp2(x)
    c = [(entity) for entity in doc2.ents]
    return c

def pizzas(tipo, subtipo, sabor, quantidade):
    compras = []
    if(subtipo in tabela[tipo] and tipo == 'PIZZA'):
        if(sabor in tabela[tipo][subtipo]):
            preco = tabela[tipo][subtipo][sabor] * quantidade
            compras.append({
            'Produto:':tipo,
            'Tamanho:':subtipo,
            'Sabor:':sabor,
            'Quantidade:':quantidade,
            'Preço:R$':preco
            })
        else:
            compras.append({})
    return compras

def bebidas(tipo, subtipo, sabor, quantidade):
    compras = []
    if(subtipo in tabela[tipo] and tipo == 'BEBIDA'):
        if(sabor in tabela[tipo][subtipo]):
            preco = tabela[tipo][subtipo][sabor] * quantidade
            compras.append({
            "Produto:":tipo,
            "Opção:":subtipo,
            "Sabor:":sabor,
            "Quantidade:":quantidade,
            "Preço:R$":preco
            })
        else:
            compras.append({}) 
    return compras

def lanches(tipo, sabor, quantidade):
    compras = []
    if(sabor in tabela[tipo] and tipo == 'LANCHE'):
        preco = tabela[tipo][sabor]
        compras.append({
        "Produto:":tipo,
        "Sabor:":sabor,
        "Quantidade:":quantidade,
        "Preço:R$":preco
        })
    else:
        compras.append({})
    return compras

def carrinho_compras(chat_id, command):
    compras = []

    contmsg = process_cont(command)
    keymsg = process_keys(command)

    while(len(keymsg) > 0):
        tipo = ''
        subtipo = ''
        opcoes = ''
        sabor = ''
        quantidade = 0

        if 'QUANTIDADE' in keymsg and keymsg.index('QUANTIDADE') == 0 or 'SUBTIPO' in keymsg and keymsg.index('SUBTIPO') == 0:
            if 'UMA' in str(contmsg[keymsg.index('QUANTIDADE')]).upper() or 'UM' in str(contmsg[keymsg.index('QUANTIDADE')]).upper():
                quantidade = 1
                idx = keymsg.index('QUANTIDADE')
                del(keymsg[idx], contmsg[idx])
            elif 'DUAS' in str(contmsg[keymsg.index('QUANTIDADE')]).upper() or 'DOIS' in str(contmsg[keymsg.index('QUANTIDADE')]).upper():
                quantidade = 2
                idx = keymsg.index('QUANTIDADE')
                del(keymsg[idx], contmsg[idx])
            elif 'TRES' in str(contmsg[keymsg.index('QUANTIDADE')]).upper() or 'TRÊS' in str(contmsg[keymsg.index('QUANTIDADE')]).upper():
                quantidade = 3
                idx = keymsg.index('QUANTIDADE')
                del(keymsg[idx], contmsg[idx])
            elif 'QUATRO' in str(contmsg[keymsg.index('QUANTIDADE')]).upper():
                quantidade = 4
                idx = keymsg.index('QUANTIDADE')
                del(keymsg[idx], contmsg[idx])
            elif 'CINCO' in str(contmsg[keymsg.index('QUANTIDADE')]).upper():
                quantidade = 5
                idx = keymsg.index('QUANTIDADE')
                del(keymsg[idx], contmsg[idx])

        if 'PIZZA' in keymsg or 'LANCHE' in keymsg or 'SUBTIPO' in keymsg:

            if 'LANCHE' in keymsg and keymsg.index('LANCHE') == 0:
                tipo = 'LANCHE'
                sabor = str(contmsg[keymsg.index('LANCHE')]).upper()
                idx = keymsg.index('LANCHE')
                del(keymsg[idx], contmsg[idx])

            if 'PIZZA' in keymsg and keymsg.index('PIZZA') == 0:
                tipo = 'PIZZA'
                idx = keymsg.index('PIZZA')
                del(keymsg[idx], contmsg[idx])

            if 'SUBTIPO' in keymsg and keymsg.index('SUBTIPO') == 0:
                if str(contmsg[keymsg.index('SUBTIPO')]).upper() == 'SUCO' or str(contmsg[keymsg.index('SUBTIPO')]).upper() == 'SUCOS':
                    tipo = 'BEBIDA'
                    subtipo = 'SUCO'
                    idx = keymsg.index('SUBTIPO')
                    del(keymsg[idx], contmsg[idx])

                else:
                    subtipo = str(contmsg[keymsg.index('SUBTIPO')]).upper()
                    idx = keymsg.index('SUBTIPO')
                    del(keymsg[idx], contmsg[idx])

            if 'REFRIGERANTE' in keymsg and keymsg.index('REFRIGERANTE') == 0:
                tipo = 'BEBIDA'
                subtipo = 'REFRIGERANTE'
                sabor = str(contmsg[keymsg.index('REFRIGERANTE')]).upper()
                idx = keymsg.index('REFRIGERANTE')
                del(keymsg[idx], contmsg[idx])

            if 'SABOR' in keymsg and keymsg.index('SABOR') == 0:
                sabor = str(contmsg[keymsg.index('SABOR')]).upper()
                idx = keymsg.index('SABOR')
                del(keymsg[idx], contmsg[idx])

        if(tipo == 'PIZZA'):
            compras += pizzas(tipo, subtipo, sabor, quantidade)
        elif(tipo == 'LANCHE'):
            compras += lanches(tipo, sabor, quantidade)
        elif(tipo == 'BEBIDA'):
            compras += bebidas(tipo, subtipo, sabor, quantidade) 
        elif tipo == '':
            keymsg = []           
        
    print('\n\n',compras,'\n\n')
    return compras


#########Funçao para solicitar localização do cliente##########
'''
def solicitarLocalizacao(msg)
location_keyboard = telegram.KeyboardButton ( text = " send_location " , request_location = True )
contact_keyboard = telegram.KeyboardButton ( text = " send_contact " , request_contact = True )
custom_keyboard = [[location_keyboard, contact_keyboard]]
reply_markup = telegram.ReplyKeyboardMarkup (custom_keyboard)
bot.send_message ( chat_id = chat_id, 
text = " Você gostaria de compartilhar sua localização e entrar em contato comigo? " , 
reply_markup = reply_markup)
'''
#----------------------------------------------------------------------------------------------------------#
