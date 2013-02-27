from distutils.core import setup
import py2exe

setup(name="pyManati",
      version="1.0",
      license="GPL",
    windows=[{"script":"pymanati.py", "icon_resources":[(1, "img/manati.ico")]}])

