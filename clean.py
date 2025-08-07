#!/usr/bin/python3
# -*- coding: utf-8 -*-

#############################################################
##                                                         ##
## Autor: Douglas Rodrigues                                ##
## Email: douglas.rodrigues@tripleplay.network             ##
##                                                         ##
## Script para limpeza automatica de ONUs em OLTs Huawei   ##
##                                                         ##
#############################################################

import time
import telnetlib
import sys
import re
from datetime import datetime

pons = []
totalOfflineBefore = 0
totalOfflineAfter = 0
tempoEstimado = 0
tempoTotal= 0
segundos_por_onu = 8

def ListPonsAndGetNumberOfOfflineOnts(tn):
    tn.write(b"display ont info 0 all\n")
    time.sleep(20)

    return_pon_informartion = tn.read_until(
        'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()

    for linha in return_pon_informartion:
        if "In port " in linha:
            pon = linha.split(',')[0].replace('In port', '').replace(' ', '')
            onlineNumber = int(linha.split(',')[2].split(':')[
                               1].replace(' ', ''))
            provisionedNumber = int(linha.split(
                ',')[1].split(':')[1].replace(' ', ''))
            offlineNumber = provisionedNumber-onlineNumber
            pons.append({'pon': pon, 'offline': offlineNumber})


def ConvertStringToTimestamp(str_date):
    formatos_possiveis = [
        '%Y-%m-%d %H:%M:%S',     # ex: 2025-08-06 14:22:00
        '%d-%m-%Y %H:%M:%S',     # ex: 06-08-2025 14:22:00
        '%Y/%m/%d %H:%M:%S',     # ex: 2025/08/06 14:22:00
        '%d/%m/%Y %H:%M:%S',     # ex: 06/08/2025 14:22:00
        #'%Y-%m-%d',              # ex: 2025-08-06
        #'%d-%m-%Y',              # ex: 06-08-2025
        #'%Y/%m/%d',              # ex: 2025/08/06
        #'%d/%m/%Y',              # ex: 06/08/2025
    ]

    for formato in formatos_possiveis:
        try:
            datetime_object = datetime.strptime(str_date, formato)
            return int(datetime_object.timestamp())
        except ValueError:
            continue

    print(f"[ERRO] Não foi possível converter a data '{str_date}' para timestamp. Formato inválido.")
    exit()



def GetActualDateTime(tn):
    try:
        tn.write(b"display time\n")
        time.sleep(.3)

        return_clock_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_clock_information:
            if re.search(r'[0-9]+\-[0-9]+\-[0-9]+.[0-9]+:[0-9]+:[0-9]+.[0-9]+:[0-9]+', linha) and not re.search(r'[A-Za-z]', linha):
                actualDate = re.sub(r'.[0-9]+:[0-9]+$',"",linha)
        return re.sub(r"^\s+", "", actualDate)
    except Exception as e:
        print("[ERRO] Não foi possivel obter a data atual da OLT")
        exit()

def GetDateTimeOfONT(tn, sn):
    timestampOfOnu = 837849918
    print("")
    print(f"[INFO] Verificando ONU {sn}")
    tn.write(
        f"display ont info by-sn {sn}\n".encode('utf-8'))
    time.sleep(5)
  

    return_ont_information = tn.read_until(
        'Tr069'.encode('utf-8'), 3).decode('utf-8').splitlines()
    

    for linha in return_ont_information:

        if "down time" in linha:
            linhatratada = linha.split(':')[1]
            print("[INFO] Horario da Ultima queda:", linhatratada)
            
            if re.search(r'[0-9]+\-[0-9]+\-[0-9]+.[0-9]+:[0-9]+:[0-9]+.[0-9]+:[0-9]+', linha):
                dateStringUtc = re.sub(r'.+:\s', "", linha)
                dateString = re.sub(r'.[0-9]+:[0-9]+$', "", dateStringUtc)
                timestampOfOnu = ConvertStringToTimestamp(dateString)
                
        
    return timestampOfOnu


def GetListOfOfflineONT(tn, pon=str):
    try:
        ponStriped = pon.split('/')
        onusOffline = []

        tn.write(
            f"display ont info {ponStriped[0]} {ponStriped[1]} {ponStriped[2]} all\n".encode('utf-8'))
        time.sleep(3)

        return_ont_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_ont_information:
            if 'offline' in linha:
                offline_str = re.sub(r'0/\s', '0/', linha)
                onusOffline.append(re.sub(r'\s+', ";", offline_str).split(';')[3])
        # print(onusOffline)
        return onusOffline
    except Exception as e:
        print(f"[ERRO] Não Foi possivel obter as ONUs Offline da PON {pon}")
        return onusOffline


def GetUptimeOfOLT(tn):
    uptimeInDays = 0

    try:

        tn.write("display version\n".encode('utf-8'))
 
        time.sleep(3)


        return_uptime_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        
        for linha in return_uptime_information:
            if re.search(r'[Uu]ptime', linha):
                # print(linha)
                # Remove espacos iniciais, separa em um array e pega o valor de dias
                uptimeInDays = int(re.sub(r"^\s+", "", linha).split(' ')[2])
        if uptimeInDays < 10:
            print(f"[WARN] A OLT está ligada há {uptimeInDays} dias.")
            print("[ERRO] O Uptime da OLT é menor que 10 dias, o script foi interrompido.")
            exit()
        else:
            print(f"[INFO] A OLT está ligada há {uptimeInDays} dias.")
            return uptimeInDays
    except Exception as e:
        print("[ERRO] Não Foi possivel obter o Uptime da OLT")
        print(e)
        exit()


def DeleteServicePortAndOnt(tn, sn):
    ontId = str
    fsp = str
    srvPort = str

    try:
        tn.write(f"display ont info by-sn {sn}\n".encode('utf-8'))
        time.sleep(1)

        return_ont_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_ont_information:
            if "F/S/P" in linha:
                fsp = linha.split(":")[1].replace(" ", "")
            if "ONT-ID" in linha:
                ontId = linha.split(":")[1].replace(" ", "")

        fspSplited = fsp.split('/')

        tn.write(
            f"display service-port port {fsp} ont {ontId}\n".encode('utf-8'))
        time.sleep(1)

        return_serviceport_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()

        for linhaService in return_serviceport_information:
            if "gpon" in linhaService:
                srvPort = re.sub(r'^\s+', "", linhaService).split(" ")[0]
                tn.write(f"undo service-port {srvPort}\n".encode('utf-8'))
                time.sleep(.5)

        tn.write(f"interface gpon 0/{fspSplited[1]}\n".encode('utf-8'))
        time.sleep(.5)
        tn.write(f"ont delete {fspSplited[2]} {ontId}\n".encode('utf-8'))
        time.sleep(.5)

        tn.write(f"quit\n".encode('utf-8'))
        time.sleep(.5)

        print(f"[INFO] Sucesso! - ONU Excluida - SN: {sn}")
        print("")
        print("Lavínia não faz nada, mas apagou mais uma ONU! ❤️")
        print("")
        return

    except Exception as e:
        print(f"[ERRO] Falha! - Erro ao excluir ONU - SN: {sn}")
        return


def ConnectOnOLTWithTelnet(ip, user, password, port, totalOfflineBefore, totalOfflineAfter):
    inicio = time.time()
    try:
        tn = telnetlib.Telnet(ip, port, timeout=10)
    except Exception as e:
        print(f"[ERRO] Falha ao conectar na OLT {ip}:{port} - {e}")
        fim = time.time()
        tempoTotal = int(fim - inicio)
        minutos_totais = tempoTotal // 60
        segundos_totais = tempoTotal % 60
        print(f"[INFO] Tempo total de execução: {minutos_totais} min {segundos_totais} seg")
        return

    # tn.set_debuglevel(100)
    
    try:
        # Login na OLT
        tn.read_until(b"name:", timeout=5)
        tn.write(user.encode('utf-8') + b"\n")
        time.sleep(0.3)

        tn.read_until(b"password:", timeout=5)
        tn.write(password.encode('utf-8') + b"\n")
        time.sleep(0.3)

        # Entra no modo de configuração
        comandos_iniciais = [
            "enable",
            "config",
            "undo smart",
            "scroll"
        ]

        for cmd in comandos_iniciais:
            tn.write(cmd.encode('utf-8') + b"\n")
            time.sleep(0.3)

        print("[INFO] Login na OLT realizado com sucesso!")
        print("[INFO] Verificando Uptime da OLT...")
        GetUptimeOfOLT(tn)

        print("[INFO] Obtendo a data atual da OLT...")

        actualDateOfOLT = GetActualDateTime(tn)
        print(f'[INFO] Data atual da OLT {actualDateOfOLT}')
        actualTimestampOfOLT = ConvertStringToTimestamp(actualDateOfOLT)
        print("[INFO] Listando PONs da OLT...")
        ListPonsAndGetNumberOfOfflineOnts(tn)
        print("")
        print("--------------------------")
        print("|    PON        OFF     ")
        print("--------------------------")
        for xpon in pons:
            totalOfflineBefore += int(xpon['offline'])
            print(f"|   {xpon['pon']}      {xpon['offline']}       ")
        print("--------------------------")
        print(f"    Total       {totalOfflineBefore}     ")
        print("--------------------------")
        print("")
       
       
        tempoEstimado = totalOfflineBefore * segundos_por_onu
        minutos_estimados = tempoEstimado // 60
        segundos_restantes = tempoEstimado % 60
        print(f"[INFO] Tempo estimado para execução: {minutos_estimados} min {segundos_restantes} seg")
        print("[INFO] Iniciando remoção de ONUs offline há mais de 10 dias...")

        for ponObj in pons:
            pon = ponObj['pon']
            onusOffline = GetListOfOfflineONT(tn, pon)
            if len(onusOffline) > 0:
                print("")
                print(f'[INFO] Verificando ONUs da PON: {pon}')
                for onu in onusOffline:
                    timestamp = GetDateTimeOfONT(tn, onu)
                    if (actualTimestampOfOLT-timestamp)>777600:
                        DeleteServicePortAndOnt(tn, onu)
                    
            else:
                continue
            

        

        tn.write(b"exit\n")
        time.sleep(.3)
        tn.close()
        fim = time.time()
        tempoTotal = int(fim - inicio)
        minutos_totais = tempoTotal // 60
        segundos_totais = tempoTotal % 60
        print(f"[INFO] Tempo total de execução: {minutos_totais} min {segundos_totais} seg")
        return
    
    except Exception as e:
        print(f"[ERRO] Problema durante o processo de login/comando - {e}")
        tn.close()
        fim = time.time()
        tempoTotal = int(fim - inicio)
        minutos_totais = tempoTotal // 60
        segundos_totais = tempoTotal % 60
        print(f"[INFO] Tempo total de execução: {minutos_totais} min {segundos_totais} seg")
        return

    

    

    


def main(ip, user, password, port, totalOfflineBefore, totalOfflineAfter):
    ConnectOnOLTWithTelnet(ip, user, password, port, totalOfflineBefore, totalOfflineAfter)


if __name__ == "__main__":
    try:
        ip, user, password, port = sys.argv[1:5]
    except ValueError:
        print("Uso correto: python script.py <ip> <user> <password> <port>")
        sys.exit(1)
        
    main(ip, user, password, port, totalOfflineBefore, totalOfflineAfter)
