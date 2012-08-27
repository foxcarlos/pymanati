#!/usr/bin/env python
# -*- coding: utf-8 *-*

'''Modulo utilizados:
    import xlwt (Escribir archivos de MS Excel)
    from rutinas import varias
'''

import time
import os
import sys
from xlwt import *
import socket

ruta_bibliotecas = os.path.abspath('desarrollo/python')
sys.path.append(ruta_bibliotecas)

from rutinas.varias import *

ruta_arch_conf = os.path.dirname(sys.argv[0])
archivo_configuracion = os.path.join(ruta_arch_conf, 'pymanati.conf')
fc = FileConfig(archivo_configuracion)


class Consulta():
    '''Clase para realizar consultas a la Base de datos del Log de Squid'''
    def __init__(self):
        pass

    def iniciar_postgres(self):
        self.host, self.clave, self.db, self.user = fc.opcion_consultar('POSTGRESQL')
        self.cadconex = "host='%s' dbname='%s' user='%s' password='%s'" % \
        (self.host[1], self.db[1], self.user[1], self.clave[1])
        self.pg = ConectarPG(self.cadconex)

    def consulta_fecha(self, fdesde='', fhasta=''):
        if len(fdesde) > 0 and len(fhasta) > 0:
            cad_fecha = " (fecha between \
to_date('%s','YYYY-MM-DD') and \
to_date('%s','YYYY-MM-DD'))" % (fdesde, fhasta)
        else:
            cad_fecha = ''
        return cad_fecha

    def consulta_ip(self, ips):
        lista_ip = ips.split(',')
        cadena = ''
        for ip in lista_ip:
            cadena = cadena + "'" + ip.strip() + "'" + ","
        #si ips esta vacio no se concatena nada
        cad_sql_ip = '' if len(ips) <= 0 else " (ip like (%s) )" % (cadena.rstrip(','))
        return cad_sql_ip

    def consulta_todas(self):
        fdesde = raw_input('Ingrese la fecha de Desde YYYY-MM-DD :')
        fhasta = raw_input('Ingrese la fecha de Hasta YYYY-MM-DD :')
        ips = raw_input('Ingrese la o las Direcciones IP  separadas por Coma:')
        paginas = raw_input('Ingrese la pagina que desea consultar:')

        cond1 = self.consulta_fecha(fdesde, fhasta) + ' and ' if len(self.consulta_fecha(fdesde, fhasta)) \
        > 0 else ''
        cond2 = self.consulta_ip(ips) + ' and ' if len(self.consulta_ip(ips)) > 0 else ''
        cond3 = " direccion like '%" + paginas + "%' and " if len(paginas) > 0 else ''
        cond4 = "(acceso not like '%DENIED%') and "
        cad_1 = "%s %s %s %s" % (cond1, cond2, cond3, cond4)

        cad_select = "select id,to_char(fecha,'DD-MM-YYYY HH24:MI') as fecha,ip,direccion \
from log_squid where %s" % (cad_1.strip().rstrip('and'))
        print cad_select
        #time.sleep(10)

        self.iniciar_postgres()
        self.registros = self.pg.ejecutar(cad_select)
        tuplas = calcular_longitud(self.registros, 0, 65000)
        exportar_excel(tuplas)

    def consulta_ip_sin_navegar(self):
        for linea in file('pc.txt'):
            pc = linea.split('\t')[0]
            try:
                ip_pc = socket.gethostbyname(pc)
            except:
                ip_pc = '0.0.0.0'

            select_sql = '''select id,to_char(fecha,'DD-MM-YYYY HH24:MI') as fecha,ip,direccion from 
            log_squid  where (fecha between to_date('2012-07-24','YYYY-MM-DD') and to_date('2012-08-06','YYYY-MM-DD')
            and ip = '%s') ''' % (ip_pc)
            
            self.iniciar_postgres()
            if len(self.pg.ejecutar(select_sql)) <= 0:
                print 'El Computador %s no ha navegado' % (pc)
   


def incluir():
    pass


def consultar():
    cns = Consulta()
    seguir = True
    while seguir:
        os.system('clear')
        print '--------------------------'
        print '-----Metodo Consultar-----'
        print '--------------------------'
        print '1- Consultar por Fecha,IP,Web'
        print '2- Consultar IP que no hayan navegado en Internet'
        print '3- Regresar...'
        print '--------------------------'
        opc = raw_input('Ingrese la Opcion de Consulta:')
        if opc.strip() == '1':
            cns.consulta_todas()
        elif opc.strip() == '2':
            cns.consulta_ip_sin_navegar()
        elif opc.strip() == '3':
            seguir = False
            #print 'Metodo Modificar'


def eliminar():
    print 'Metodo Eliminar'


def salir():
    print 'Metodo Salir'


def main():
    seguir = True
    while seguir:
        print '--------------------------'
        print '-----MENU PRINCIPAL-------'
        print '--------------------------'
        print '1 - Inlcuir'
        print '2 - Consultar'
        print '3 - Modificar'
        print '4 - Eliminar'
        print '5 - Salir'
        print '-------------------'
        op = raw_input('Ingrese la opcion:')
        os.system('clear')

        if op.strip() == '1':
            incluir()
        elif op.strip() == '2':
            consultar()
            os.system('clear')
        elif op.strip() == '3':
            modificar()
        elif op.strip() == '4':
            eliminar()
        elif op.strip() == '5':
            salir()
            seguir = False


if __name__ == '__main__':
    main()
