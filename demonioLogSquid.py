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

        self.nombreArchivoConf = 'pymanati.cfg'
        self.fc = SafeConfigParser()

        #Propiedades de la Clase
        self.archivoLog = ''

        #Ejecutar los Procesos Inciales
        self.configInicial()
        self.configDemonio()

    def configInicial(self):
        '''Metodo que permite extraer todos los parametros
        del archivo de configuracion pymanati.cfg que se
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

        if self.fc.has_section('SQUID'):
            confSquid = self.fc.items('SQUID')
            self.rutaRemota, self.rutaLocal, self.archivoRemoto = [valor[1] for valor in confSquid]
                
            self.rutaArchivoLocal = os.path.join(self.rutaLocal, self.archivoRemoto)
            self.rutaArchivoRemoto = os.path.join(self.rutaRemota, self.archivoRemoto)
               
            self.mascaraArchivo = dma_hms
            print(self.rutaArchivoLocal)
        else:
            self.logger.error('Error al leer archivo de configuracion .cfg, no se consigue la Seccion "SQUID"')

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

    def ssh_ejecutar(self, comando):
        '''
        El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
        via ssh.
    
        Valor Devuelto: El metodo devuelve el mensaje de error, si quiero saber si
        genero error simplemente busco la longitud del mensaje "len(error)"
        si este devuelve valor 0 quiere decir que no genero ningun error
        '''
        
        conectarSSH = self.ssh_conectar()
        if not conectarSSH:
            stdin, stdout, stderr = conectarSSH.exec_command(comando)
            error = stderr.read()
            print(error)
            conectarSSH.close()
 
    def leer_log(self, tupla):
        '''
        El log de squid viene separado por espacios en blanco , este medotdo
        recorre el archivo linea por linea y toma cada columna desechando aquellas
        que esten sin datos , es decir desecha las columnas que solo tengan un
        espacion en blanco Ej, '10410021221', ' ', ' ', 'www.foxcarlos.wordpress.
        com' en el ejemplo el metodo devolveria :
        '10410021221','www.foxcarlos.wordpress.com'
        '''

        archivo_local = tupla[1]  
        no_linea = 0
    
        '''#<POSTGRESQL>
        host, db, user, clave = fc.opcion_consultar('POSTGRESQL')
        cadconex = "host='%s' dbname='%s' user='%s' password='%s'" % (host[1], db[1], user[1], clave[1])   
        pg = ConectarPG(cadconex)

        #</POSTGRESQL>'''
        
        f = open(archivo_local)
        for linea in f.readlines():
            no_linea = no_linea + 1
            #print no_linea
            separar = linea.split()
    
            if len(separar) > 1:
                '''
                El Metodo limpiar_lista() elimina de la tupla ciertas
                condiciones que no se necesitan, por ejemplo tuplas vacias
                '''
                #separar = limpiar_lista(separar_tupla)
    
                '''
                Aqui convierto la hora en segundos que coloca squid en
                su archivo access.log en un formato fecha entendible
                por humanos (dd/mm/aaa hh:mm:ss) , por ahora esta opcion
                esta desabilitada ya que utlizo la funcion que me provee
                PostGreSql, "to_timestamp" que hace la conversion automaticamente
                Ej:to_timestamp(1325523994.041)
    
                Antes:
                t = time.localtime(float(separar[0]))
                lfecha = '%s/%s/%s %s:%s:%s' % \
                    (t.tm_mday, t.tm_mon, t.tm_year, t.tm_hour, t.tm_min, t.tm_sec)
                '''

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

                ComandoSql = "insert into log_squid (fecha,puerto,ip,pc,acceso,\
                puerto_acceso,metodo,direccion,redireccion) \
                values ({0},'{1}','{2}','{3}','{4}','{5}','{6}',$${7}$$,$${8}$$)".\
                format(lfecha, lpuerto, lip, lpc, lacceso, lpuerto_acceso, lmetodo, \
                ldireccion[0:240], lredireccion)

                print ComandoSql
                #reg_devueltos = pg.ejecutar(ComandoSql)   
                #pg.conn.commit()
   
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
        nombreReal = self.rutaArchivoRemoto
        nombreCopia = self.rutaArchivoLocal + self.mascaraArchivo
        tupla = (nombreReal, nombreCopia)
        
        #self.preparar_log_remoto(tupla)
        #self.ssh_copiar_log(tupla)
        self.leer_log(('/var/log/squid3/', '/home/cgarcia/desarrollo/python/pymanati/access.log'))


    def run(self):
        '''Metodo que ejecuta el demonio y lo mantiene
        ejecutandose infinitamente hasta que se ejecute
        el comando:
        python demonioLogSquid.py stop'''

        self.logger.info('Felicidades..!, Demonio Iniciado con Exito')

        while True:
            self.main()

app = demonioServer()
handler = app.configLog()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()
