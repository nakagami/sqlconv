import sys
from distutils.core import setup

description='SQL converter'
setup(name='sqlconv',
      version="%d.%d.%d" % __import__('sqlconv').VERSION,
      description=description,
      url='https://github.com/nakagami/sqlconv',
      author='Hajime Nakagami',
      author_email='nakagami@gmail.com',
      license='MIT',
      install_requires=['sqlparse'],
      py_modules=['sqlconv'])
