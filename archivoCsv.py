'''
Primero se debe obtener el archivo access.log de squid,
luego tomar del archivo .log y tratarlo y tomar solo 
algunos campos para crear con esa inforamcion un nuevo
arhivo con estension .csv, luego de tener listo el archivo
.csv ejecutar el comando "copy" de postgresql para hacer
el insert de todo el archivo a la tabla log_squid
'''
import datetime
import os
import sys

def leerLog(self, archivoLocal):
    ''' Este metodo permite  tratar el archivo .LOG que se copio 
    desde el servidor squid hasta el pc local reccoriendo line a 
    linea y ordenar cada fila para poder crear un archivo separado
    por comas CSV para luego con otro proceso hacer el COPY TO a 
    PostgreSQL'''
    
    l = ''
    archivo_local = archivoLocal
    archivoCSV = archivoLocal + '.csv'
    
    with open(archivo_local) as archivo:
        for fila in archivo.readlines():
            separar = fila.split()
            fechaStamp, puerto, ip, acceso, puerto_acceso, \
            metodo, direccion, redirect1, redirect2, redirect3 = separar
            
            fechaChar = datetime.datetime.fromtimestamp(float(fechaStamp))
            fecha = fechaChar.strftime('%Y-%m-%d %I:%M:%S')
            pc = self.nombre_pc(ip.strip())
            direccion =  direccion[0:240]
            direccion = direccion.replace(',', '')
            
            l = '{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(\
            fecha, puerto, ip, pc, acceso, puerto_acceso, metodo, direccion)
            
            with open(archivoCSV, 'a') as n:
                n.write(l)
                n.close()
    archivo.close()
    print(l)
    
    comandoSQL = """ copy log_squid (fecha,puerto,ip,pc,acceso,puerto_acceso,metodo,direccion) from '/home/administrador/prueba.csv' delimiter ','"""
    
    #psql -U postgres -h 10.121.6.4 -F "," -A -c "select *from log_squid limit 10" -o log_squid.csv bdhcoromoto
    '''
    scp /home/cgarcia/respaldo_pg/pymanati/logs/prueba.csv  administrador@10.121.6.4:/home/administrador/
    
    psql -U postgres -h 10.121.6.4 -c "copy log_squid (fecha,puerto,ip,pc,acceso,puerto_acceso,metodo,direccion) from '/home/administrador/prueba.csv' delimiter ','" bdhcoromoto
    '''