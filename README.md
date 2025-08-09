# ORDEN

Sistema sencillo para registrar órdenes de servicio en un taller de reparación de computadoras, laptops e impresoras.

## Uso rápido

```bash
python ordenes_servicio.py
```

El script crea la base de datos `ordenes.db`, registra un ejemplo de orden y genera un archivo de texto con los datos de la orden.

## Estructura de la base de datos
- **clientes**: datos del cliente (nombre, dirección, celular, DNI).
- **ordenes_servicio**: información del equipo, descripción de la falla, diagnóstico y solución.

Cada orden recibe un número secuencial que se almacena junto con la fecha de ingreso.
