#!/usr/bin/env python3
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from twocaptcha  import  TwoCaptcha
from bs4 import BeautifulSoup
sys.path.append("NumPy_path")
#import numpy as np
#import cv2
import urllib.request
import uuid
#import pdfkit
import re
import csv
import pandas as pd
from pathlib import Path
import os
import errno
import shutil
import pickle
import json
import glob
import errno
from datetime import datetime
from pytz import timezone
##Dhiogo
import boto3
import json

from elasticsearch import Elasticsearch
from elasticsearch import helpers

client = boto3.client(
    's3',
    aws_access_key_id='AKIAIZ35VVE6VAJRIZJQ',
    aws_secret_access_key='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'
)

bucketname = 'itera-fapesp-qa-contratos'

def upload_file(data, folder_path, filename):
    path = f'{folder_path}/{filename}'
    client.put_object(Body=data, Bucket=bucketname, Key=path, ACL='public-read')
    return f'https://{bucketname}.s3.amazonaws.com/{folder_path}/{filename}'
 

host='elastic.fapesp.itera.com.br'
port='9200'
username='elastic'
password='*lab.Midas@1'
url = f'{username}:{password}@{host}:{port}'  
es = Elasticsearch(hosts=url, timeout=30, max_retries=10, retry_on_timeout=True)   

try:
    import Image    
except ImportError:
    from PIL import Image
import pytesseract
from PIL import Image



def quebra_captcha_new(nome_imagen): 
    solver = TwoCaptcha('c026b1b99fa198121e1b04fb2e2daa70')
    time.sleep(1)
    result = solver.normal(nome_imagen)       
    return result
    
def create_index(index):
    es.indices.create(index=index, ignore=400)
        
def insert_one_data(_index, doc_type, data,id):
    # index and doc_type you can customize by yourself
    res = es.index(index=_index, doc_type=doc_type, id=id, body=data)
    # index will return insert info: like as created is True or False
    print(res)
    
def line_contrato(driver, row_number):

   if(row_number == 0):
      raise Exception("Row number starts from 1")
   row_number = row_number      
   rows = driver.find_elements_by_xpath("//*[@id= 'ctl00_cphContent_GdvArquivamento_gdvContent']/tbody/tr["+str(row_number)+']/td')
   print(str(row_number-1), ' pdf contrato-alteração')
   bandeira_disponivel=1 
   if rows[6].text == "INDISPONÍVEL":
       bandeira_disponivel=0
       print('..INDISPONÍVEL ')
   if rows[6].text == "NÃO DISPONÍVEL":
       bandeira_disponivel=0
       print('..NÃO DISPONÍVEL ')    
   if rows[6].text == "DISPONÍVEL":
       print('..DISPONÍVEL ')  
    
   word1='contrato_alteração'
   word='contrato_alteração'
   if rows[5].text == "DETALHES":
       detalhes = 'ctl00_cphContent_GdvArquivamento_gdvContent_ctl0'+str(row_number)+'_lnkAto'       
       hiperlink = driver.find_element_by_id(detalhes)
       hiperlink.click()
         
   src_str=rows[4].text
   sub_con_matriz = src_str.find('CONSOLIDAÇÃO CONTRATUAL DA MATRIZ')
   sub_constitucao = src_str.find('CONSTITUIÇÃO')

      
   bandeira_constitucao=0
   bandeira_cons_contratual_matriz=0        
   if sub_con_matriz  != -1:
      word='CONSOLIDACAO_CONTRATUAL_DA_MATRIZ'
      bandeira_cons_contratual_matriz=1
   if (sub_constitucao) != -1:#não encontro
        word='CONSTITUICAO'
        bandeira_constitucao=1
   if rows[4].text == "":#não encontro
        word='DOC_CONTRATO_ALT'  
   
   dicionario_contrato = {}
      # ID da divisão com dados da empresa
   id_div ='dados'
      # Parsear com BeautifulSoup
   soup = BeautifulSoup(driver.page_source, 'html.parser')
   div_dados = soup.find('div',{'id':id_div})
  
   dicionario_contrato['sessao'] = rows[1].text
   dicionario_contrato['N_registro'] = rows[2].text
   dicionario_contrato['protocolo'] = rows[3].text
   dicionario_contrato['descricao'] = rows[4].text
   dicionario_contrato['detalhes'] = rows[5].text.strip()
   dicionario_contrato['digitalizacao'] = rows[6].text


   path_Data_csv=pathJucesp+'/'+param_busca
   complete_name_csv=os.path.join( path_Data_csv, param_busca+" "+word1+'.csv')   

   df_contrato=pd.DataFrame([dicionario_contrato]) 

   
   with open(complete_name_csv, 'a') as f:
      df_contrato.to_csv(f, header=f.tell()==0) 
 
   return word, bandeira_constitucao, bandeira_cons_contratual_matriz, bandeira_disponivel, dicionario_contrato      
   


                
   
def busca_empresa(indexJucesp, index_log, param_busca, path_Data_Jucesp, path_Data_cont_cons, path_Data_con_cont_matriz, path_download, path_dir, selenium_timeout=2,espera_captcha=3):
    """
    Realiza uma busca por empresas em 'http://www.institucional.jucesp.sp.gov.br/'
    
    Argumentos:
    param_busca      -- Nome ou NIRE da empresa a ser pesquisada.
    selenium_timeout -- Valor utilizado como implicitly_wait do Selenium para aguardar carregamento 
                        de elementos da página, em segundos. Após este tempo, retorna exceção de
                        elemento não encontrado (NoSuchElementException). Pode ser aumentado para
                        evitar este erro em caso de conexão lenta.
    espera_captcha   -- Tempo para esperar o carregamento total da imagem do CAPTCHA da página, em 
                        segundos. Se for muito curto, a função de avaliar CAPTCHA pode não funcionar
                        corretamente. Usar valores maiores em conexões lentas para evitar problemas.
    Caso param_busca seja NIRE de uma empresa, retorna um dicionário com dados da empresa (ver função 
    coleta_nire)
    Caso param_busca seja um nome de empresa para busca, retorna uma lista de dicionários, contendo
    NIRE, nome e município das empresas encontradas (ver função coleta_nome)
    """


    # Configurar navegador
    chrome_options = Options()
    #chrome_options.add_argument("--headless") #Modo headless
    chrome_options.add_argument("--window-size=1920x1080") #Tamanho grande para facilitar screenshot do CAPTCHA
    #chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--log-level=3")  #Não exibir muitos logs
    chrome_options.binary_location='/usr/bin/google-chrome'  #Não exibir muitos logs
    download_dir='./'
    chrome_options.add_experimental_option('prefs',  {"download.default_directory": download_dir,
    							"download.prompt_for_download": False,
    							"download.directory_upgrade": True,
    							"plugins.always_open_pdf_externally": True
    							})
    
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options)
    
    # Configurar tempo de espera implícito do Selenium, em segundos.
    driver.implicitly_wait(selenium_timeout)
    
    # Abrir página inicial 
    driver.get('http://www.jucesponline.sp.gov.br/')
    # Abrir página de pesquisa e localizar o campo de busca
    id_busca = 'ctl00_cphContent_frmBuscaSimples_txtPalavraChave' #ID do campo de pesquisa
    busca = driver.find_element_by_id(id_busca)
    
    selenium_timeout=3
    # Efetuar busca por param_busca
    busca.send_keys(param_busca)
    busca.send_keys(Keys.ENTER)
    
    
    # Avaliar captcha automatico
    print('------QUEBRA CAPTCHA------')
    print('')
    avalia_captcha(driver,espera_captcha=4)
    
  

    # Checar se o parâmetro de busca é nome ou NIRE. Se for apenas números e com 11 dígitos, é um NIRE.
    if param_busca.isdecimal() and len(param_busca) == 11:
        resultado = coleta_nire(driver) # Definida abaixo
        #resultado =  coleta_contrato_ficha_cadastral(driver) 
    else:
        resultado = coleta_nire(driver) # Definida abaixo

    # Fechar Browser
    driver.quit()

    # Retornar resultado da busca
    return resultado
    

    

def avalia_captcha(driver,espera_captcha=2):
    """
    Captura a imagem do CAPTCHA da página, exibe na tela e solicita
    a solução ao usuário. 
    
    Argumentos:
    driver         -- Driver do Selenium que está sendo utilizado para navegar a página.
    espera_captcha --  Tempo para esperar o carregamento total da imagem do CAPTCHA da página, em 
                       segundos. Se for muito curto, a função de avaliar CAPTCHA pode não funcionar
                       corretamente. Usar valores maiores em conexões lentas para evitar problemas. 
    
    Retorna o valor fornecido pelo usuário.
    """
    
    #XPATH da imagem do captcha
    xpath_captcha = '//*[@id="formBuscaAvancada"]/table/tbody/tr[1]/td/div/div[1]/img'
    

    # Nome do campo para se digitar o captcha
    nome_campo_captcha = 'ctl00$cphContent$gdvResultadoBusca$CaptchaControl1' 
    
    # Contador de tentativas do CAPTCHA. Encerrar se superar máximo
    tentativas = 0
    max_tentativas = 5

    #Aguardar carregamento inicial da página
    time.sleep(espera_captcha)
    id_image=str(uuid.uuid4()) + ".jpg"
   
    
    # Pedir ao usuário que digite o captcha até acertar
    while tentativas < max_tentativas:
        # Tentar encontrar o elemento de captcha (figura + campo para digitar)
        try:
            captcha = driver.find_element_by_xpath(xpath_captcha)
            campo_captcha = driver.find_element_by_name(nome_campo_captcha)
            var=captcha.get_attribute("src") 
            urllib.request.urlretrieve(var, id_image)
        except NoSuchElementException:
            # Se o CAPTCHA sumir, foi resolvido. Sair da função de solução de CAPTCHA.
            return
       #    metodo quebrarcaptcha para obter o texto 
        captcha_ = quebra_captcha_new(id_image)
        print('captcha 1',captcha_['code'])   
 
        #captcha = input('Digite o captcha: ')
        #cv2.destroyAllWindows() # Fechar janela de imagem

        # Enviar o captcha no campo correto 
        campo_captcha.send_keys(captcha_['code'])
        campo_captcha.send_keys(Keys.ENTER)

        #Incrementar contador de tentativas
        tentativas += 1

        #Aguardar carregamento da página
        time.sleep(espera_captcha)

    # Encerrar processo se o máximo de tentativas for atingido
    print('Número máximo de tentativas do CAPTCHA atingido. Encerrando...')
    driver.quit()
    sys.exit(1)
    
def avalia_captcha_contrato_(driver,espera_captcha=1):
    """
    Captura a imagem do CAPTCHA da página, exibe na tela e solicita
    a solução ao usuário. 
    
    Argumentos:
    driver         -- Driver do Selenium que está sendo utilizado para navegar a página.
    espera_captcha --  Tempo para esperar o carregamento total da imagem do CAPTCHA da página, em 
                       segundos. Se for muito curto, a função de avaliar CAPTCHA pode não funcionar
                       corretamente. Usar valores maiores em conexões lentas para evitar problemas. 
    
    Retorna o valor fornecido pelo usuário.
    """
    myPath = "./Img_captcha"
    #XPATH da imagem do captcha
     
    xpath_captcha = '//*[@id="formBuscaAvancada"]/div[2]/table/tbody/tr[3]/td/div/div/img'
    

    # Nome do campo para se digitar o captcha
    ed_captcha_contrato = 'ctl00$cphContent$CaptchaControl1' 
    
    # Contador de tentativas do CAPTCHA. Encerrar se superar máximo
    tentativas = 0
    max_tentativas = 5

    #Aguardar carregamento inicial da página
    time.sleep(espera_captcha)
    id_image_="_" + str(uuid.uuid4()) + ".jpg"
    
    # Pedir ao usuário que digite o captcha até acertar
    while tentativas < max_tentativas:
        # Tentar encontrar o elemento de captcha (figura + campo para digitar)
        try:
            captcha_im_ = driver.find_element_by_xpath(xpath_captcha)
            ed_campo_captcha_contrato = driver.find_element_by_name(ed_captcha_contrato)
            var_=captcha_im_.get_attribute("src")  
            urllib.request.urlretrieve(var_, id_image_)

        except NoSuchElementException:
            # Se o CAPTCHA sumir, foi resolvido. Sair da função de solução de CAPTCHA.
            return
        captcha_1 = quebra_captcha_new(id_image_)
        print('captcha 2',captcha_1['code']) 


        # Enviar o captcha no campo correto 
        ed_campo_captcha_contrato.send_keys(captcha_1['code'])
        ed_campo_captcha_contrato.send_keys(Keys.ENTER)

        #Incrementar contador de tentativas
        tentativas += 1

        #Aguardar carregamento da página
        time.sleep(espera_captcha)

    # Encerrar processo se o máximo de tentativas for atingido
    print('Número máximo de tentativas do CAPTCHA atingido. Encerrando...')
    driver.quit()
    sys.exit(1)  
         
  
def coleta_nire(driver):    
    """
    Coletar informações só de nros NIRE onde  é fornecido como parâmetro de busca = "ltda".
    Neste caso, retorna o site da Jucesp soamente  15 dados de diferentes empresas numa tabela para.
    """            
    
    open("Nro_Nires_Bruto.txt", "w")
    contador = 0 #para 15 nires usar 1, para 30 nires usar 2, para 45 usar 3, 60 usar 4,75 usar 5, 90 usar 6, 105 usar 7, para 1000 nires usar  67, eu usei 75 75*15=1125
    while (contador < 75):
       print(contador)
       contador   = contador + 1
       campo_selecao = 'ctl00_cphContent_gdvResultadoBusca_gdvContent' 
       table = driver.find_element_by_id(campo_selecao).text

       with open("Nro_Nires_Bruto.txt", "a") as infile:
           infile.write(table)    
       botao_selecao = 'ctl00_cphContent_gdvResultadoBusca_pgrGridView_btrNext_lbtText'
       botao=driver.find_element_by_id(botao_selecao).click()
       time.sleep(2) 


    with open("Nro_Nires_Bruto.txt") as infile, open('Nro_Nires_limpo.txt', 'w') as outfile:  
    # splitlines of the content
        content = infile.read().splitlines()
        for line in content:
            if not line.strip():
                continue 
            if line and len(line) == 12:
               valor=re.sub("[^\d\.]", "",line)
               outfile.write(valor + os.linesep)
               
def wait_for_download_to_be_done( path_to_folder, file_name):
    max_time = 10
    time_counter = 0
    print("-waiting for download ", end=".pdf")
    while not os.path.exists(path_to_folder + file_name) and time_counter < max_time:
        time.sleep(1)
        time_counter += 1
        if time_counter == max_time:
            assert os.path.exists(path_to_folder + file_name), "The file wasn't downloaded"
    print("..done! time in seconds : ", str(time_counter))         
       

def wait_for_downloads(path):
    time_counter = 1
    print("--Waiting for downloads", end=".pdf")
    while any([filename.endswith(".crdownload") for filename in 
               os.listdir(path)]):
        time.sleep(1)
        time_counter +=1
        print(".", end="")
    print("time in seconds : ", str(time_counter))  
    
  
       
      
            
def coleta_csv_empresa(driver):
    """
    Coletar informações quando o NIRE da empresa é fornecido como parâmetro de busca.
    Neste caso, é retornada uma página com diversos dados da empresa.
    Argumentos:
    driver -- Driver do Selenium que está sendo utilizado para navegar a página.
    Esta função retorna um dicionário os dados da empresa, sendo suas chaves:
    'nome', 'tipo de empresa', 'início de atividade', 'cnpj', 'nire, 'data da constituição',
    'inscrição estadual', 'objeto', 'capital', 'logradouro', 'número', 'bairro', 'município', 
    'cep', 'uf'. 
    """
 
    id_div ='dados'

    # Verificar carregamento da divisão
    #if not obteve_resultados(driver,id_div):
    #    return None # Se não há resultados, retornar None.
    #    print('não carrego id_div')
   
    # Parsear com BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    div_dados = soup.find('div',{'id':id_div})

    # Dicionário vazio para resultados
    dicionario_res = {}

    # Adicionar informações ao dicionário
    dicionario_res['nome_empresa'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblEmpresa'}).get_text()
    dicionario_res['tipo_de_empresa'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblDetalhes'}).get_text()
    dicionario_res['início_de_atividade'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblAtividade'}).get_text()
    dicionario_res['cnpj'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblCnpj'}).get_text()
    dicionario_res['nire_matriz'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblNire'}).get_text()
    dicionario_res['data_da_constituicao'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblConstituicao'}).get_text()
    dicionario_res['inscricao_estadual'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblInscricao'}).get_text()
    dicionario_res['objeto'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblObjeto'}).get_text(separator='. ') 
    dicionario_res['logradouro'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblLogradouro'}).get_text()
    dicionario_res['número'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblNumero'}).get_text()
    dicionario_res['bairro'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblBairro'}).get_text()
    dicionario_res['complemento'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblComplemento'}).get_text()
    dicionario_res['município'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblMunicipio'}).get_text()
    dicionario_res['cep'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblCep'}).get_text()
    dicionario_res['uf'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblUf'}).get_text()
    # Tratamento especial para o campo 'capital'. Costuma ter diversos espaços em branco.
    dicionario_res['capital'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblCapital'}).get_text()
    dicionario_res['data_rececao_arquivo'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblEmissao'}).get_text()
    #dicionario_res['path_arquivo_empresa_csv'] = path_Data_Jucesp+param_busca+'/'+param_busca+"_dados_empresa.csv"
    
    df_empresa=pd.DataFrame([dicionario_res])
    path_Data_csv=pathJucesp+'/'+param_busca
    complete_name=os.path.join( path_Data_csv, param_busca+"_dados_empresa.csv")
    df_empresa.to_csv(complete_name, encoding="utf-8")
    dicionario_empresa=dicionario_res
    return dicionario_empresa
    
def coleta_csv_ficha_cadastral(driver):
    """
    Coletar informações quando o NIRE da empresa é fornecido como parâmetro de busca.
    Neste caso, é retornada uma página com diversos dados da empresa.
    Argumentos:
    driver -- Driver do Sedoc_type=lenium que está sendo utilizado para navegar a página.
    Esta função retorna um dicionário os dados da empresa, sendo suas chaves:
    'nome', 'tipo de empresa', 'início de atividade', 'cnpj', 'nire, 'data da constituição',
    'inscrição estadual', 'objeto', 'capital', 'logradouro', 'número', 'bairro', 'município', 
    'cep', 'uf'. 
    """
    
    id_div ='dados'
    # Parsear com BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    div_dados = soup.find('div',{'id':id_div})

    # Dicionário vazio para resultados
    dicionario_ficha_cadastral = {}                                       
    #dicionario_ficha_cadastral['nomeEmpresa'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblEmpresa'}).get_text()
    #dicionario_ficha_cadastral['nireMatriz'] = div_dados.find('span',{'id': 'ctl00_cphContent_frmPreVisualiza_lblNire'}).get_text()
    dicionario_ficha_cadastral['path_arquivo_de_fc_pdf'] = path_Data_Jucesp+'/'+param_busca+"_ficha_cadastral.pdf"


    df_contrato=pd.DataFrame([dicionario_ficha_cadastral])
    path_Data_csv=pathJucesp+'/'+param_busca
    complete_name=os.path.join( path_Data_csv, param_busca+"_ficha_cadastral.csv")
    df_contrato.to_csv(complete_name, encoding="utf-8")
    return dicionario_ficha_cadastral 
     
def coleta_csv_contrato1(driver):
    """
    Coletar informações quando o NIRE da empresa é fornecido como parâmetro de busca.
    Neste caso, é retornada uma página com diversos dados da empresa.
    Argumentos:
    driver -- Driver do Selenium que está sendo utilizado para navegar a página.
    Esta função retorna um dicionário os dados da empresa, sendo suas chaves:
    'nome', 'tipo de empresa', 'início de atividade', 'cnpj', 'nire, 'data da constituição',
    'inscrição estadual', 'objeto', 'capital', 'logradouro', 'número', 'bairro', 'município', 
    'cep', 'uf'. 
    """
    
    id_div ='dados'
    # Parsear com BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    div_dados = soup.find('div',{'id':id_div})

    # Dicionário vazio para resultados
    dicionario_contrato = {}
    dicionario_contrato['nireMatriz'] = div_dados.find('span',{'id': 'ctl00_cphContent_InfoEmpresa1_lblNire'}).get_text()
    dicionario_contrato['nomeEmpresa'] = div_dados.find('span',{'id': 'ctl00_cphContent_InfoEmpresa1_lblEmpresa'}).get_text()
    dicionario_contrato['path_arquivo'] = path_Data_Jucesp+param_busca+'/'+param_busca+"_c.csv"


    df_contrato=pd.DataFrame([dicionario_contrato])
    path_Data_csv=pathJucesp+'/'+param_busca
    complete_name=os.path.join( path_Data_csv, param_busca+"_c.csv")
    df_contrato.to_csv(complete_name, encoding="utf-8")
    return dicionario_contrato   
    
def read_table(driver):
    id_count='ctl00_cphContent_GdvArquivamento_pgrGridView_lblResultCount'    
    total=driver.find_element_by_id(id_count)
    #print('total ',total.text)
    total=int(total.text)
    id_Results='ctl00_cphContent_GdvArquivamento_pgrGridView_lblResults'    
    results=driver.find_element_by_id(id_Results)
    #print(results.text)
    parcial = results.text.replace('Mostrando 1 - ', '')
    #print('parcial', results.text)
    parcial=int(parcial)
    
    li2=total-parcial+1
    #print('total - parcial +1: ',str(li2)) 
    
                    
    
def coleta_contrato_ficha_cadastral(driver):
    """
    Coletar informações contrato_ficha_cadastral.
    Neste caso, é retornada uma página com diversos dados da empresa.
    Argumentos:
    driver -- Driver do Selenium que está sendo utilizado para navegar a página.
    Esta função retorna um dicionário os dados da empresa, sendo suas chaves:
    'nome', 'tipo de empresa', 'início de atividade', 'cnpj', 'nire, 'data da constituição',
    'inscrição estadual', 'objeto', 'capital', 'logradouro', 'número', 'bairro', 'município', 
    'cep', 'uf'. 
    """    
    time.sleep(1)
    campo_selecao = 'ctl00_cphContent_frmPreVisualiza_rblTipoDocumento_2' 
    radio = driver.find_element_by_id(campo_selecao)
    window_before_before = driver.current_window_handle
    radio.click()
    #
    
   
    # ID da divisão com dados da empresa    
    id_div ='dados'
    
    # Verificar carregamento da divisão
    if not obteve_resultados(driver,id_div):
        return None # Se não há resultados, retornar None.
        
        
    dic_empresa_=coleta_csv_empresa(driver)     
    #-------------------------                               seleçao do contrato  

    time.sleep(2)
    campo_selecao = 'ctl00_cphContent_frmPreVisualiza_rblTipoDocumento_2' 
    radio = driver.find_element_by_id(campo_selecao)
    radio.click()   
    time.sleep(2)
    
    class_button = 'btcadastro'
    window_before = driver.window_handles[0]
    button = driver.find_element_by_class_name(class_button).click()
    time.sleep(4)
    #verificar se foi para outra aba
    window_after = driver.window_handles[1] 
    
    driver.switch_to_window(window_after)
      
    
    #inserir cpf no gedit
    cpf="348.214.778-74"
    name_text = 'ctl00$cphContent$txtEmail'
    edit_cpf=driver.find_element_by_name(name_text)    
    edit_cpf.send_keys(cpf)
    
    #inserir senha no gedit
    senha="Camila1234"
    id_edit='ctl00_cphContent_txtSenha'
    edit_senha=driver.find_element_by_id(id_edit)
    edit_senha.send_keys(senha)
    
    avalia_captcha_contrato_(driver,espera_captcha=1)
    table='ctl00_cphContent_GdvArquivamento_gdvContent'
    time.sleep(4)#------------------------------------------------------------------------------------------------------------------
    print('------CONTRATOS-ALTERAÇÃO------')
    print('')
    n_row_data = driver.find_elements_by_xpath("/html/body/div[2]/form/div[3]/div[3]/div[1]/div[2]/div/table/tbody/tr")
    print('nro lines em contrato-alteração',str(len(n_row_data)-1))
    dic_empresa_['nro_contratos_alteracao'] = str(len(n_row_data)-1)
    
    read_table(driver)
    
    lista_contrato_alt=[]
    li = 2
    file_pdf='VisualizaTicket.pdf'
    while (li < len(n_row_data)+1) and (len(n_row_data)+1<11) :
       radio_id="ctl00_cphContent_GdvArquivamento_gdvContent_ctl0"+str(li)+"_rbtRow" 
       radio = driver.find_element_by_id(radio_id)
       radio.click()
       time.sleep(3)
       
       #-----------------------------------------------------------------------------------------------------------------------
       word1, bandeira_constitucao, bandeira_cons_contratual_matriz, bandeira_disponivel, dic_contrato_alt=line_contrato(driver, li)
       name_file_pdf= str(param_busca)+"_"+word1+"_"+str(li-1)+".pdf"
       name_file_constitucao=str(param_busca)+"_"+word1+"_"+str(li-1)+".pdf"
       name_file_cons_contratual_matriz=str(param_busca)+"_"+word1+".pdf"
       
       
       if bandeira_disponivel == 1:
          id_boton='ctl00_cphContent_btnContinuar'
          boton = driver.find_element_by_id(id_boton)
          boton.click()
          time.sleep(1)
          wait_for_download_to_be_done(path_download,file_pdf)
          time.sleep(0.5)   #------fazer dinamico No such file or 
             #------fazer dinamico No such file or           

          ##################
          if bandeira_cons_contratual_matriz == 1:     

             shutil.copy(os.path.join(path_download, file_pdf), os.path.join(path_dir, 'cons_contratual_matriz.pdf')) 
             if os.path.exists('cons_contratual_matriz.pdf'):
                filepath = os.path.join(path_Data_con_cont_matriz, name_file_cons_contratual_matriz)
                #print(filepath)
                os.rename('cons_contratual_matriz.pdf',filepath)      
             #with open(filepath, 'rb') as f:
             #  data = f.read()
          ##################
          if bandeira_constitucao == 1:
             shutil.copy(path_download+file_pdf,path_dir+'contitucao.pdf')
             if os.path.exists('contitucao.pdf'):
                filepath = os.path.join(path_Data_cont_cons, name_file_constitucao)
                #print(filepath)
                os.rename('contitucao.pdf',filepath)      
             #with open(filepath, 'rb') as f:
             #  data = f.read()
          ################
          time.sleep(2) 
          shutil.move(os.path.join(path_download, file_pdf), os.path.join(path_dir, file_pdf))  
          if os.path.exists('VisualizaTicket.pdf'):
             filepath = os.path.join(path_Data_Jucesp, name_file_pdf)
             os.rename('VisualizaTicket.pdf',filepath)      
             with open(filepath, 'rb') as f:
               data = f.read()
          
             complete_name_cont_alt_pdf = upload_file(data, param_busca,  name_file_pdf)         
             dic_contrato_alt['path_contrato_alteracao_pdf'] =complete_name_cont_alt_pdf
             

       lista_contrato_alt.append(dic_contrato_alt)
       window_after = driver.window_handles[1]
       li += 1     

    dic_empresa_['CONTRATO_ALTERACAO'] = lista_contrato_alt
    #---------------------------------------------------ficha cadastral 
    time.sleep(3)
    print('------FICHA CADASTRAL------')
    print('')
    driver.switch_to.window(window_before)
    id_div ='dados'
    # Verificar carregamento da divisão
    if not obteve_resultados(driver,id_div):
        return None # Se não há resultados, retornar None.
 
    campo_selecao = 'ctl00_cphContent_frmPreVisualiza_rblTipoDocumento_0'
    radio = driver.find_element_by_id(campo_selecao)
    #---------------------------------------------------------------------------------------------------------------------------
    dicionario_ficha_cadastral=coleta_csv_ficha_cadastral(driver) 
    #dic_empresa_['FICHA_CADASTRAL'] = dicionario_ficha_cadastral
    radio.click()

 
    time.sleep(1)
    id_boton='ctl00_cphContent_frmPreVisualiza_btnEmitir'
    boton = driver.find_element_by_id(id_boton)
    boton.click()
    print('ficha cadastral')
    wait_for_downloads(path_download)
    time.sleep(1)
    
    
    file_name=str(param_busca)+"_ficha_cadastral.pdf"
    complete_name_fc=os.path.join(path_Data_Jucesp, file_name)

    if os.path.exists(path_download+ file_pdf):
       filepath = os.path.join(path_Data_Jucesp, file_name)
       os.rename(path_download+"VisualizaTicket.pdf",filepath)      
       with open(filepath, 'rb') as f:
          data = f.read()          
       complete_name_fc_pdf = upload_file(data, param_busca, file_name)         
       dic_empresa_['path_fc_pdf'] =complete_name_fc_pdf 
       
   
    	
    id_cnpj=dic_empresa_['cnpj']
    print('saving cnpj: ')	
    print(id_cnpj)
    json_empresa = json.dumps(dic_empresa_) 

    #inserindo como diccionario data=dicionario_contrato
    insert_one_data(indexJucesp, doc_type='Empresa', data=json_empresa, id=id_cnpj)
    
    dicionario_log['estatus'] ='sucess'
    dicionario_log['cnpj'] =id_cnpj
    dicionario_log['error'] =''
    data_e_hora_atuais = datetime.now()
    fuso_horario = timezone('America/Sao_Paulo')
    data_e_hora_sao_paulo = data_e_hora_atuais.astimezone(fuso_horario)
    data_e_hora_sao_paulo_em_texto = data_e_hora_sao_paulo.strftime('%d/%m/%Y %H:%M')
    dicionario_log['data_recepcao'] =data_e_hora_sao_paulo_em_texto
    json_log = json.dumps(dicionario_log)       
    insert_one_data(index_log, doc_type='Log-Jucesp', data=json_log, id=param_busca)    
    
 
   
   
    


def obteve_resultados(driver, id_desejado):
    """
    Verifica se a busca teve êxito.
    Argumentos:
    driver      -- Driver do Selenium que está sendo utilizado para navegar a página.
    id_desejado -- ID do objeto desejado (tabela de resultados, página de resultados, etc) que
                   aparece uma busca com êxito.
    A verificação checa se o objeto com id 'id_desejado' foi carregado.
    Caso não seja, verifica se o ID de busca 0 resultados apareceu.
    """
    

    # Veficar se o objeto com id_desejado apareceu na página.
    try:
        # Verificar se foi encontrado
        driver.find_element_by_id(id_desejado)

        return True
    except:
        # ID desejado não encontrado! Talvez a busca não tenha encontrado resultados.

        # Verificar se apareceu a mensagem de busca sem resultados       
        id_erro = 'ctl00_cphContent_gdvResultadoBusca_qtpGridview_lblMessage' #ID da mensagem de erro de 0 resultados encontrados  
        driver.find_element_by_id(id_erro) #Dará erro de timeout em caso de perda de conexão
        print('A busca não obteve resultados. Verifique o nome ou NIRE fornecido e tente novamente.')
        return False
        
def mkdir_p(path, pasta):
    """ 'mkdir -p' in Python """
    root_path = path
    try:
        os.mkdir(os.path.join(root_path, pasta))
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            #pass sobreescreve
            shutil.rmtree(os.path.join(root_path, pasta)) #apaga          
            os.makedirs(os.path.join(root_path, pasta))#cria novo
        else:
            raise
    pathnew=str(os.path.join(root_path, pasta))         
    return pathnew 

def mkdir_p2(path, pasta):
    """ 'mkdir -p' in Python """
    
    root_path = path
    try:
        os.mkdir(os.path.join(root_path, pasta))
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass #sobreescreve

        else:
            raise
    pathnew=str(os.path.join(root_path, pasta))         
    return pathnew  

def config_Jucesp():
    global path_dir,path_download,path_downloads,pathJucesp,diretorio_cons,diretorio_con_cont_matriz
    path_dir='/home/user/Itera13agosto/'
    path_download ='/home/user/Downloads/'# fixando pasta de downloads'/home/sher/downloads'
    path_downloads = glob.glob('/home/user/Downloads/*')#removendo arquivos de '/home/sher/downloads' 
    for file in path_downloads:
       os.remove(file) 
    pathJucesp='./Pdfs_Jucesp_data_final/'
    diretorio_cons = 'contratos_constituicao' 
    diretorio_con_cont_matriz= 'consolidacao_contratual_matriz'                 

if __name__ == '__main__':
    print('----------------------------------------WEB SCRAPING CONTRATOS-ITERA(AGOSTO-2021)----------------------------')
    list_nires_errados = []
    indexJucesp = "jucesp-index1"
    create_index(indexJucesp)
    print('---Index DataSet Jucesp em kibana.fapesp.itera.com.br/: ',indexJucesp)
    index_log = "jucesp_log_index2"    
    create_index(index_log)
    print('---Logs nires baixados em kibana.fapesp.itera.com.br/ : ',index_log)
    print('---Dados e metadados em : AWS:s3 ')
    print('--------------------------------------------------------------------------------------------------------------') 

    f = open("Nro_Nires_limpo_1093.txt", "r")
    j=0
    log_nires=[]
    while(True) & (j<20):
        try:
            dicionario_log={}
            param_busca = f.readline()
            config_Jucesp()  
            if param_busca.endswith("\n") or param_busca.endswith("\r"): 
                param_busca = param_busca[:-1]
       
            diretorio = str(param_busca)
            print('-----------------------Download NIRE :-------------------')
            print(diretorio)
            horainicio=data_e_hora_atuais = datetime.now()
            print('hora_inicio Download: ',str(horainicio))
            dicionario_log['nire'] =diretorio     
            path_Data_cont_cons=mkdir_p2(pathJucesp,diretorio_cons) 
            path_Data_con_cont_matriz=mkdir_p2(pathJucesp,diretorio_con_cont_matriz)   
            path_Data_Jucesp=mkdir_p(pathJucesp,diretorio)

            resultado = busca_empresa(indexJucesp, index_log, param_busca, path_Data_Jucesp, path_Data_cont_cons, path_Data_con_cont_matriz, path_download, path_dir)     
            if resultado:
                print(resultado)   	
            j=j+1
       
        except Exception as e:
           print("Oops!", e.__class__, "------occurred.")
           j=j+1
           #excNoSuchElementException
           dicionario_log['estatus'] ='failed'
           print(type(e.__class__))
           dicionario_log['error'] =str(e.__class__)     

           data_e_hora_atuais = datetime.now()
           fuso_horario = timezone('America/Sao_Paulo')
           data_e_hora_sao_paulo = data_e_hora_atuais.astimezone(fuso_horario)
           data_e_hora_sao_paulo_em_texto = data_e_hora_sao_paulo.strftime('%d/%m/%Y %H:%M')
           dicionario_log['data_recepcao'] =data_e_hora_sao_paulo_em_texto
           json_log = json.dumps(dicionario_log)       
           insert_one_data(index_log, doc_type='Log-Jucesp', data=json_log, id=diretorio)   
           print('---------------------------------------------------- wrong!!!!!!!')
        finally:
           print('---------TIME DOWNLOAD--------------')
           print('')           
           horafin=data_e_hora_atuais = datetime.now()
           print('hora fin Download: ',str(horafin))
           time_ext=horafin-horainicio
           print('total tempo Download: ', str(time_ext))
           print('......................................................................................Sucess!')
        #log_nires.append(dicionario_log)
        
        
    f.close 
	

	
	
    
      
    
    
    
 
