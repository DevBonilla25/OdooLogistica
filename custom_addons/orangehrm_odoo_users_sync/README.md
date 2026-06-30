# OrangeHRM Odoo Users Sync

Modulo para sincronizar empleados desde OrangeHRM hacia Odoo.

El endpoint principal puede traer solo datos basicos como empNumber, firstName, middleName, lastName, employeeId y terminationId. Con esos datos el modulo crea o actualiza empleados base.

Si OrangeHRM devuelve cargo, el modulo clasifica roles: chofer de flota, vendedor o empleado.

Se mantienen las opciones de autenticacion: sin autenticacion, Bearer token, API key, usuario/contrasena y cookie.

Si aparece 401 Unauthorized, OrangeHRM rechazo la llamada desde Odoo aunque el navegador muestre JSON por tener cookie de sesion.

Instalar como orangehrm_odoo_users_sync y usar Flota > Configuracion > OrangeHRM Sync.
