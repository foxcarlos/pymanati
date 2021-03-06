#!/usr/bin/env python
# -*- coding: utf-8 *-*

import logging
import os
import sys
import ConfigParser
import paramiko
import pxssh
import datetime
import psycopg2
import socket
import datetime
import subprocess
import time
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
        del archivo de configuracion pymanati.cfg que se
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
        self.logger = logging.getLogger("{0}".format(self.archivoActual))
        self.logger.setLevel(logging.INFO)
        #formatter = logging.Formatter("%(levelname)s--> %(asctime)s - %(name)s:  %(message)s", datefmt='%d/%m/%Y %I:%M:%S %p')

        #2013/11/28 15:13:53| WARNING:
        formatter = logging.Formatter("%(asctime)s| %(name)s| %(levelname)s: %(message)s", datefmt='%Y/%m/%d %I:%M:%S %p')

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
            self.rutaRemota, self.rutaLocal, self.archivoRemoto, self.rutaCSV = [valor[1] for valor in confSquid]

            self.rutaArchivoLocal = os.path.join(self.rutaLocal, self.archivoRemoto)
            self.rutaArchivoRemoto = os.path.join(self.rutaRemota, self.archivoRemoto)
            self.rutaArchivoCSV = os.path.join(self.rutaCSV, self.archivoRemoto)

            self.mascaraArchivo = dma_hms
            #print(self.rutaArchivoLocal)
        else:
            self.logger.error('Error al leer archivo de configuracion .cfg, no se consigue la Seccion:"{0}"'.format(seccion))
            #sys.exit(0)

    def sshConectar(self):
        ''' '''
        devolver = True
        self.ssh = pxssh.pxssh()
        confSquid = self.fc.items('SSH')
        servidor, puerto, usuario, clave = [valores[1] for valores in confSquid]
        try:
            self.ssh.login(servidor,  usuario, clave, port=puerto)
            #self.ssh.sendline('uptime')
            #self.ssh.prompt()
            #print(self.ssh.before)
            #self.ssh.logout()
            self.logger.info('Conexion Satisfactoria con el Servidor SSH:{0}'.format(servidor))
        except:
            devolver = False
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error('Error al momento de conectar con el Servidor SSH:{0}:"{1}"'.format(servidor, exceptionValue))
            sys.exit(0)
        return devolver


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

    def sshEjecutar(self, comandoEjecutar):
        ''' ssh_ejecutar('ls -l' )
        Parametros de Entrada: 1 tipo:string
        El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
        via ssh.'''

        confSquid = self.fc.items('SSH')
        servidor, puerto, usuario, clave = [valores[1] for valores in confSquid]

        comandoSSH = comandoEjecutar
        comando = 'ssh {0}@{1} {2} '.format(usuario, servidor, comandoSSH)
        try:
            ejecutar = subprocess.Popen(comando, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            errorEnComando = ejecutar.stderr.read()
            print(comando)

            if errorEnComando:
                self.logger.error('Ocurrio el siguiente error:{0} ejecutando el comando:{1}'.format(errorEnComando, comando))

            self.logger.info('Ejecutado con Exito el comando:{1}'.format(comando))
        except:
            print('Hubo una ecepcion', comando)
            # Obtiene la ecepcion mas reciente
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            #sale del Script e Imprime un error con lo que sucedio
            self.logger.error(exceptionValue)

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

                #print(comandoSQL)
                self.ejecutarPostGreSQL(comandoSQL)
                self.conn.commit()
        self.cur.close()
        self.conn.close()

    def leerLog(self, tupla):
        '''Parametros 1 Tipo Tupla (nombreArchivo.log, nombreArchuivo.csv)
        Este metodo permite  tratar el archivo .LOG que se copio
        desde el servidor squid hasta el pc local reccoriendo line a
        linea y ordenar cada fila para poder crear un archivo separado
        por comas CSV para luego con otro proceso hacer el COPY TO a
        PostgreSQL o a MongoDB'''

        l = ''
        archivo_local, archivoCSV = tupla

        try:
            with open(archivo_local) as archivo:
                for fila in archivo.readlines():
                    separar = fila.split()
                    #print(separar)
                    try:
                        fechaStamp, puerto, ip, acceso, puerto_acceso, \
                        metodo, direccion, redirect1, redirect2, redirect3 = separar
                    except:
                        fechaStamp, puerto, ip, acceso, puerto_acceso, metodo, \
                        direccion, redirect1, redirect2, redirect3 = \
                        ['1390852504.791', '1111', '10.0.0.0', 'TCP_MISS/200', '7814', 'CONNECT', 'Error', '-', 'error', '-']

                    fechaChar = datetime.datetime.fromtimestamp(float(fechaStamp))
                    fecha = fechaChar.strftime('%Y-%m-%d %I:%M:%S')
                    pc = ''  # self.nombre_pc(ip.strip())
                    direccion =  direccion  # [0:240]  # Creo  que se limita a 240 por postgres
                    direccion = direccion.replace(',', '')

                    l = '{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(\
                    fecha, puerto, ip, pc, acceso, puerto_acceso, metodo, direccion)

                    with open(archivoCSV, 'a') as n:
                        n.write(l)
                        n.close()
            archivo.close()
        except:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error('Ocurrio un error al momento de abrir el archivo via ssh:{0}'.format(exceptionValue))

    def importarRemotoLog(self, tupla):
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
        if ssh_cnx:
            ftp = self.ssh.open_sftp()
            try:
                ftp.get(rutaArchivoRemoto, rutaArchivoLocal)
                #ftp.put(local_path, remote_path)
                ftp.close()
            except:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.logger.error('Ocurrio un error al momento de copiar el archivo via ssh:{0}'.format(exceptionValue))

            self.ssh.close()

    def exportarRemotoLog(self, tupla):
        '''
         Metodo que permite copiar el .csv local al servidor remoro
         recibe como parametro una tupla con los nombres del archivo
         tanto local como remoto
         Ej:
         archivo_local = '/home/cgarcia/desarrollo/python/agr/log/access.csv'
         archivo_remoto = '/home/administrador/csv/access.csv'

         tupla = (archivo_local, archivo_remoto)
         copiarRemoto_log(tupla)
        '''

        rutaArchivoRemoto, rutaArchivoLocal = tupla

        self.ssh2 = paramiko.SSHClient()
        self.ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_cnx2 = False
        servidor, puerto, usuario, clave = ['10.121.6.4', '22', 'administrador', 'shc21152115']
        try:
            self.ssh2.connect(servidor, int(puerto), usuario, clave)
            self.logger.info('Conexion Satisfactoria con el Servidor SSH:{0}'.format(servidor))
            ssh_cnx2 = True
        except:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            self.logger.error('Error al momento de conectar con el Servidor SSH:{0}:"{1}"'.format(servidor, exceptionValue))
            #sys.exit(0)

        if ssh_cnx2:
            ftp2 = self.ssh2.open_sftp()
            try:
                ftp2.put(rutaArchivoLocal, rutaArchivoRemoto)
                ftp2.close()
            except:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                self.logger.error('Ocurrio un error al momento de copiar el archivo .csv via ssh:{0}'.format(exceptionValue))
            self.ssh2.close()

    def prepararLogRemoto(self, tupla):
        '''Este metodo se conecta via SSH con el servidor proxy
        y lo detiene mientras realiza las siguientes operaciones:
         - Copia el archivo remoto access.log con otro nombre
        '''

        print(tupla)
        nombre_real, nombre_copia = tupla
        #self.ssh_ejecutar('/etc/init.d/squid3 stop')
        self.sshEjecutar('"cp {0} {1}"'.format(nombre_real, nombre_copia))
        #self.ssh_ejecutar('/etc/init.d/squid3 start')

    def limpiarLogRemoto(self, tupla):
        '''Este metodo se conecta via SSH con el servidor proxy
        y lo detiene mientras realiza las siguientes operaciones:
            - elimina el archivo remoto access.log
            - Crear un nuevo archivo Log vacio access.log
            - Le asigna los permisos de proxy:proxy
            - Inicia de nuevo el proxy
            - Elimina la copia que se habia hecho de access.log
        '''

        nombre_real, nombre_copia = tupla

        self.sshEjecutar('"echo > {0}"'.format(nombre_real))
        self.sshEjecutar('"chown proxy:proxy {0}"'.format(nombre_real))

        self.logger.info('Eliminando archivo {0} que es una copia de {1} del proxy'\
                         .format(nombre_copia, nombre_real))

        self.sshEjecutar('rm {0}'.format(nombre_copia))

    def limpiarLogLocal(self, nombreRutaArchivo):
        ''' Metodo que permite eliminar archivos .Log del PC Local'''

        self.logger.info('Eliminando {0} del pc local'.format(nombreRutaArchivo))
        os.system('rm {0}'.format(nombreRutaArchivo))

    def main(self):
        '''Metodo Principal'''

        #El metodo nombreArchivo permite obtener del archivo de configuracion
        #Las rutas y nombre de los archivos a copiar y renombrar
        self.nombreArchivo()

        archivoConRutaLocal = self.rutaArchivoLocal
        archivoConRutaRemota = self.rutaArchivoRemoto
        mascara = self.mascaraArchivo

        #Hacer una Copia de Access.log remoto y copiarlo con otro nombre
        self.nombreCopia = archivoConRutaRemota + mascara
        self.prepararLogRemoto((archivoConRutaRemota, self.nombreCopia))

        #Copiar el archivo remoto para el pc local y poder tratarlo
        self.importarRemotoLog((self.nombreCopia, archivoConRutaLocal + mascara))

        #Tratar el archivo .log LOCAL para transformarlo en un archivo .CSV
        #Se le pasan 2 parametros (El nombre del archivo mas una mascara que tiene formato dma_hms)
        self.leerLog((archivoConRutaLocal + mascara, archivoConRutaLocal + mascara + '.csv'))

        #Apartir de aqui se usa MongoDb
        '''Este comando es para exportar el .csv a mongo database
        Si se desea reemplazar la coleccion se utuliza el parametro --drop
        de lo contrario si se desea a�adir a la coleccion se quita el
        parametro --drop
        mongoimport -d pymanati -c log_squid --drop --stopOnError --type csv --file
        /home/cgarcia/access.csv --ignoreBlanks --fields fecha,puerto,ip,pc,acceso,
        puerto_acceso,metodo,direccion'''

        #comandoTerminalMongo = "mongoimport -d pymanati -c log_squid --stopOnError --type csv --file /home/cgarcia/access.csv --ignoreBlanks --fields fecha,puerto,ip,pc,acceso,puerto_acceso,metodo,direccion"
        #os.system(comandoTerminalMongo)
        #c = subprocess.Popen(['mongoimport', '-d', 'pymanati', '-c', 'log_squid',  '--stopOnError' ,'--type', 'csv', '--file', '/home/cgarcia/access.csv', '--ignoreBlanks', '--fields', 'fecha,puerto,ip,pc,acceso,puerto_acceso,metodo,direccion'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=False)

        al = archivoConRutaLocal + mascara + '.csv'
        os.system('export LC_ALL=C')
        comando = 'mongoimport -h 10.121.3.124:27017 -d  pymanati -c log_squid --stopOnError --type csv --file {0} --ignoreBlanks \
            --fields fecha,puerto,ip,pc,acceso,puerto_acceso,metodo,direccion'.format(al)
        try:
            ejecutar = subprocess.Popen(comando, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            errorEnComando = ejecutar.stderr.read()

            if errorEnComando:
                self.logger.info('Ocurrio el siguiente error:{0} ejecutando el comando:{1}'.format(errorEnComando, comando))
            else:

                #Limpiar Log y copia del .log  del server remoto
                self.nombreCopia = archivoConRutaRemota + mascara
                self.limpiarLogRemoto((archivoConRutaRemota, self.nombreCopia))

        except:
            # Obtiene la ecepcion mas reciente
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            #sale del Script e Imprime un error con lo que sucedio
            self.logger.error(exceptionValue)

        #Eliminar el archivo .log y .csv local
        self.limpiarLogLocal(archivoConRutaLocal + mascara)
        self.limpiarLogLocal(archivoConRutaLocal + mascara + '.csv')


    def run(self):
        '''Metodo que ejecuta el demonio y lo mantiene
        ejecutandose infinitamente hasta que se ejecute
        el comando:
        python demonioLogSquid.py stop'''

        #horaEjecutar = 13
        while True:
            #fecha = datetime.datetime.now()
            #hora = fecha.hour
            #if hora == horaEjecutar:
            self.logger.info('Iniciando demonio')
            self.main()
            self.logger.info('Finalizado Demonio')
            #sys.exit(0)
            time.sleep(1800)

'''
#Instancio la Clase
app = demonioServer()
handler = app.configLog()
daemon_runner = runner.DaemonRunner(app)

#Esto garantiza que el identificador de archivo logger no quede cerrada durante daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()
'''

if __name__ == '__main__':
    app = demonioServer()
    handler = app.configLog()
    app.run()
