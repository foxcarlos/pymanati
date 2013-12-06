__author__ = 'cgarcia'
#!/usr/bin/python
import time
from daemon import runner
import paramiko
import sys

class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/foo.pid'
        self.pidfile_timeout = 5
        self.ssh_conectar()
        self.ssh_ejecutar('ls -lah')
    
    def ssh_conectar(self):
        ''' Metodo que permite conectarme via ssh al servidor proxy'''
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        servidor, puerto, usuario, clave = ['10.121.6.12', '22', 'root', 'shcproxy014107475237921shc']
        try:
            self.ssh.connect(servidor, int(puerto), usuario, clave)
            print('Conexion Satisfactoria con el Servidor SSH:{0}'.format(servidor))
        except:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            print('Error al momento de conectar con el Servidor SSH:{0}:"{1}"'.format(servidor, exceptionValue))
            self.ssh.close()
            sys.exit(0)

    def ssh_ejecutar(self, comando):
        ''' Meotodo que permite ejecutar un comando ssh 
        pasado como parametro'''

        try:
            stdin, stdout, stderr = self.ssh.exec_command(comando)
            error = stderr.read()
            salida = stdout.read()
            if error:
                print('Error al momento de ejecutar el comando "{0}" :{1}'.format(comando, error))
            
            if salida:
                print('El Comando {0} devolvio lo siguiente:{1}'.format(comando, salida))
        except:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            print('Error al momento de ejecutar el comando:{0}:"{1}"'.format(comando, exceptionValue))
            sys.exit(0)

    def run(self):
        while True:
            print("Howdy!  Gig'em!  Whoop!")
            #self.ssh_ejecutar('ls -lah')
            time.sleep(10)

app = App()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.do_action()
