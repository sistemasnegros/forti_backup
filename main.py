# -*- coding: utf-8 -*-

import os
import argparse
import logging
#import threading
#import shutil
import datetime
import time

from multiprocessing import Process
import multiprocessing

from paramiko import SSHClient
import paramiko

# Ruta de archivos estaticos
from unipath import Path

# librerias propias
from lib_sysblack.lib_config import load_config
from lib_sysblack.lib_csv import parser_cvs
from lib_sysblack.lib_mail import send_mail


from lib_sysblack.lib_folder_incremental import folder_incremental


# Raiz del proyecto
PROJECT_DIR = Path(__file__).ancestor(1)


NAMEAPP = "forti_backup"

NAME_FILE_LOG = "%s.log" % (NAMEAPP)
NAME_FILE_LOG_PATH = PROJECT_DIR.child(NAME_FILE_LOG)


NAME_FILE_CONFIG = "%s.cfg" % (NAMEAPP)
NAME_FILE_CONFIG_PATH = PROJECT_DIR.child(NAME_FILE_CONFIG)


FILE_CSV = "%s.csv" % (NAMEAPP)
FILE_CSV_PATH = PROJECT_DIR.child(FILE_CSV)

NAME_FOLDER_BACKUP = "backup"
NAME_FOLDER_BACKUP_PATH = PROJECT_DIR.child(NAME_FOLDER_BACKUP)

#outlock = threading.Lock()


def loading_args():
    """Argumento de ejecucion"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Mostrar información en consola.", action="store_true")
    parser.add_argument("-c", "--config", help="Nombre de archivo de configuracion.", default=NAME_FILE_CONFIG_PATH)
    parser.add_argument("-d", "--debug", help="Mostrar información de depuración.", action="store_true")
    parser.add_argument("-t", "--test", help="Tirar una prueba del comando.", action="store_true")
    parser.add_argument("-csv", help="Nombre de archivo de configuracion.", default=FILE_CSV_PATH)

    args = parser.parse_args()

    return args


def log_configuration(args):
    """Configurando los log"""

    level_log = logging.INFO

    if args.debug:
        level_log = logging.DEBUG

    logformat = "%(asctime)s %(levelname)s: %(message)s"

    logging.basicConfig(filename=NAME_FILE_LOG_PATH, filemode='w', format=logformat, level=level_log)

    if args.verbose:
        fh = logging.StreamHandler()
        logFormatter = logging.Formatter(logformat)
        fh.setFormatter(logFormatter)
        logging.getLogger().addHandler(fh)


def witter_file(name, data):
    file_config = open(name, "w")
    file_config.write(data)
    file_config.close()


def read_file(filename):
    with open(filename) as my_file:
        file_read = my_file.read()
    return file_read


def conect_fortigate(hostname, port, username, password):
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # print ssh
    ssh.connect(hostname, port=int(port), username=username, password=password, timeout=10, allow_agent=False, look_for_keys=False)

    return ssh


def exec_fortigate(ssh, comando):
    #global outlock

    stdin, stdout, stderr = ssh.exec_command(comando)

    outlines = stdout.read()
    #outlines = ""

    ssh.close()

    # print stdout.readlines()

    return outlines


def worker(forti, numero_copias):
    """funcion que realiza el trabajo en el thread"""
    logging.info('Process id {} - Start: {}. '.format(os.getpid(), forti["name"]))
    try:
        ssh = conect_fortigate(
            forti["host"],
            forti["port"],
            forti["user"],
            forti["pass"],
        )

        data = exec_fortigate(ssh, "show full-configuration")

        fecha = datetime.date.today()
        hora = time.strftime("%H-%M-%S")

        ruta_destino = NAME_FOLDER_BACKUP_PATH.child(forti["name"])

        name_file_backup_latest = "forti-%s-time-%s.txt" % (fecha, hora)

        #path_name_temp = PROJECT_DIR.child(name_file_backup_latest)
        path_name_temp = ruta_destino.child(name_file_backup_latest)

        #witter_file(name_file_backup_latest, data.replace("--More--", ""))

        controller_backup(forti["name"], NAME_FOLDER_BACKUP_PATH, path_name_temp, ruta_destino, numero_copias, data)

        logging.info('Process id {} - Copia de Seguridad Completada Correctamente en: {}. '.format(os.getpid(), forti["name"]))

    except Exception as e:

        logging.error("Process id {} - Error en la copia de seguridad: {} {}.".format(os.getpid(), e, forti["name"]))


def fun_send_mail(config, args, data_log=""):
    if config.get("MAIL", "enable") == "yes":

        send_from = config.get("MAIL", "send_from")
        username = config.get("MAIL", "username")
        password = config.get("MAIL", "password")
        send_to = config.get("MAIL", "send_to")

        files = config.get("MAIL", "files")
        if files == "no":
            files = None

        server = config.get("MAIL", "server")
        port = config.get("MAIL", "port")
        tls = config.get("MAIL", "tls")

        # with open(NAME_FILE_LOG_PATH) as my_file:
        #     data_log = my_file.read()

        subject = config.get("MAIL", "subject")

        for email in send_to.split(","):

            # Sin es una prueba evite la ejecucion
            if args.test:
                log = "Modo Test enable, se evito Mandar email a: {email}".format(email=email)
                logging.info(log)
                continue

            try:
                send_mail(
                    username,
                    password,
                    send_from,
                    email.strip(),
                    subject,
                    data_log,
                    files,
                    server,
                    port,
                    tls
                )

                logging.info('Email enviado correctamente.')

            except Exception as e:
                #raise e
                logging.error("Al Enviar email: {}.".format(e))


def folder_device(folder_backup, name_folder):
        # Si no exite la carpeta que guarda el historial del dispositivo, se crea!
    if not os.path.exists(folder_backup.child(name_folder)):
        os.mkdir(folder_backup.child(name_folder))


def controller_backup(folder_name, backup_path, path_name_temp, ruta_destino, numero_copias, data):

    # Nombre del archivo que va quedar con la copia mas reciente

    # Si no exite la carpeta que guarda el historial del dispositivo, se crea!
    folder_device(backup_path, folder_name)

    # print data_cleaned.replace("--More--", "")

    witter_file(path_name_temp, data.replace("--More--", ""))

    folder_incremental(path_name_temp, ruta_destino, numero_copias, "forti")


def main():
    """Funcion Principal"""

    # Cargando variables pasadas como argumentos
    args = loading_args()

    # estableciendo la configuracion de los logs
    log_configuration(args)

    logging.debug("Inicio de modo de depuracion.")

    # Cargando variables de configuracion
    # Esto toma el nombre del archivo conf por defecto y cargar de la raiz del folder
    config = load_config(args.config)

    list_fortigates = parser_cvs(args.csv, config.get("GENERAL", "fields_csv").split(","))

    threads = []

    numero_copias = config.get("GENERAL", "number_backup")

    for forti in list_fortigates:
        # Sin es una prueba evite la ejecucion
        if args.test:
            log = "Modo Test enable, se evito hacer el backup: {name} {host}:{port} {user} {password}".format(
                name=forti["name"],
                host=forti["host"],
                port=forti["port"],
                user=forti["user"],
                password=forti["pass"],

            )
            logging.info(log)
            continue

        #t = threading.Thread(target=worker, args=(forti, numero_copias))
        t = Process(target=worker, args=(forti, numero_copias))

        t.start()
        threads.append(t)
        time.sleep(0.5)

        # t.join()

    # Si no es una prueba
    if not args.test:

        for t in threads:
            t.join()

    # leo el log
    file_log_read = read_file(NAME_FILE_LOG_PATH)

    # mando el log del proceso al correo
    fun_send_mail(config, args, file_log_read)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
