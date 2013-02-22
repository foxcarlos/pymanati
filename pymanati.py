# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/pymanati.ui'
#
# Created: Fri Feb 22 10:25:34 2013
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
#
# WARNING! All changes made in this file will be lost!

import sys
from PySide import QtCore, QtGui
from rutinas.varias import *
from windowUi import Ui_Form

ruta_arch_conf = os.path.dirname(sys.argv[0])
archivo_configuracion = os.path.join(ruta_arch_conf, 'pymanati.conf')
fc = FileConfig(archivo_configuracion)

class ControlMainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        # Esto es siempre lo mismo
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        '''
        Aqui se conectan todos los objetos con sus slot
        '''
        QtCore.QObject.connect(self.ui.btnBuscar, QtCore.SIGNAL("clicked()"), self.Buscar2)
        QtCore.QObject.connect(self.ui.btnLimpiar, QtCore.SIGNAL("clicked()"), self.limpiarText)        
        self.main()

    def main(self):
        host,  db, user, clave = fc.opcion_consultar('POSTGRESQL')
        self.cadconex = "host='%s' dbname='%s' user='%s' password='%s'" % (host[1], db[1], user[1], clave[1])

        #Esto es temporal mientras se hacen las pruebas
        self.Buscar()

    def iniciarForm(self):
        '''
        '''
        pass

    def Buscar2(self):
        '''
        '''
        x = self.armarSelect()
        print x

    def Buscar(self):
        '''
        Metodo que se utiliza para realizar la busqueda segun lo que
        ingresa el usuario en las cajas de texto.
        '''      
        
        registros = self.obtenerDatos('select id, fecha, puerto, ip, pc, puerto_acceso, metodo, direccion from log_squid limit 10')
        #print registros

        listaCabecera = [('ID', 90), ('FECHA', 160), ('PUERTO', 60), ('IP', 100),
                ('PC', 160), ('P_ACCESO', 100), ('METODO', 80), ('DIRECCION_WEB', 300)]
        
        self.PrepararTableWidget(registros, listaCabecera)  # Configurar el tableWidget
        self.InsertarRegistros(registros)  # Insertar los Registros en el TableWidget

    def PrepararTableWidget(self, CantidadReg=0, Columnas=0):
        '''
        Parametros pasados (2) (CantidadReg: Entero) y (Columnas :Lista)
        Ej: PrepararTableWidget(50, ['ID', 'FECHA', 'PUERTO'])
        
        Meotodo que permite asignar y ajustar  las columnas que tendra el tablewidget
        basados en la cantidad de conlumnas y la cantidad de registros que le son
        pasados como parametro
        '''

        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(245, 244, 226))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)

        brush = QtGui.QBrush(QtGui.QColor(254, 206, 45))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Highlight, brush)

        brush = QtGui.QBrush(QtGui.QColor(255, 255, 203))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)

        lista = CantidadReg
        self.ui.tableWidget.setColumnCount(len(Columnas))
        self.ui.tableWidget.setRowCount(len(lista))

        #Armar Cabeceras de las Columnas
        cabecera = []
        for f in Columnas:
            nombreCampo = f[0]
            cabecera.append(nombreCampo)

        for f in Columnas:
            posicion = Columnas.index(f)
            nombreCampo = f[0]
            ancho = f[1]
            self.ui.tableWidget.horizontalHeader().resizeSection(posicion, ancho)

        self.ui.tableWidget.setPalette(palette)  
        self.ui.tableWidget.setAutoFillBackground(False)
        self.ui.tableWidget.setAlternatingRowColors(True)
        self.ui.tableWidget.setHorizontalHeaderLabels(cabecera)
  
        self.ui.tableWidget.setSelectionMode(QtGui.QTableWidget.SingleSelection)
        self.ui.tableWidget.setSelectionBehavior(QtGui.QTableView.SelectRows)

        #ciudades = ["Valencia","Maracay","Barquisimeto","Merida","Caracas"]
        #self.combo.addItems(ciudades)
        #deshabilitar() 

    def armarSelect(self):
        '''
        Metodo que permite armar la consulta select segun 
        los datos que hay  en los textbox
        Parametro devuelto(1) String con la cadena sql de busqueda    
        '''

        lcFechaDesde = self.ui.txtFechaDesde.text()
        lcFechaHasta = self.ui.txtFechaHasta.text()
        lcPuerto = self.ui.txtPuerto.text()
        lcIP = self.ui.txtIP.text()
        lcComputador = self.ui.txtComputador.text()
        lcWeb = self.ui.txtWeb.text()

        cadFecha =  " fecha >= '%s' AND fecha<='%s' " % (lcFechaDesde, lcFechaHasta) if (lcFechaDesde and lcFechaHasta) else ''
        #valorDepartamento =  " upper(departamento) like '%%%s%%' AND " % (lcDepartamento.upper()) if lcDepartamento else ''
        #valorTelefono = " telefono like '%%%s%%' AND " % (lcTelefono) if lcTelefono else ''

        campos = cadFecha
        cadenaSql = 'select id,nombre,departamento,telefono from agenda where ' + campos + 'del = 0 order by nombre'
        return cadenaSql



    def InsertarRegistros(self, cursor):
        '''
        Metodo que permite asignarle registros al tablewidget
        parametros recibitos (1) Tipo (Lista)
        Ej:RowSource(['0', 'Carlos', 'Garcia'], ['1', 'Nairesther', 'Gomez'])
        '''

        ListaCursor = cursor
        for pos, fila in enumerate(ListaCursor):
            for posc, columna in enumerate(fila):
                self.ui.tableWidget.setItem(pos, posc, QtGui.QTableWidgetItem(str(columna)))

    def obtenerDatos(self, cadena_pasada):
        '''
        Ejecuta la Consulta SQl a el servidor PostGreSQL segun la cadena SQL
        pasada como parametro
        parametros recibidos: (1) String
        parametros devueltos: (1) Lista

        Ej: obtener_datos('select *from tabla where condicion')
        '''
        try:
            pg = ConectarPG(self.cadconex)
            self.registros = pg.ejecutar(cadena_pasada)
            pg.cur.close()
            pg.conn.close()
        except:
            self.registros = []
        return self.registros

    def limpiarText(self):
        '''
        Limpia los QlineEdit o Textbox
        '''
        self.txtId.clear()
        self.txtNombre.clear()
        self.txtDepartamento.clear()
        self.txtTelefono.clear()
        self.iniciarForm()

    def salir(self):
        pass

    def borrar(self):
        msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Question, 'Titulo', 'Prueba')
        #msgBox.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
        GuardarButton = msgBox.addButton("Guardar", QtGui.QMessageBox.ActionRole)
        AbortarButton = msgBox.addButton("Cancelar", QtGui.QMessageBox.ActionRole)
        msgBox.exec_()
        print GuardarButton
        print AbortarButton

    def GoFocus(self):
        lcMensaje = 'Hola'  # self.combo.currentText()
        msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Question, 'Titulo',lcMensaje)
        msgBox.exec_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    mySW = ControlMainWindow()
    mySW.show()
    sys.exit(app.exec_())
