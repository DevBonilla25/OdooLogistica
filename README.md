# OdooLogistica

Proyecto para ejecutar Odoo 19 Community con un modulo personalizado de ordenes de mantenimiento vehicular.

El repositorio contiene solo las personalizaciones del proyecto, no todo el core de Odoo.

## Estructura recomendada

En el servidor se trabajo con esta estructura:

```text
C:\Sites\odoo-logistic\
  odoo\              # Odoo Community 19 clonado desde GitHub
  OdooLogistica\     # Este repositorio
  iis\               # Carpeta vacia usada por IIS para reverse proxy
```

El modulo personalizado esta en:

```text
OdooLogistica\custom_addons\fleet_vehicle_maintenance_order
```

Si el modulo esta en `addons`, ajustar el `addons_path` segun corresponda.

## 1. Clonar Odoo y el repositorio del proyecto

```powershell
cd C:\Sites
mkdir odoo-logistic
cd C:\Sites\odoo-logistic

git clone https://github.com/odoo/odoo.git -b 19.0 odoo
git clone https://github.com/DevBonilla25/OdooLogistica.git OdooLogistica
```

## 2. Instalar Python 3.11

Descargar e instalar Python 3.11 para Windows:

```text
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
```

Durante la instalacion marcar:

```text
Add python.exe to PATH
Install launcher for all users
pip
venv
```

Validar:

```powershell
py -0
py -3.11 --version
```

## 3. Crear entorno virtual e instalar dependencias

```powershell
cd C:\Sites\odoo-logistic\odoo
py -3.11 -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Si aparece error con PostgreSQL/psycopg2:

```powershell
pip install psycopg2-binary
pip install -r requirements.txt
```

## 4. Instalar PostgreSQL

Instalar PostgreSQL para Windows y ubicar `psql.exe`. Ejemplo:

```text
C:\Program Files\PostgreSQL\18\bin\psql.exe
```

Crear usuario para Odoo. No usar el usuario `postgres` en `odoo.conf`.

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```

Dentro de `psql`:

```sql
CREATE USER odoo_user WITH PASSWORD 'Odoo2026';
ALTER USER odoo_user CREATEDB;
\q
```

## 5. Crear base de datos compatible en Windows

En Windows puede fallar la base si `LC_COLLATE` y `LC_CTYPE` quedan incompatibles. Crear la base asi:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U odoo_user -d postgres
```

Dentro de `psql`:

```sql
DROP DATABASE IF EXISTS odoo_logistic;

CREATE DATABASE odoo_logistic
WITH OWNER = odoo_user
ENCODING = 'UTF8'
LC_COLLATE = 'Spanish_Spain.1252'
LC_CTYPE = 'Spanish_Spain.1252'
TEMPLATE = template0;

\q
```

## 6. Configurar Odoo

Crear archivo:

```text
C:\Sites\odoo-logistic\odoo\odoo.conf
```

Ejemplo:

```ini
[options]
addons_path = C:\Sites\odoo-logistic\odoo\addons,C:\Sites\odoo-logistic\odoo\odoo\addons,C:\Sites\odoo-logistic\OdooLogistica\custom_addons
db_host = localhost
db_port = 5432
db_user = odoo_user
db_password = Odoo2026
http_port = 8070
http_interface = 127.0.0.1
proxy_mode = True
admin_passwd = AdminOdoo2026
```

Notas:

- `http_port = 8070`: puerto interno donde corre Odoo.
- `http_interface = 127.0.0.1`: Odoo solo escucha localmente.
- `proxy_mode = True`: requerido cuando IIS publica Odoo como proxy.
- `admin_passwd`: master password para crear/restaurar bases desde Odoo.

## 7. Inicializar Odoo

Inicializar la base:

```powershell
cd C:\Sites\odoo-logistic\odoo
.\.venv\Scripts\activate

python .\odoo-bin -c .\odoo.conf -d odoo_logistic -i base --stop-after-init
```

Levantar Odoo:

```powershell
python .\odoo-bin -c .\odoo.conf -d odoo_logistic
```

Abrir:

```text
http://localhost:8070
```

## 8. Aplicaciones Odoo requeridas

Antes de instalar el modulo personalizado, instalar o tener disponibles estas aplicaciones de Odoo:

```text
Fleet / Flota
Inventory / Inventario
Purchase / Compras
Contacts / Contactos
```

Módulo Personalizado

```text
Ordenes de Mantenimiento Vehicular
```

Uso de cada aplicacion:

```text
Fleet: relaciona las ordenes con los vehiculos.
Inventory: permite consumir repuestos existentes en bodega.
Purchase: permite crear RFQ / solicitudes de presupuesto de repuestos.
Contacts: permite gestionar proveedores, choferes/reportantes y empresas.
```

El modulo estandar **Maintenance / Mantenimiento** de Odoo no es obligatorio para este flujo. Ese modulo esta orientado a equipos internos, mientras que este proyecto maneja una orden de mantenimiento vehicular propia.

## 9. Instalar el modulo de mantenimiento vehicular

```powershell
cd C:\Sites\odoo-logistic\odoo
.\.venv\Scripts\activate

python .\odoo-bin -c .\odoo.conf -d odoo_logistic -i fleet_vehicle_maintenance_order --stop-after-init
```

Luego levantar Odoo:

```powershell
python .\odoo-bin -c .\odoo.conf -d odoo_logistic
```

## 10. Seeder de sistemas vehiculares

El modulo carga automaticamente los sistemas vehiculares desde:

```text
custom_addons\fleet_vehicle_maintenance_order\data\fleet_vehicle_system_data.xml
```

Valores incluidos:

```text
Sistema del Motor        engine
Sistema de Transmision   transmission
Sistema Electrico        electrical
Sistema de Frenos        brakes
Sistema de Suspension    suspension
Sistema de Direccion     steering
Sistema de Escape        exhaust
Llantas y Ruedas         tires_wheels
Lubricantes y Fluidos    fluids
Otros                    other
```

Este archivo esta declarado en `__manifest__.py` dentro de `data`, por lo que se ejecuta automaticamente al instalar el modulo.

## 11. Publicar Odoo con IIS

IIS no ejecuta Odoo directamente. IIS se usa como reverse proxy:

```text
Cliente red local -> IIS puerto 8085 -> Odoo localhost:8070
```

### Instalar componentes IIS

Instalar IIS:

```powershell
Install-WindowsFeature Web-Server, Web-WebSockets, Web-Mgmt-Tools
```

Instalar manualmente:

- URL Rewrite
- Application Request Routing 3.0 (ARR)

Despues de instalar ARR, habilitar proxy:

```powershell
& "$env:windir\system32\inetsrv\appcmd.exe" set config -section:system.webServer/proxy /enabled:"True" /preserveHostHeader:"True" /commit:apphost
iisreset
```

Si aparece:

```text
Seccion de configuracion desconocida: system.webServer/proxy
```

falta instalar ARR.

### Crear sitio en IIS

Crear carpeta:

```powershell
New-Item -ItemType Directory -Force C:\Sites\odoo-logistic\iis
```

En IIS Manager crear sitio:

```text
Nombre: OdooLogistica
Ruta fisica: C:\Sites\odoo-logistic\iis
Tipo: http
IP: Todas las no asignadas
Puerto: 8085
Host name: vacio
```

Crear archivo:

```text
C:\Sites\odoo-logistic\iis\web.config
```

Contenido:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="ReverseProxyToOdoo" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://127.0.0.1:8070/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <webSocket enabled="true" />
  </system.webServer>
</configuration>
```

Reiniciar IIS:

```powershell
iisreset
```

## 12. Abrir firewall para red local

```powershell
New-NetFirewallRule `
  -DisplayName "Odoo IIS 8085" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8085 `
  -Action Allow
```

## 13. Probar acceso

Primero verificar que Odoo corre directo:

```text
http://localhost:8070
```

Luego verificar via IIS:

```text
http://localhost:8085
```

Desde otra PC de la red:

```text
http://IP_DEL_SERVIDOR:8085
```

Ejemplo:

```text
http://10.10.10.8:8085
```

## 14. Arranque automatico con Programador de tareas

Si Odoo se levanta desde consola, no iniciara automaticamente despues de reiniciar el servidor. Para dejarlo automatico, crear una tarea en Windows.

Abrir **Programador de tareas** y seleccionar **Crear tarea**.

En la pestana **General**:

```text
Nombre: OdooLogistica
Ejecutar tanto si el usuario inicio sesion como si no
Ejecutar con los privilegios mas altos
Configurar para: Windows Server 2022
```

En la pestana **Desencadenadores**:

```text
Nuevo
Iniciar la tarea: Al iniciar el sistema
Aceptar
```

En la pestana **Acciones**:

```text
Accion: Iniciar un programa
Programa/script:
C:\Sites\odoo-logistic\odoo\.venv\Scripts\python.exe

Agregar argumentos:
C:\Sites\odoo-logistic\odoo\odoo-bin -c C:\Sites\odoo-logistic\odoo\odoo.conf -d odoo_logistic

Iniciar en:
C:\Sites\odoo-logistic\odoo
```

En la pestana **Condiciones**:

```text
Desmarcar: Iniciar la tarea solo si el equipo esta conectado a corriente
```

En la pestana **Configuracion**:

```text
Permitir que la tarea se ejecute a peticion
Reiniciar cada: 1 minuto
Intentos: 3
Si la tarea ya se esta ejecutando: No iniciar una nueva instancia
```

Al aceptar, Windows pedira la clave del usuario administrador.

Probar la tarea sin reiniciar:

```powershell
Start-ScheduledTask -TaskName "OdooLogistica"
```

Validar acceso:

```text
http://localhost:8070
http://localhost:8085
http://IP_DEL_SERVIDOR:8085
```

## 15. Resetear clave de usuario Odoo

Entrar al shell:

```powershell
cd C:\Sites\odoo-logistic\odoo
.\.venv\Scripts\activate

python .\odoo-bin shell -c .\odoo.conf -d odoo_logistic
```

Listar usuarios:

```python
users = env['res.users'].search([])
for u in users:
    print(u.id, u.login, u.name, u.active)
```

Cambiar password:

```python
user = env['res.users'].browse(2)
user.write({'password': 'Admin2026'})
env.cr.commit()
```

Salir:

```python
exit()
```

## 16. Actualizar el modulo despues de cambios

```powershell
cd C:\Sites\odoo-logistic\OdooLogistica
git pull

cd C:\Sites\odoo-logistic\odoo
.\.venv\Scripts\activate
python .\odoo-bin -c .\odoo.conf -d odoo_logistic -u fleet_vehicle_maintenance_order --stop-after-init
python .\odoo-bin -c .\odoo.conf -d odoo_logistic
```

## 17. Archivos que no deben subirse

No subir:

```text
.venv/
.local_data/
odoo.conf
*.log
filestore/
```

Usar un archivo de ejemplo si se desea documentar configuracion:

```text
odoo.conf.example
```
