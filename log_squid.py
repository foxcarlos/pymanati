#!/usr/bin/env python
# -*- coding: utf-8 *-*

'''
Creado el 19/12/2011
@author: Carlos Garcia (foxcarlos)

Script que permite obtener via SSH el log de navegacion que genera
el servidor proxy squid y copiarlo localmente para luego e ingresarlo
en una Base de Datos PostGreSql o Sqlite
Modulo Utilizados:
datetime : Obtener fecha y hora
psycopg2 : Para conectarse a una base de datos PostGresql
socket : Para obtener el nombre de un pc via socket
paramiko : Para conectarse via ssh a un pc remoto
'''


import datetime
import psycopg2
import socket
import paramiko
import sys
import os

from rutinas.varias import *

lin = 0
archivo_log_con_ruta = ''

ruta_arch_conf = os.path.dirname(sys.argv[0])
archivo_configuracion = os.path.join(ruta_arch_conf, 'pymanati.conf')
fc = FileConfig(archivo_configuracion)

def nombre_archivo(opcion):
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
    dma_hms = t.strftime('%d%m%Y%I%M%S')      
    conf_squid = fc.opcion_consultar('SQUID')
    
    ruta_remota = conf_squid[0][1] 
    ruta_local = conf_squid[1][1] 
           
    ruta = {'local': ruta_local, 'remoto': ruta_remota}
    nombre_archivo = conf_squid[4][1]  # 'access'
    archivo = "%s%s_%s" % (ruta[opcion], nombre_archivo, dma_hms)
    return archivo

    
def ssh_conectar():
    '''
     Metodo que permite conectarme via ssh al servidor proxy
    '''
    conf_squid = fc.opcion_consultar('SSH')
    ssh = ''
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    servidor = fc.opcion_consultar('SSH')[0][1]
    puerto = int(fc.opcion_consultar('SSH')[1][1])
    usuario = fc.opcion_consultar('SSH')[2][1]
    clave = fc.opcion_consultar('SSH')[3][1]
    try:
        ssh.connect(servidor,puerto,usuario,clave)
    except:
        ssh = 1
    return ssh


def ssh_copiar_log(tupla):
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
    error = ''
   
    rutaarchivo_local = tupla[0]
    rutaarchivo_remoto = tupla[1]

    ssh_cnx = ssh_conectar()
    if ssh_cnx == 1:
        error = '**Error al intentar conectar via SSH metodo ssh_conectar()**'
        reporta_error(error)
    else:
        ftp = ssh_cnx.open_sftp()
        ftp.get(rutaarchivo_remoto, rutaarchivo_local)
        ftp.close()
        ssh_cnx.close()


def ssh_ejecutar(comando):
    '''
    El Metodo ssh_ejecutar ejecuta un comando del sistema operativo remoto
    via ssh.

    Valor Devuelto: El metodo devuelve el mensaje de error, si quiero saber si
    genero error simplemente busco la longitud del mensaje "len(error)"
    si este devuelve valor 0 quiere decir que no genero ningun error
    '''
    error = ''
    x = ssh_conectar()
    if x == 1:
        error = '**Error al intentar conectar via SSH metodo ssh_conectar()**'
        reporta_error(error)
    else:
        stdin, stdout, stderr = x.exec_command(comando)
        error = stderr.read()
        reporta_error(error)
        x.close()


def preparar_log_remoto(tupla):
    '''
    '''
    error = ''  
    
    nombre_real = fc.opcion_consultar('SQUID')[0][1] + fc.opcion_consultar('SQUID')[4][1]
    nombre_copia = tupla[1]

    detener = ssh_ejecutar('/etc/init.d/squid3 stop')
    renombrar = ssh_ejecutar('mv %s %s' % (nombre_real, nombre_copia))
    crear = ssh_ejecutar('echo > %s' % (nombre_real))
    chown = ssh_ejecutar('chown proxy:proxy %s' % (nombre_real))
    iniciar = ssh_ejecutar('/etc/init.d/squid3 start')

    error = "%s\n%s\n%s\n%s\n%s" % (detener, renombrar, crear, chown, iniciar)
    reporta_error(error)


def nombre_pc(ippc):
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


def sql_ejecutar(cadena_sql):
    '''
    metodo que permite realizar operaciones sobre una base de datos en
    postgresql, esta funcion recibe como parametro el comando a ejecutar
    ej: "Select *from tabla"
    '''
     
    error = '' 
    reg_devueltos = pg.ejecutar(cadena_sql)   
    pg.conn.commit()
    return reg_devueltos


def limpiar_lista(separar):
    '''
     Metodo que permite eliminar de la Lista que fue pasada como parametro
     aquellas que estan vacias y las que tienen solo un guion
     ej: ('fox','','-','carlos','')
     Count() Cuenta cuantas veces se repite en la Lista el parametro pasado
     remove() Elimina de la lista aquellas que cumplan la condicion
     For Lin recorre la Lista y ejecuta el Metodo remove()
    '''

    eliminar_blanco = separar.count('')
    eliminar_guion = separar.count('-')

    lin = 0
    for lin in range(eliminar_guion):
        separar.remove('-')

    lin = 0
    for lin in range(eliminar_blanco):
        separar.remove('')

    return separar


def leer_log(tupla):
    '''
    El log de squid viene separado por espacios en blanco , este medotdo
    recorre el archivo linea por linea y toma cada columna desechando aquellas
    que esten sin datos , es decir desecha las columnas que solo tengan un
    espacion en blanco Ej, '10410021221', ' ', ' ', 'www.foxcarlos.wordpress.
    com' en el ejemplo el metodo devolveria :
    '10410021221','www.foxcarlos.wordpress.com'
    '''

    archivo_local = tupla[0]

    separador = ' '
    no_linea = 0
    
    #<POSTGRESQL>
    host, db, user, clave = fc.opcion_consultar('POSTGRESQL')
    cadconex = "host='%s' dbname='%s' user='%s' password='%s'" % (host[1], db[1], user[1], clave[1])   
    pg = ConectarPG(cadconex) 
    #</POSTGRESQL>
    
    for linea in file(archivo_local):
        no_linea = no_linea + 1
        #print no_linea
        separar_tupla = linea.split(separador)

        if len(separar_tupla) > 1:
            '''
            El Metodo limpiar_lista() elimina de la tupla ciertas
            condiciones que no se necesitan, por ejemplo tuplas vacias
            '''
            separar = limpiar_lista(separar_tupla)

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
            lpc = nombre_pc(lip.strip())
            lacceso = separar[3]
            lpuerto_acceso = separar[4]
            lmetodo = separar[5]
            ldireccion = separar[6]
            '''
            Las Comillas simples y el simbolo de porcentaje en la direccion web
             generan error se reemplazan por la palabra comilla_simple
            '''

            ldireccion2 = ldireccion.replace("'", "comilla_simple")
            ldireccion3 = ldireccion2.replace("%", "porcentaje")
    
            lredireccion = separar[7]
            lredireccion2 = lredireccion.replace("%", "porcentaje")
            lredireccion3 = lredireccion2.replace("'", "comilla_simple")

            ComandoSql = "insert into log_squid (fecha,puerto,ip,pc,acceso,\
            puerto_acceso,metodo,direccion,redireccion) \
            values (%s,'%s','%s','%s','%s','%s','%s','%s','%s')" \
            % (lfecha, lpuerto, lip, lpc, lacceso, lpuerto_acceso, lmetodo, \
            ldireccion3[0:240], lredireccion3)

            print ComandoSql            
            reg_devueltos = pg.ejecutar(ComandoSql)   
            pg.conn.commit()


def reporta_error(recibe_error):
    '''
     Documentar
    '''
    file_log = fc.opcion_consultar('SQUID')[2][1]
    error = "%s\n" % (recibe_error)
    f = open(file_log, "a")
    f.write(error)
    f.close()


def iniciar():

    tupla = nombre_archivo('local'), nombre_archivo('remoto')
    #tupla = ('/home/cgarcia/desarrollo/python/pymanati/logs/access_09082012121115.log', '/var/log/squid3/access_09082012121115.log')
    
    reporta_error('Iniciando  Preparar_log')
    preparar_log_remoto(tupla)
    reporta_error('Terminando  Preparar_log')

    reporta_error('Iniciando  ssh_copiar')
    ssh_copiar_log(tupla)
    reporta_error('Terminando  ssh_copiar')

    reporta_error('Leyendo archivo de log y procesando la inforamcion')
    leer_log(tupla)
    reporta_error('Proceso de lectura de log terminado')

if __name__ == '__main__': 
    reporta_error('*** Iniciando Proceso por favor espere...***')
    iniciar()
    reporta_error('*** Proceso terminado ***')
