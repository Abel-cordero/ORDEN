# ORDEN

Sistema sencillo para registrar órdenes de servicio en un taller de reparación de computadoras, laptops e impresoras.

## Uso rápido

```bash
python ordenes_servicio.py
```

Al ejecutar el script se abre una pequeña ventana en la que se pueden ingresar los datos del cliente y del equipo. La información se almacena en la base de datos `ordenes.db` y se genera un archivo de texto con los detalles de la orden.

## Estructura de la base de datos
- **clientes**: datos del cliente (nombre, dirección, celular, DNI).
- **ordenes_servicio**: información del equipo, descripción de la falla, diagnóstico y solución.

Cada orden recibe un número secuencial que se almacena junto con la fecha de ingreso.
