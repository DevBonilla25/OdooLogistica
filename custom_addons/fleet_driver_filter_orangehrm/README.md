# Filtro de choferes OrangeHRM en Flota

Modulo puente para Odoo 19 Community que limita el campo Conductor de Flota a contactos vinculados con empleados sincronizados desde OrangeHRM y marcados como choferes.

El modulo no modifica el core de Odoo ni mezcla la logica de OrangeHRM con las ordenes de mantenimiento. Su objetivo es conectar de forma controlada:

- `fleet.vehicle`
- `res.partner`
- `hr.employee`
- `orangehrm_odoo_users_sync`

## Problema que resuelve

En Flota, el campo Conductor de `fleet.vehicle` usa contactos de Odoo (`res.partner`). Sin un filtro adicional, Odoo puede mostrar muchos contactos que no son choferes operativos.

Este modulo hace que el campo Conductor sugiera solamente contactos laborales vinculados a empleados con:

```text
is_fleet_driver = True
```

## Dependencias

- `fleet`
- `hr`
- `orangehrm_odoo_users_sync`

La dependencia con `orangehrm_odoo_users_sync` es necesaria porque ese modulo agrega el campo `is_fleet_driver` en `hr.employee` y crea o vincula el contacto laboral del empleado mediante `work_contact_id`.

## Estrategia tecnica

En Odoo 19, el campo:

```text
fleet.vehicle.driver_id
```

apunta a:

```text
res.partner
```

Por eso el filtro no se aplica directamente sobre `hr.employee`, sino sobre `res.partner`.

El modulo agrega en `res.partner`:

```text
orangehrm_employee_ids
is_orangehrm_fleet_driver_contact
```

`orangehrm_employee_ids` relaciona contactos con empleados mediante:

```text
hr.employee.work_contact_id
```

`is_orangehrm_fleet_driver_contact` queda en `True` cuando al menos un empleado vinculado al contacto tiene `is_fleet_driver = True`.

## Domain aplicado

El modulo hereda la vista formulario de vehiculos:

```text
fleet.fleet_vehicle_view_form
```

y modifica el campo:

```text
driver_id
```

con el siguiente domain:

```python
['|', ('id', '=', driver_id), ('is_orangehrm_fleet_driver_contact', '=', True)]
```

Esto permite dos comportamientos importantes:

- Al buscar o seleccionar un nuevo conductor, se sugieren solo contactos vinculados a choferes de OrangeHRM.
- Si un vehiculo existente ya tiene asignado un conductor que no cumple el filtro, el formulario sigue abriendo y mostrando ese valor sin error.

## Archivos principales

```text
__manifest__.py
models/res_partner.py
views/fleet_vehicle_views.xml
```

## Instalacion

Actualizar la lista de aplicaciones e instalar:

```text
fleet_driver_filter_orangehrm
```

Tambien puede instalarse por consola, ajustando la ruta de `odoo-bin`, archivo de configuracion y base de datos:

```powershell
python odoo-bin -c tu_config.conf -d tu_base -i fleet_driver_filter_orangehrm --stop-after-init
```

Para actualizar el modulo:

```powershell
python odoo-bin -c tu_config.conf -d tu_base -u fleet_driver_filter_orangehrm --stop-after-init
```

## Pruebas manuales

1. Ejecutar la sincronizacion de empleados desde OrangeHRM.
2. Confirmar que los choferes quedaron marcados en empleados con `is_fleet_driver = True`.
3. Confirmar que esos empleados tienen contacto laboral en `work_contact_id`.
4. Abrir Flota > Vehiculos.
5. Crear o editar un vehiculo.
6. Abrir el campo Conductor.
7. Confirmar que solo aparecen contactos vinculados a choferes de OrangeHRM.
8. Confirmar que contactos de empleados no choferes ya no aparecen en la busqueda.
9. Abrir un vehiculo existente con conductor previamente asignado.
10. Confirmar que el formulario abre sin error aunque ese conductor no cumpla el filtro.

## Alcance

Este modulo solo filtra la seleccion del conductor en el formulario de vehiculos.

No modifica:

- registros existentes de vehiculos,
- empleados,
- contactos,
- logica de sincronizacion OrangeHRM,
- ordenes de mantenimiento,
- core de Odoo.
