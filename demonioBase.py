__author__ = 'cgarcia'
#!/usr/bin/env python

import logging
import os
import sys
import ConfigParser
import paramiko
from daemon import runner

class demonioServer():
    def __init__(self):
        '''Init'''

        self.archivoCfg()
        self.configInicial()
        self.configDemonio()

    def archivoCfg(self):
        '''Inicializa y Obtiene Informacion del archivo de Configuracion .cfg'''

        self.nombreArchivoConf = 'pymanati.cfg'
        self.fc = ConfigParser.ConfigParser()

        self.ruta_arch_conf = os.path.dirname(os.path.abspath(__file__))
        self.archivo_configuracion = os.path.join(self.ruta_arch_conf, self.nombreArchivoConf)
        self.fc.read(self.archivo_configuracion)

    def configInicial(self):
        '''Metodo que permite extraer todos los parametros
        del archivo de configuracion pyloro.cfg que se
        utilizara en todo el script'''

        #Para saber como se llama este archivo .py que se esta ejecutando
        archivo = sys.argv[0]  # Obtengo el nombre de este  archivo
        archivoSinRuta = os.path.basename(archivo)  # Elimino la Ruta en caso de tenerla
        self.archivoActual = archivoSinRuta

        #Obtiene el nombre del archivo .log para uso del Logging
        seccion = 'RUTAS'
        opcion = 'archivoLog'
        self.archivoLog = self.fc.get(seccion, opcion)

    def configDemonio(self):
        '''Configuiracion del Demonio'''

        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/{0}.pid'.format(self.archivoActual)
        self.pidfile_timeout = 5

    def configLog(self):
        '''Metodo que configura los Logs de error tanto el nombre
        del archivo como su ubicacion asi como tambien los
        metodos y formato de salida'''

        #Extrae de la clase la propiedad que contiene el nombre del archivo log
        nombreArchivoLog = self.archivoLog
        self.logger = logging.getLogger("{0}".format(self.archivoActual))
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s| %(name)s| %(levelname)s: %(message)s", datefmt='%Y/%m/%d %I:%M:%S %p')
        handler = logging.FileHandler(nombreArchivoLog)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        return handler

    def ssh_conectar(self):
        ''' Metodo que permite conectarme via ssh al servidor proxy'''
        devolver = True
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        confSquid = self.fc.items('SSH')
        servidor, puerto, usuario, clave = [valores[1] for valores in confSquid]
        try:
            self.ssh.connect(servidor, int(puerto), usuario, clave)
            self.logger.info('Conexion Satisfactoria con el Servidor SSH:{0}'.format(servidor))
        except:
            devolver = False
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error('Error al momento de conectar con el Servidor SSH:{0}:"{1}"'.format(servidor, exceptionValue))
            sys.exit(0)
        return devolver

    def ssh_ejecutar(self, comando):
        ''' ssh_ejecutar('ls -l' )
        Parametros de Entrada: 1 tipo:string

        El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
        via ssh.'''

        self.conectarSSH = self.ssh_conectar()
        if self.conectarSSH:
            stdin, stdout, stderr = self.ssh.exec_command(comando)
            error = stderr.read()
            salida = stdout.read()

            if error:
                self.logger.error('Error al momento de ejecutar el comando "{0}" :{1}'.format(comando, error))

            if salida:
                self.logger.info('El Comando {0} devolvio lo siguiente:{1}'.format(comando, salida))

            self.ssh.close()
        else:
            self.logger.error('no se pudo ejecutar el comando:{0}'.format(comando))

    def run(self):
        '''Metodo que ejecuta el demonio y lo mantiene
        ejecutandose infinitamente hasta que se ejecute
        el comando:
        python demonioLogSquid.py stop'''

        self.ssh_ejecutar('ls -lah')

        '''
        while True:
            self.logger.info('Iniciando demonio')
            self.main()
            self.logger.info('Finalizado Demonio')
            sys.exit(0)'''

app = demonioServer()
handler = app.configLog()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()
