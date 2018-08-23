# Fortigate Backup automatizados por ssh

Con este script se pueden hacer backups de un dispositivo Fortigate por medio del puerto SSH. Esto se puede automatizar con tareas programadas recurrentes. Ademas tambien se permite matener unas rotacion de copias definida por el archivo de configuracion.


## Requerimientos
```
pip install lib_sysblack
pip install paramiko
pip install unipath
```

## Configure los parametros de conexion SSH en el archivo: forti_backup.csv
```
#ip,port,usuario,password,nombre
192.168.1.254,22,admin,password,Fortigate Master
```
## Compilacion para windows
pyinstaller main.spec

## Ejemplos de usos

#### Modo prueba 
```
python python main.py -v -d -t
```

#### Modo basico
```
python python main.py -v 
```

#### Modo basico en windows
```
forti_backup.exe -v 
```

#### Nota Importante
Cuando se vaya restablecer el backup editar manualmente y quitar el promt al comienzo y al final del archivo
```
miforti# 
miforti#
```
