#!/usr/bin/env python

import logging
import os
import sys
import ConfigParser
import paramiko
import datetime
import psycopg2
import socket
import datetime

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
        opcion = 'archivo_log'
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
        self.logger = logging.getLogger("DemonioPyManati")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s--> %(asctime)s - %(name)s:  %(message)s", datefmt='%d/%m/%Y %I:%M:%S %p')
        handler = logging.FileHandler(nombreArchivoLog)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        return handler

    def prepararPostGreSQL(self):
        seccion = 'POSTGRESQL'
        if self.fc.has_section(seccion):
            host, dbname, user, password = [valores[1] for valores in self.fc.items(seccion)]
            self.cadConex = 'host={0} dbname={1} user={2} password={3} '.format(host, dbname, user, password)
        else:
            mensaje = 'No existe la seccion:"{0}" dentro del archivo de configuracion'.format(seccion)
            self.logger.error(mensaje)
            sys.exit(0)

    def conectarPostGreSQL(self):
        try:
            self.prepararPostGreSQL()
            self.conn = psycopg2.connect(self.cadConex)
            self.cur = self.conn.cursor()
        except:
            # Obtiene la ecepcion mas reciente
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error(exceptionValue)
            sys.exit(0)

    def ejecutarPostGreSQL(self, comandoSQL):
        try:
            self.cur.execute(comandoSQL)
            #self.records = self.cur.fetchall()
            #self.devolver = self.records
        except:
            # Obtiene la ecepcion mas reciente
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            # sale del Script e Imprime un error con lo que sucedio.
            self.logger.error(exceptionValue)
            sys.exit(0)

    def nombre_pc(self, ippc):
        '''
        metodo que permite obtener el nombre de un pc mediante
        la direccion ip suministrada,
        *Recibe como parametro la ip del pc
        *Retorna el Nombre del PC
        *Ej:
        pc_name = nombre_pc('10.121.10.5')
        print pc_name
        '''
        devolver = 'host desconocido'
        if len(ippc) > 0:
            try:
                nombrepc = socket.gethostbyaddr(ippc)
                devolver = nombrepc[0]
            except:
                pass
        return devolver

    def nombreArchivo(self):
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
        seccion = 'SQUID'
        if self.fc.has_section(seccion):
            confSquid = self.fc.items('SQUID')
            self.rutaRemota, self.rutaLocal, self.archivoRemoto = [valor[1] for valor in confSquid]
                
            self.rutaArchivoLocal = os.path.join(self.rutaLocal, self.archivoRemoto)
            self.rutaArchivoRemoto = os.path.join(self.rutaRemota, self.archivoRemoto)
               
            self.mascaraArchivo = dma_hms
            #print(self.rutaArchivoLocal)
        else:
            self.logger.error('Error al leer archivo de configuracion .cfg, no se consigue la Seccion:"{0}"'.format(seccion))
            sys.exit(0)
    
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
            print(servidor, int(puerto), usuario, clave) 
        except:
            devolver = False
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error('Error al momento de conectar con el Servidor SSH:{0}:"{1}"'.format(servidor, exceptionValue))
            sys.exit(0)
        return devolver

    def ssh_ejecutar(self, comando):
        '''
        El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
        via ssh.
    
        Valor Devuelto: El metodo devuelve el mensaje de error, si quiero saber si
        genero error simplemente busco la longitud del mensaje "len(error)"
        si este devuelve valor 0 quiere decir que no genero ningun error
        '''
        
        self.conectarSSH = self.ssh_conectar()
        if not self.conectarSSH:
            stdin, stdout, stderr = self.ssh.exec_command(comando)
            error = stderr.read()
            salida = stdout.read()
            print(error, salida)
            self.conectarSSH.close()
 
    def leer_log(self, archivoLocal):
        '''
        El log de squid viene separado por espacios en blanco , este medotdo
        recorre el archivo linea por linea y toma cada columna desechando aquellas
        que esten sin datos , es decir desecha las columnas que solo tengan un
        espacion en blanco Ej, '10410021221', ' ', ' ', 'www.foxcarlos.wordpress.
        com' en el ejemplo el metodo devolveria :
        '10410021221','www.foxcarlos.wordpress.com'
        '''

        archivo_local = archivoLocal
        self.conectarPostGreSQL()

        f = open(archivo_local)
        for linea in f.readlines():
            separar = linea.split()
            if len(separar) > 1:
                lfecha = 'to_timestamp(%s)' % (separar[0])
                lpuerto = separar[1]
                lip = separar[2]
                '''
                Llama al metodo nombre_pc() para ubicar el nombre del pc
                '''
                lpc = self.nombre_pc(lip.strip())
                lacceso = separar[3]
                lpuerto_acceso = separar[4]
                lmetodo = separar[5]
                ldireccion = separar[6]    
                lredireccion = separar[7]

                comandoSQL = "insert into log_squid (fecha,puerto,ip,pc,acceso,\
                puerto_acceso,metodo,direccion,redireccion) \
                values ({0},'{1}','{2}','{3}','{4}','{5}','{6}',$${7}$$,$${8}$$)".\
                format(lfecha, lpuerto, lip, lpc, lacceso, lpuerto_acceso, lmetodo, \
                ldireccion[0:240], lredireccion)
                
                print(comandoSQL)
                self.ejecutarPostGreSQL(comandoSQL)
                self.conn.commit()
        self.cur.close()
        self.conn.close()
   
    def copiarRemoto_log(self, tupla):
        '''
         Metodo que permite copiarme el log del servidor remoto squid
         a mi pc local, este metodo recibe como parametro una tupla
         con los nombres del archivo tanto local como remoto
         Ej:
         archivo_local = '/home/cgarcia/desarrollo/python/agr/log/access.log'
         archivo_remoto = '/var/log/squid3/access.log'
    
         tupla = (archivo_local, archivo_remoto)
         copiarRemoto_log(tupla)
        '''

        rutaArchivoRemoto, rutaArchivoLocal = tupla
        ssh_cnx = self.ssh_conectar()
        if not ssh_cnx:
            ftp = ssh_cnx.open_sftp()
            ftp.get(rutaArchivoRemoto, rutaArchivoLocal)
            ftp.close()
            ssh_cnx.close()

    def preparar_log_remoto(self, tupla):
        '''Este metodo se conecta via SSH con el servidor proxy
        y lo detiene mientras realiza las siguientes operaciones:
            - Mueve el archivo access.log
            - crea un nuevo archivo access.log
            - Le asigna los permisos de proxy:proxy
            - Inicia de nuevo el proxy'''
        
        nombre_real, nombre_copia = tupla
        self.ssh_ejecutar('/etc/init.d/squid3 stop')
        self.ssh_ejecutar('mv {0} {1}'.format(nombre_real, nombre_copia))
        self.ssh_ejecutar('echo > {0}'.format(nombre_real))
        self.ssh_ejecutar('chown proxy:proxy {0}'.format(nombre_real))
        self.ssh_ejecutar('/etc/init.d/squid3 start')

    def main(self):
        '''Metodo Proncipal'''

        self.nombreArchivo()
        #Estas son variables publicas (nombreReal y nombreCopia) generadas desde el metodo nombreArchivo()
        self.nombreReal = self.rutaArchivoRemoto
        self.nombreCopia = self.rutaArchivoLocal + self.mascaraArchivo
        tupla = (self.nombreReal, self.nombreCopia)
        
        self.preparar_log_remoto(tupla)
        self.copiarRemoto_log(tupla)
        self.leer_log(self.nombreCopia)

        #self.leer_log(('/var/log/squid3/', '/home/cgarcia/desarrollo/python/pymanati/access.log'))

    def prue(self):
        print('entro')
        self.logger.info('Iniciando demonio')
        self.ssh_ejecutar('ls /temp')
        self.logger.info('Finalizado Demonio')
        print('se salio')

    def run(self):
        '''Metodo que ejecuta el demonio y lo mantiene
        ejecutandose infinitamente hasta que se ejecute
        el comando:
        python demonioLogSquid.py stop'''

        horaEjecutar = 17
        while True:
            fecha = datetime.datetime.now()
            hora = fecha.hour
            if hora >= horaEjecutar:
                self.logger.info('Iniciando demonio')
                self.prue()
                self.logger.info('Finalizado Demonio')

if __name__ == '__main__':
    app = demonioServer()
    handler = app.configLog()
    app.run()
    #daemon_runner = runner.DaemonRunner(app)
    #daemon_runner.daemon_context.files_preserve = [handler.stream]
    #daemon_runner.do_action()
