# File Transfer 

Sistema de transferencia de archivos sobre UDP con protocolos de transmisión confiable en la capa de aplicación.

## Ejecución

Desde la carpeta ```src/``` del proyecto, inicializar el servidor en una
terminal y el cliente en otra utilizando los siguientes comandos.

## Servidor

El comando tiene la siguiente estructura:
```
start_server.py [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [- s DIRPATH ]
```
Ejemplo de uso:
```
python3 start_server.py -H 127.0.0.1 -p 8000 -s ./storage
```

Argumentos: 
```
-h , -- help, mostrar mensaje de help y salir
-v , -- verbose, aumenta la verbosidad
-q , -- quiet, disminuye la verbosidad
-H , -- host, dirección IP del servicio
-p , -- port, puerto del servicio
-s , -- storage, path para el almancenamiento
```

## Cliente

El cliente soporta los comandos ```upload``` y ```download```.

### Upload
```
upload.py [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - s FILEPATH ] [ - n FILENAME ] [ - r
protocol ]
```
Argumentos: 
```
-h , -- help, mostrar mensaje de help y salir
-v , -- verbose, aumenta la verbosidad
-q , -- quiet, disminuye la verbosidad
-H , -- host, dirección IP del servicio
-p , -- port, puerto del servicio
-s , -- src, path del archivo origen
-n , -- name, nombre dela rchivo
-r , -- protocolo de recuperación de errores
```

Ejemplo de uso: 

```
python3 upload.py  -H 127.0.0.1   -p 8000   -s ./lib/data/5mb.jpg   -n 5mb.jpg   -r sw -v
```

### Download

```
download.py [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - d FILEPATH ] [ - n FILENAME ] [ - r
protocol ]
```

Argumentos:
```
-h , -- help, mostrar mensaje de help y salir
-v , -- verbose, aumenta la verbosidad
-q , -- quiet, disminuye la verbosidad
-H , -- host, dirección IP del servicio
-p , -- port, puerto del servicio
-d , -- src, path destino del archivo
-n , -- name, nombre dela rchivo
-r , -- protocolo de recuperación de errores
```

Ejemplo de uso:

```
python3 download.py  -H 127.0.0.1   -p 8000   -d 3mb.jpg   -n 3mb.jpg   -r gbn -v```
```

Para una conexión exitosa, el ```host``` y el ```puerto``` deben coincidir con los especificados en el servidor.

---
## Mininet 

Para ejecutar la topología de mininet con una perdida de 10%, se debe tener instalado ```xterm``` para visualizar las terminales. Estas se abren de la siguiente manera:

Primero corremos la topología desde la carpeta ```/mininet```:
```
sudo python3 topology.py
```
Y ahora desde mininet:
```
xterm server client
```

Se abrirán dos terminales, una para ```server``` y otra para ```client```. En cada una se deben correr los respectivos comandos, asegurándose de usar la dirección ```0.0.0.0``` para el servidor, y  ```10.0.0.2``` para el client.