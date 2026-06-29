# Ordenes de mantenimiento vehicular

Modulo personalizado para Odoo 19 Community orientado a gestionar ordenes de mantenimiento vehicular integradas con Flota, Inventario y Compras.

## Dependencias

- fleet
- product
- stock
- purchase
- mail

## Datos iniciales

El catalogo de sistemas vehiculares se carga automaticamente al instalar el modulo desde:

```text
data/fleet_vehicle_system_data.xml
```

Este archivo funciona como seeder de Odoo. Esta incluido en la clave `data` del `__manifest__.py`, por lo que se ejecuta al instalar o actualizar el modulo en cualquier maquina o servidor.

Sistemas precargados:

- Sistema del Motor: `engine`
- Sistema de Transmision: `transmission`
- Sistema Electrico: `electrical`
- Sistema de Frenos: `brakes`
- Sistema de Suspension: `suspension`
- Sistema de Direccion: `steering`
- Sistema de Escape: `exhaust`
- Llantas y Ruedas: `tires_wheels`
- Lubricantes y Fluidos: `fluids`
- Otros: `other`

Los registros tienen XML IDs estables, por ejemplo:

```text
fleet_vehicle_maintenance_order.vehicle_system_engine
fleet_vehicle_maintenance_order.vehicle_system_transmission
```

El archivo usa `noupdate="1"` para que, despues de instalados, los usuarios puedan ajustar nombres o secuencias sin que una actualizacion del modulo sobrescriba esos cambios.

## Instalacion

Actualizar lista de aplicaciones e instalar:

```powershell
.\.venv\Scripts\python.exe .\odoo-bin -c .\odoo.local.conf -d odoo_fleet -i fleet_vehicle_maintenance_order --stop-after-init
```

Actualizar modulo:

```powershell
.\.venv\Scripts\python.exe .\odoo-bin -c .\odoo.local.conf -d odoo_fleet -u fleet_vehicle_maintenance_order --stop-after-init
```

## Alcance actual

- Ordenes de mantenimiento relacionadas con `fleet.vehicle`.
- Sistemas afectados como checklist.
- Actividades, repuestos y mano de obra.
- Consumo de repuestos desde inventario.
- Creacion de RFQ para repuestos por comprar.
- Trazabilidad con movimientos de inventario y compras.

No crea facturas, asientos contables ni endpoints externos.
