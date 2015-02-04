#-*-coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/pymanati.ui'
#
# Created: Fri Feb 22 10:25:34 2013
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
# 
# pyside-uic -o windowUi.py src/pymanati.ui
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
    '''
    '''

    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        # Esto es siempre lo mismo
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        '''
        Aqui se conectan todos los objetos con sus slot
        '''
        QtCore.QObject.connect(self.ui.btnBuscar, QtCore.SIGNAL("clicked()"), self.tipoBusqueda)
        QtCore.QObject.connect(self.ui.btnLimpiar, QtCore.SIGNAL("clicked()"), self.limpiarText)
        QtCore.QObject.connect(self.ui.btnExportar, QtCore.SIGNAL("clicked()"), self.exportarExcel)
        self.connect(self.ui.btnSalir, QtCore.SIGNAL('clicked()'),QtGui.qApp, QtCore.SLOT('quit()'))
        self.statusBar().showMessage("Listo")

        self.main()

    def main(self):
        '''
        Este metodo se ejecuta al iniciar la Aplicacion,
        en las variables host, db, user, clave, se almacenaran
        los valores necesarios para realizar las consultas a
        el servidor de Base de Datos PostGreSQL y estas a su vez 
        crearan una Cadena de Conexion que sera utilizada por
        toda la aplicacion como variable Publica
        '''

        self.archivoCfg()

        #Antes:
        #host, db, user, clave = fc.opcion_consultar('POSTGRESQL')
        #self.cadconex = "host='%s' dbname='%s' user='%s' password='%s'" % (host[1], db[1], user[1], clave[1])
        
        #Ahora
        self.prepararPostGreSQL()

        self.ui.txtFechaDesde.setFocus()
        self.registros = []

        #Si la Plataforma es Windows aumento de tamaño los Iconos de los botones ya que se ven muy pequeños
        if sys.platform == 'win32':
            self.ui.btnBuscar.setIconSize(QtCore.QSize(45, 45))
            self.ui.btnLimpiar.setIconSize(QtCore.QSize(35, 35))
            self.ui.btnExportar.setIconSize(QtCore.QSize(35, 35))
            self.ui.btnSalir.setIconSize(QtCore.QSize(35, 35))

    def archivoCfg(self):
        '''Inicializa y Obtiene Informacion del archivo de Configuracion .cfg'''

        self.nombreArchivoConf = 'pymanati.cfg'
        self.fc = ConfigParser.ConfigParser()

        self.ruta_arch_conf = os.path.dirname(os.path.abspath(__file__))
        self.archivo_configuracion = os.path.join(self.ruta_arch_conf, self.nombreArchivoConf)
        self.fc.read(self.archivo_configuracion)
   
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
        '''Este Metodo permite elecutar una sentencia SQL pasada como parametro
        y devuelve una lista con los registros'''

        self.devolver = []

        try:
            self.cur.execute(comandoSQL)
            self.records = self.cur.fetchall()
            self.devolver = self.records
        except:
            # Obtiene la ecepcion mas reciente
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            # sale del Script e Imprime un error con lo que sucedio.
            self.logger.error(exceptionValue)
            sys.exit(0)
        return self.devolver

    def tipoBusqueda(self):
        if self.ui.radiobBuscar.isChecked():
            self.validarBusqueda()
        else:
            self.Filtrar()

    def validarBusqueda(self):
        campos = []

        lcFechaDesde = self.ui.txtFechaDesde.text()
        lcFechaHasta = self.ui.txtFechaHasta.text()
        lcPuerto = self.ui.txtPuerto.text()
        lcIP = self.ui.txtIP.text()
        lcComputador = self.ui.txtComputador.text()
        lcWeb = self.ui.txtWeb.text().upper()
        
        #para saber cuantos campos de consultaran
        for f in lcFechaDesde, lcFechaHasta, lcPuerto , lcIP, lcComputador, lcWeb:
            if f:
                campos.append(f)

        #saber de cuantos dias es la consulta, si no se coloca nada se elimina el caracter '/'
        f1 = datetime.datetime.strptime(lcFechaDesde, '%d/%m/%Y').date() if lcFechaDesde.replace('/', '') else 0
        f2 = datetime.datetime.strptime(lcFechaHasta, '%d/%m/%Y').date() if lcFechaHasta.replace('/', '') else 0

        '''
        Si el valor de FechaDesde y El Valor de Fecha hasta esta Vacio 
        entonces la variable dias se establece a 0, en python 0 devuelve False
        '''
        
        dias = (f2 - f1).days if f1 and f2  else 0

        if dias >30 or len(campos) <3:
            mensaje = 'Para que la Busqueda sea mas eficiente y rapida Verifique que la consulta no sobrepase los 30 dias \
o que realice una busqueda de almenos 3 campos'
            msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, 'Aviso de Sistema', mensaje)
            msgBox.exec_()
        else:
            self.Buscar()

    def Buscar(self):
        '''
        Metodo que se utiliza para realizar la busqueda segun lo que
        ingresa el usuario en las cajas de texto.
        '''

        #registros = self.obtenerDatos('select id, fecha, puerto, ip, pc, puerto_acceso, metodo, direccion from log_squid limit 10')
        #print registros   
        listaCabecera = [('ID', 90), ('FECHA', 160), ('PUERTO', 60), ('IP', 100),
                ('PC', 160), ('P_ACCESO', 100), ('METODO', 80), ('DIRECCION_WEB', 300)]
        
        cadSql = self.armarSelect()
        print cadSql
        if cadSql:
            self.statusBar().showMessage("Espere mientras se obtienen los registros de la base de datos....!")
            self.setCursor(QtCore.Qt.WaitCursor)
            self.registros = ''
            self.registros = self.obtenerDatos(cadSql)  # Ejecuta en PostGreSQL la cadena sql pasada 
            self.PrepararTableWidget(self.registros, listaCabecera)  # Configurar el tableWidget
            self.InsertarRegistros(self.registros)  # Insertar los Registros en el TableWidget
            self.statusBar().showMessage("Consulta realizada con exito, se obtuvieron %s registro(s)" % (len(self.registros)))
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, 'Lo siento', 'Es necesario que seleccione una opcion de Busqueda')
            msgBox.exec_()

    def Filtrar(self):
        '''
        '''
        print('Click')
        l = self.registros

        lcFechaDesde = self.ui.txtFechaDesde.text()
        lcFechaHasta = self.ui.txtFechaHasta.text()
        lcPuerto = self.ui.txtPuerto.text()
        lcIP = self.ui.txtIP.text()
        lcComputador = self.ui.txtComputador.text()
        lcWeb = self.ui.txtWeb.text().upper()
        
        cadFechaD = "'%s' in f and " % (lcFechaDesde) if lcFechaDesde.replace('/', '') else ''        
        cadFechaH = "'%s' in f and " % (lcFechaHasta) if lcFechaHasta.replace('/', '')  else ''
        cadPuerto = "'%s'  in f and " % (lcPuerto) if lcPuerto else ''
        cadIP = "'%s' in f and "   % (lcIP) if lcIP.replace('.', '') else ''
        cadComputador = "'%s' in f and " % (lcComputador) if lcComputador else ''
        cadWeb = "'%s' in f  and " % (lcWeb) if lcWeb else ''
        filtro = cadFechaD + cadFechaH + cadPuerto + cadIP + cadComputador + cadWeb
        cadFiltrar = filtro[:-4]
        
        for f in l:
            if eval(cadFiltrar):
                print f


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

        cadenaSql = ''
        lcFechaDesde = self.ui.txtFechaDesde.text()
        lcFechaHasta = self.ui.txtFechaHasta.text()
        lcPuerto = self.ui.txtPuerto.text()
        lcIP = self.ui.txtIP.text()
        lcComputador = self.ui.txtComputador.text()
        lcWeb = self.ui.txtWeb.text().upper()

        cadFecha = "(fecha between '%s' AND '%s') AND " % (lcFechaDesde, lcFechaHasta) \
                if (lcFechaDesde.replace('/', '') and lcFechaHasta.replace('/', '')) else ''

        cadPuerto = "puerto = %s AND " % (lcPuerto) if lcPuerto else ''
        cadIP = "ip like '%%%s%%' AND "   % (lcIP) if lcIP.replace('.', '') else ''
        cadComputador = "upper(pc) like '%%%s%%' AND " % (lcComputador.upper()) if lcComputador else ''
        cadWeb = "upper(direccion) like '%%%s%%' AND " % (lcWeb) if lcWeb else ''
        cadSoloValidas = "(acceso not like '%DENIED%') and "
        cadExcluirme = "upper(pc) !='ANLPRG7' AND "

        #Campos que pide el Form, es necesario que el usuario llene por lo menos uno
        campos = cadFecha + cadPuerto + cadIP + cadComputador + cadWeb
        
        #Si lleno al menos uno, arma el select, de lo contrario devuelde cadenaSql Vacia
        if campos:
            campos = campos + cadExcluirme + cadSoloValidas
            cadenaSql = 'select id, fecha, puerto, ip, pc, puerto_acceso, metodo, direccion from log_squid  where ' + \
                campos + 'del = 0 '
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
        self.conectarPostGreSQL()
        registros = self.ejecutarPostGreSQL(cadena_pasada)

        '''
        try:
            pg = ConectarPG(self.cadconex)
            registros = pg.ejecutar(cadena_pasada)
            pg.cur.close()
            pg.conn.close()
        except:
            registros = []
        '''
        return registros

    def exportarExcel(self):
        '''
        Permite Exportar a excel los registros obtenidos en la Consulta,
        estos registros estan contenidos dentro de la variable 
        self.registros devuelto por el Metodo obtenerDatos(), si existen
        registros estos son exportados a de lo contrario emite un mensaje
        de Advertencia
        '''

        file = QtGui.QFileDialog.getSaveFileName(self, caption="Guardar Archivo Como..", filter=".xls")
        nombreArchivo = file[0] + file[1]
        
        if self.registros:
            tuplas = calcular_longitud(self.registros, 0, 65000)
            exportar_excel(tuplas, nombreArchivo)
            
            msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Information, 'Felicidades ....', 'Consulta Guardada con Exito en:%s' % (file[0]))
            msgBox.exec_()
        else:
            msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, 'Lo siento', 'No Existen registros para guardar')
            msgBox.exec_()

    def limpiarText(self):
        '''
        Limpia los QlineEdit o Textbox
        '''
        self.ui.txtFechaDesde.clear()
        self.ui.txtFechaHasta.clear()
        self.ui.txtPuerto.clear()
        self.ui.txtIP.clear()
        self.ui.txtComputador.clear()
        self.ui.txtWeb.clear()

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
        msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Question, 'Titulo', lcMensaje)
        msgBox.exec_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    mySW = ControlMainWindow()
    mySW.show()
    sys.exit(app.exec_())
