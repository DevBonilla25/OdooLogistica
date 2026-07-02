```markdown
# OrangeHRM Odoo Users Sync

Modulo para sincronizar empleados desde OrangeHRM hacia Odoo 19 Community.

OrangeHRM se mantiene como maestro de empleados. Odoo guarda una copia sincronizada para Recursos Humanos, Flota y futuras reglas comerciales.

## Funcionalidad

- Consulta empleados desde OrangeHRM usando API JSON.
- Soporta endpoints paginados y trae todas las paginas disponibles.
- Sincroniza empleados hacia `hr.employee`.
- Sincroniza puestos de trabajo hacia `hr.job`.
- Sincroniza departamentos/subunidades hacia `hr.department`.
- Clasifica empleados como:
  - empleado,
  - chofer de flota,
  - vendedor.
- Marca choferes con `is_fleet_driver`.
- Marca vendedores con `is_orangehrm_salesperson`.
- Crea o actualiza el contacto laboral del empleado para que pueda usarse en Flota.
- Evita duplicados usando ID OrangeHRM, identificacion y correo.
- Permite incluir u omitir empleados terminados.
- Registra historial de sincronizaciones con totales y errores.
- Incluye cron diario opcional, desactivado por defecto.

## Endpoints usados

Empleados:

```text
/web/index.php/api/v2/pim/employees
```

Puestos de trabajo:

```text
/web/index.php/api/v2/admin/job-titles
```

Departamentos/subunidades:

```text
/web/index.php/api/v2/admin/subunits
```

El endpoint de empleados puede usar parametros como:

```text
limit=50&offset=0&model=detailed&includeEmployees=onlyCurrent
```

El modulo usa paginacion para traer todos los registros disponibles, no solo la primera pagina.

## Autenticacion

Se mantienen las opciones de autenticacion:

- Sin autenticacion.
- Bearer token.
- API key.
- Usuario/contrasena.
- Cookie.

Si aparece `401 Unauthorized`, OrangeHRM rechazo la llamada desde Odoo aunque el navegador muestre JSON por tener cookie de sesion.

## Campos OrangeHRM en empleados

El modulo agrega campos a `hr.employee`:

- `orangehrm_employee_id`
- `orangehrm_employee_number`
- `orangehrm_job_title_id`
- `orangehrm_job_title`
- `orangehrm_subunit_id`
- `orangehrm_subunit_name`
- `orangehrm_employment_status`
- `orangehrm_termination_id`
- `orangehrm_last_sync_at`
- `orangehrm_sync_role`
- `is_fleet_driver`
- `is_orangehrm_salesperson`
- `driver_type`

Tambien intenta mapear datos nativos de Odoo si vienen desde OrangeHRM:

- nombre,
- correo laboral,
- telefono laboral,
- identificacion,
- puesto de trabajo,
- departamento,
- contacto laboral.

## Puestos y departamentos

El modulo sincroniza catalogos antes de sincronizar empleados.

En `hr.job` guarda:

- ID del puesto OrangeHRM.
- descripcion del puesto OrangeHRM.

En `hr.department` guarda:

- ID de subunidad OrangeHRM.
- codigo de departamento OrangeHRM.
- nivel jerarquico OrangeHRM.

Con esto, los empleados pueden quedar vinculados a su puesto y departamento correspondiente en Odoo.

## Reglas de roles

El rol sincronizado se calcula desde el cargo OrangeHRM.

Si el cargo coincide con la lista de choferes configurada, el empleado queda como:

```text
fleet_driver
```

Si el cargo coincide con la lista de vendedores configurada, queda como:

```text
salesperson
```

Si no coincide con ninguna regla, queda como:

```text
employee
```

La comparacion no distingue mayusculas y permite coincidencias parciales.

## Matching para evitar duplicados

El modulo busca empleados existentes en este orden:

1. `orangehrm_employee_id`.
2. Identificacion/cedula.
3. Correo laboral.

Si encuentra un empleado existente, lo actualiza. Si no existe, lo crea.

## Configuracion en Odoo

Instalar como:

```text
orangehrm_odoo_users_sync
```

Usar el menu:

```text
Empleados > OrangeHRM > Configuracion
```

Desde esa pantalla se configura:

- URL base de OrangeHRM.
- Endpoint de empleados.
- Endpoint de puestos.
- Endpoint de departamentos.
- Tipo de autenticacion.
- Cargos de choferes.
- Cargos de vendedores.
- Sincronizacion de empleados terminados.
- Frecuencia manual o diaria.

## Sincronizacion manual

Desde:

```text
Empleados > OrangeHRM > Configuracion
```

Abrir la configuracion y ejecutar:

```text
Sincronizar empleados desde OrangeHRM
```

Al finalizar se abre el log de sincronizacion.

## Historial

Los logs se revisan en:

```text
Empleados > OrangeHRM > Historial
```

Cada sincronizacion registra:

- empleados consultados,
- empleados sincronizados,
- choferes detectados,
- vendedores detectados,
- creados,
- actualizados,
- omitidos,
- errores,
- mensaje tecnico resumido.

## Pruebas minimas

- Configurar URL base de OrangeHRM.
- Configurar autenticacion.
- Ejecutar sincronizacion manual.
- Validar empleados creados o actualizados.
- Validar puestos sincronizados.
- Validar departamentos sincronizados.
- Confirmar que los choferes quedan marcados como choferes de flota.
- Confirmar que los vendedores quedan marcados como vendedores OrangeHRM.
- Ejecutar una segunda sincronizacion y confirmar que actualiza sin duplicar.
```