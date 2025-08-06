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

def ListPonsAndGetNumberOfOfflineOnts(tn):
    tn.write(b"display ont info 0 all | include port 0\n")
    time.sleep(9)

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
    try:
        datetime_str = str_date
        datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        return (int(datetime.timestamp(datetime_object)))
    except Exception as e:
        print("Não foi possviel converder a data para timestamp")
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
        print("Não foi possivel obter a data atual da OLT")
        exit()

def GetDateTimeOfONT(tn, sn):

    timestampOfOnu = 837849918
    tn.write(
        f"display ont info by-sn {sn} | include down time\n".encode('utf-8'))
    time.sleep(3)

    return_ont_information = tn.read_until(
        'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
    for linha in return_ont_information:
        if "down time" in linha:
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
        time.sleep(8)

        return_ont_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_ont_information:
            if 'offline' in linha:
                offline_str = re.sub(r'0/\s', '0/', linha)
                onusOffline.append(re.sub(r'\s+', ";", offline_str).split(';')[3])
        return onusOffline
    except Exception as e:
        print(f"Não Foi possivel obter as ONUs Offline da PON {pon}")
        return onusOffline


def GetUptimeOfOLT(tn):
    uptimeInDays = 0
    try:
        tn.write(b"display version\n")
        time.sleep(3)

        return_uptime_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_uptime_information:
            if re.search(r'[Uu]ptime', linha):
                # Remove espacos iniciais, separa em um array e pega o valor de dias
                uptimeInDays = int(re.sub(r"^\s+", "", linha).split(' ')[2])
        if uptimeInDays < 10:
            print(f"A OLT está ligada há {uptimeInDays} dias.")
            print("O Uptime da OLT é menor que 10 dias, o script foi interrompido.")
            exit()

        else:
            print(f"A OLT está ligada há {uptimeInDays} dias.")
            return uptimeInDays
    except Exception as e:
        print("Não Foi possivel obter o Uptime da OLT")
        exit()


def DeleteServicePortAndOnt(tn, sn):
    ontId = str
    fsp = str
    srvPort = str

    try:
        tn.write(f"display ont info by-sn {sn}\n".encode('utf-8'))
        time.sleep(2)

        return_ont_information = tn.read_until(
            'Control flag'.encode('utf-8'), 3).decode('utf-8').splitlines()
        for linha in return_ont_information:
            if "F/S/P" in linha:
                fsp = linha.split(":")[1].replace(" ", "")
            if "ONT-ID" in linha:
                ontId = linha.split(":")[1].replace(" ", "")

        fspSplited = fsp.split('/')

        tn.write(
            f"display service-port port {fsp} ont {ontId} | include common\n".encode('utf-8'))
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

        print(f"Sucesso! - ONU Excluida - SN: {sn}")
        return

    except Exception as e:
        print(f"Falha! - Erro ao excluir ONU - SN: {sn}")
        return


def ConnectOnOLTWithTelnet(ip, user, password, port, totalOfflineBefore, totalOfflineAfter):

    try:
        tn = telnetlib.Telnet(ip, port, 10)
    except Exception as e:
        print(e)
        return

    # tn.set_debuglevel(100)

    tn.read_until(b"name:")
    tn.write(user.encode('utf-8') + b"\n")
    time.sleep(.3)
    tn.read_until(b"password:")
    tn.write(password.encode('utf-8') + b"\n")
    time.sleep(.3)

    tn.write(b"enable\n")
    time.sleep(.3)
    tn.write(b"config\n")
    time.sleep(.3)
    tn.write(b"undo smart\n")
    time.sleep(.3)
    tn.write(b"scroll\n")
    time.sleep(.3)

    
    print("Login na OLT realizado!")
    print("Verificando Uptime da OLT...")
    GetUptimeOfOLT(tn)
    print("Obtendo a data atual da OLT...")
    actualDateOfOLT = GetActualDateTime(tn)
    print(f'Data atual da OLT {actualDateOfOLT}')
    actualTimestampOfOLT = ConvertStringToTimestamp(actualDateOfOLT)
    print("Listando PONs da OLT...")
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
    print("Iniciando remoção de ONUs offline há mais de 10 dias...")

    for ponObj in pons:
        pon = ponObj['pon']
        onusOffline = GetListOfOfflineONT(tn, pon)
        if len(onusOffline) > 0:
            print("")
            print(f'PON: {pon}')
            for onu in onusOffline:
                timestamp = GetDateTimeOfONT(tn, onu)
                if (actualTimestampOfOLT-timestamp)>777600:
                    DeleteServicePortAndOnt(tn, onu)
                
        else:
            continue
        

    

    tn.write(b"exit\n")
    time.sleep(.3)
    tn.close()
    return


def main(ip, user, password, port, totalOfflineBefore, totalOfflineAfter):
    ConnectOnOLTWithTelnet(ip, user, password, port, totalOfflineBefore, totalOfflineAfter)


ip = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
port = sys.argv[4]


if __name__ == "__main__":
    main(ip, user, password, port, totalOfflineBefore, totalOfflineAfter)
