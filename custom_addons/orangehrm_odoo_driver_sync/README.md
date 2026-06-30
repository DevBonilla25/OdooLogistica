# OrangeHRM Odoo Driver Sync

Modulo para sincronizar choferes desde OrangeHRM hacia Odoo Flota.

OrangeHRM es el maestro de empleados. Odoo conserva una copia para que los choferes puedan usarse como conductores en Flota.

## Configuracion

1. Instalar el modulo `orangehrm_odoo_driver_sync`.
2. Ir a Flota > Configuracion > OrangeHRM Sync > Configuracion.
3. Crear una configuracion con:
   - URL base de OrangeHRM, por ejemplo `http://192.168.1.10/orangehrm`.
   - Endpoint `/web/index.php/api/v2/pim/employees`.
   - Tipo de autenticacion disponible.
   - Cargos permitidos, un cargo por linea.
4. Usar el boton `Sincronizar choferes desde OrangeHRM`.

## Campos OrangeHRM reconocidos

El importador acepta varios nombres de campo porque el JSON real puede variar segun OrangeHRM:

- ID empleado: `empNumber`, `employeeId`, `id`, `employee_id`.
- Numero empleado: `employeeId`, `employeeNumber`, `employee_number`, `empNumber`.
- Nombre: `name`, `fullName`, `full_name` o combinacion de `firstName`, `middleName`, `lastName`.
- Cargo: `jobTitle.title`, `jobTitle.name`, `job_title`, `jobTitle`, `jobSpecification.title`.
- Estado laboral: `employmentStatus.name`, `employmentStatus.title`, `employment_status`, `employeeStatus`.
- Correo: `workEmail`, `work_email`, `email`, `empWorkEmail`.
- Telefono: `workTelephone`, `work_phone`, `mobile`, `empMobile`, `telephone`.
- Identificacion: `identificationId`, `identification_id`, `nationalId`, `otherId`, `ssnNumber`.

Si OrangeHRM devuelve nombres distintos, ajustar el metodo `_extract_employee_values`.

## Matching para evitar duplicados

El modulo busca empleados en este orden:

1. `orangehrm_employee_id`.
2. `identification_id`.
3. `work_email`.

## Flota

Odoo Flota usa normalmente `res.partner` como conductor del vehiculo. El modulo crea o actualiza el contacto laboral (`work_contact_id`) del empleado sincronizado para que pueda seleccionarse como conductor.

## Logs

Cada sincronizacion crea un registro en Flota > Configuracion > OrangeHRM Sync > Historial con consultados, choferes detectados, creados, actualizados, omitidos y errores.
