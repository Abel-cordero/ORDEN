import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

DB_PATH = Path('ordenes.db')


def get_connection(db_path: Path = DB_PATH):
    """Return a connection to the SQLite database."""
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables needed for the service order system."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            direccion TEXT,
            celular TEXT NOT NULL,
            dni TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ordenes_servicio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_orden INTEGER UNIQUE NOT NULL,
            cliente_id INTEGER NOT NULL,
            tipo_equipo TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            numero_serie TEXT,
            falla_reportada TEXT NOT NULL,
            diagnostico TEXT,
            solucion TEXT,
            fecha_ingreso TEXT NOT NULL,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
        """
    )
    conn.commit()


def next_order_number(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT COALESCE(MAX(numero_orden), 0) + 1 FROM ordenes_servicio")
    return cur.fetchone()[0]


def add_cliente(conn: sqlite3.Connection, nombre: str, direccion: str, celular: str, dni: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clientes(nombre, direccion, celular, dni) VALUES (?,?,?,?)",
        (nombre, direccion, celular, dni),
    )
    conn.commit()
    return cur.lastrowid


def add_orden(
    conn: sqlite3.Connection,
    cliente_id: int,
    tipo_equipo: str,
    marca: str,
    modelo: str,
    numero_serie: str,
    falla: str,
    diagnostico: str,
    solucion: str,
) -> int:
    cur = conn.cursor()
    numero = next_order_number(cur)
    fecha_ingreso = datetime.now().isoformat(sep=" ", timespec="minutes")
    cur.execute(
        """
        INSERT INTO ordenes_servicio(
            numero_orden, cliente_id, tipo_equipo, marca, modelo, numero_serie,
            falla_reportada, diagnostico, solucion, fecha_ingreso
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            numero,
            cliente_id,
            tipo_equipo,
            marca,
            modelo,
            numero_serie,
            falla,
            diagnostico,
            solucion,
            fecha_ingreso,
        ),
    )
    conn.commit()
    return numero


def generar_hoja_txt(conn: sqlite3.Connection, numero_orden: int, destino: Path) -> None:
    """Generate a plain text sheet for the given order number."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.numero_orden, o.tipo_equipo, o.marca, o.modelo, o.numero_serie,
               o.falla_reportada, o.diagnostico, o.solucion, o.fecha_ingreso,
               c.nombre, c.direccion, c.celular, c.dni
        FROM ordenes_servicio o
        JOIN clientes c ON o.cliente_id = c.id
        WHERE o.numero_orden = ?
        """,
        (numero_orden,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No existe la orden {numero_orden}")

    (
        num,
        tipo,
        marca,
        modelo,
        serie,
        falla,
        diag,
        sol,
        fecha,
        nombre,
        direccion,
        celular,
        dni,
    ) = row

    contenido = f"""Orden de Servicio N° {num:05d}
Fecha de ingreso: {fecha}

Cliente
-------
Nombre     : {nombre}
Dirección  : {direccion}
Celular    : {celular}
DNI        : {dni}

Equipo
------
Tipo       : {tipo}
Marca      : {marca}
Modelo     : {modelo}
N° Serie   : {serie}

Estado del equipo
-----------------
Falla reportada: {falla}
Diagnóstico    : {diag}
Solución       : {sol}

Observaciones: ________________________________

Firma Cliente: __________________   Firma Técnico: __________________
"""
    destino.write_text(contenido, encoding="utf-8")


def open_gui() -> None:
    """Open a simple Tkinter form to capture order data."""
    root = tk.Tk()
    root.title("Nueva orden de servicio")

    fields = [
        ("Nombre", "nombre"),
        ("Dirección", "direccion"),
        ("Celular", "celular"),
        ("DNI", "dni"),
        ("Tipo de equipo", "tipo"),
        ("Marca", "marca"),
        ("Modelo", "modelo"),
        ("N° Serie", "serie"),
        ("Falla reportada", "falla"),
        ("Diagnóstico", "diag"),
        ("Solución", "sol"),
    ]

    vars_: dict[str, tk.StringVar] = {}
    for i, (label, key) in enumerate(fields):
        ttk.Label(root, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        ttk.Entry(root, textvariable=var, width=40).grid(row=i, column=1, padx=5, pady=5)
        vars_[key] = var

    def guardar() -> None:
        data = {k: v.get() for k, v in vars_.items()}
        try:
            with get_connection() as conn:
                init_db(conn)
                cliente_id = add_cliente(
                    conn,
                    data["nombre"],
                    data["direccion"],
                    data["celular"],
                    data["dni"],
                )
                numero = add_orden(
                    conn,
                    cliente_id,
                    data["tipo"],
                    data["marca"],
                    data["modelo"],
                    data["serie"],
                    data["falla"],
                    data["diag"],
                    data["sol"],
                )
                generar_hoja_txt(conn, numero, Path(f"orden_{numero:05d}.txt"))
            messagebox.showinfo("Éxito", f"Orden {numero:05d} registrada.")
            for var in vars_.values():
                var.set("")
        except Exception as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Error", str(exc))

    ttk.Button(root, text="Guardar", command=guardar).grid(
        row=len(fields), column=0, columnspan=2, pady=10
    )

    root.mainloop()


if __name__ == "__main__":
    open_gui()
