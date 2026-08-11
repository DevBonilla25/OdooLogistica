def post_init_hook(env):
    env.cr.execute(
        """
        UPDATE fleet_vehicle_log_fuel
        SET approval_state = 'approved'
        WHERE state = 'done'
          AND approval_state = 'draft'
        """
    )
    fuel_logs = env["fleet.vehicle.log.fuel"].search([])
    fuel_logs._compute_previous_odometer()
    fuel_logs._compute_fuel_metrics()
    for fuel_log in fuel_logs:
        fuel_log.amount = fuel_log.fuel_total_cost
        if fuel_log.service_id:
            fuel_log.service_id.amount = fuel_log.fuel_total_cost
