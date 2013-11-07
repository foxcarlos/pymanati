#!/usr/bin/env python

import time
from daemon import runner
import logging
import os
import sys
import zmq
from rutinas import varias
from ConfigParser import SafeConfigParser
import paramiko
import datetime
import psycopg2
import socket


class demonioServer():
    def __init__(self):
        '''Metodo Init donde se inicializan
        todos los procesos para dar comienzo
        al Demonio'''

        #Para saber como se llama este archivo .py que se esta ejecutando
        archivo = sys.argv[0]  # Obtengo el nombre de este  archivo
        archivoSinRuta = os.path.basename(archivo)  # Elimino la Ruta en caso de tenerla
        self.archivoActual = archivoSinRuta

        self.nombreArchivoConf = 'pymanaty.cfg'
        self.fc = SafeConfigParser()

        #Propiedades de la Clase
        self.archivoLog = ''

        #Ejecutar los Procesos Inciales
        self.configInicial()
        self.configDemonio()

    def configInicial(self):
        '''Metodo que permite extraer todos los parametros
        del archivo de configuracion pyloro.conf que se
        utilizara en todo el script'''

        #Obtiene Informacion del archivo de Configuracion .cfg
        self.ruta_arch_conf = os.path.dirname(sys.argv[0])
        self.archivo_configuracion = os.path.join(self.ruta_arch_conf, self.nombreArchivoConf)
        self.fc.read(self.archivo_configuracion)

        #Obtiene el nombre del archivo .log para uso del Logging
        # (RUTAS Y archivo.log son los campos del archivo .cfg)
        seccion = 'RUTAS'
        opcion = 'archivo_log'
        self.archivoLog = self.fc.get(seccion, opcion)

    def configDemonio(self):
        '''Configuiracion del Demonio'''

        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/{0}.pid'.format(self.archivoActual)
        self.pidfile_timeout = 5

    def configLog(self):
        '''Metodo que configura los Logs de error tanto el nombre
        del archivo como su ubicacion asi como tambien los
        metodos y formato de salida'''

        #Extrae de la clase la propiedad que contiene el nombre del archivo log
        nombreArchivoLog = self.archivoLog
        self.logger = logging.getLogger("{0}".format(self.archivoActual))
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s--> %(asctime)s - %(name)s:  %(message)s", datefmt='%d/%m/%Y %I:%M:%S %p')
        handler = logging.FileHandler(nombreArchivoLog)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        return handler

    def nombre_archivo(self, opcion):
        '''
        metodo que permite armar el nombre del archivo basado en la fecha
        y hora del pc para el momento en el cual se este ejecutando, se crea
        un diccionario  con la ruta local y remota
        Parametro pasado 1:'local' o 'remoto' Ej: nombre_archivo('remoto')
        Parametro devuelto 1:Nombre del archivo basado en la fecha y hora
        asi como tambien la ruta, esta ruta dependera del parametro que le
        pasemos al metodo Ej:
        nombre_archivo('remoto')
        retornara: /var/log/squid3/access_ddmmaahhmmss.log
    
        '''
        t = datetime.datetime.now()
        dma_hms = t.strftime('%d_%m_%Y_%I%M%S')      
        confSquid = self.fc.items('SQUID')

        rutaRemota, rutaLocal, archivoRemoto = [valor[1] for valor in confSquid]
               
        ruta = {'local': rutaLocal, 'remoto': rutaRemota}
        nombreArchivo = archivoRemoto
        archivo = "%s%s_%s" % (ruta[opcion], nombreArchivo, dma_hms)
        return archivo

    def ssh_conectar(self):
        ''' Metodo que permite conectarme via ssh al servidor proxy'''
        devolver = True
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        confSquid = self.fc.items('SSH')
        servidor, puerto, usuario, clave = [valores[1] for valores in confSquid]
        try:
            ssh.connect(servidor,puerto,usuario,clave)
            self.logger.info('Conexion Satisfactoria con el Servidor SSH:{0}'.format(servidor))
        except:
            devolver = False
            self.logger.error('Error al momento de conectar con el Servidor SSH:{0}'.format(servidor))
        return devolver

    def ssh_copiar_log(self, tupla):
        '''
         Metodo que permite copiarme el log del servidor remoto squid
         a mi pc local, este metodo recibe como parametro una tupla
         con los nombres del archivo tanto local como remoto
         Ej:
         archivo_local = '/home/cgarcia/desarrollo/python/agr/log/access.log'
         archivo_remoto = '/var/log/squid3/access.log'
    
         tupla = (archivo_local, archivo_remoto)
         ssh_copiar_log(tupla)
        '''

        rutaArchivoLocal, rutaArchivoRemoto = tupla
        ssh_cnx = self.ssh_conectar()
        if not ssh_cnx:
            ftp = ssh_cnx.open_sftp()
            ftp.get(rutaArchivoRemoto, rutaArchivoLocal)
            ftp.close()
            ssh_cnx.close()

    def ssh_ejecutar(self, comando):
        '''
        El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
        via ssh.
    
        Valor Devuelto: El metodo devuelve el mensaje de error, si quiero saber si
        genero error simplemente busco la longitud del mensaje "len(error)"
        si este devuelve valor 0 quiere decir que no genero ningun error
        '''
        
        x = self.ssh_conectar()
        if not x:
            stdin, stdout, stderr = x.exec_command(comando)
            #error = stderr.read()
            x.close()

    def preparar_log_remoto(tupla):
        ''''''
        error = ''  
        detener = ''
        renombrar = ''
        crear = ''
        chown = ''
        iniciar = ''

        nombre_real = fc.opcion_consultar('SQUID')[0][1] + fc.opcion_consultar('SQUID')[3][1]
        nombre_copia = tupla[1]
        detener = ssh_ejecutar('/etc/init.d/squid3 stop')
        renombrar = ssh_ejecutar('mv %s %s' % (nombre_real, nombre_copia))
        crear = ssh_ejecutar('echo > %s' % (nombre_real))
        chown = ssh_ejecutar('chown proxy:proxy %s' % (nombre_real))
        iniciar = ssh_ejecutar('/etc/init.d/squid3 start')

        error = "%s\n%s\n%s\n%s\n%s" % (detener, renombrar, crear, chown, iniciar)
        print error
        #reporta_error(error)

    def run(self):
        '''Metodo que ejecuta el demonio y lo mantiene
        ejecutandose infinitamente hasta que se ejecute
        el comando:
        python demonioLogSquid.py stop'''

        self.logger.info('Felicidades..!, Demonio Iniciado con Exito')

        while True:
            pass

app = demonioServer()
handler = app.configLog()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()
