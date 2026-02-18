# Proyecto (1 página): Simulación de capacidad y colas

## Problema
Dimensionar cupos operativos para evitar esperas altas y rechazos sin perder margen.

## Solución
Simulación de eventos discretos con llegadas Poisson por hora y servicio exponencial.

## Dataset y modelo
- Perfil de llegadas: [10, 13, 18, 22, 26, 24, 23, 20, 18, 16, 14, 11]
- Media de servicio: 22 min
- Cola máxima: 12
- Precio por servicio: USD 18
- Costo por cupo/hora: USD 11.5

## Resultados
- Capacidad recomendada: **9 cupos**
- Espera promedio: **6.3 min**
- Rechazo: **0.9%**
- Margen neto: **USD 2808**

## Decisión
Con 9 cupos y precio de USD 18 se logra un equilibrio entre servicio y rentabilidad.
