import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from fpdf import FPDF

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
            dni TEXT,
            fecha_registro TEXT NOT NULL
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
    # Ensure new columns exist when upgrading an old database
    cur.execute("PRAGMA table_info(clientes)")
    columnas = [row[1] for row in cur.fetchall()]
    if "fecha_registro" not in columnas:
        cur.execute("ALTER TABLE clientes ADD COLUMN fecha_registro TEXT")
    conn.commit()


def next_order_number(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT COALESCE(MAX(numero_orden), 0) + 1 FROM ordenes_servicio")
    return cur.fetchone()[0]


def add_cliente(conn: sqlite3.Connection, nombre: str, direccion: str, celular: str, dni: str):
    cur = conn.cursor()
    fecha_registro = datetime.now().isoformat(sep=" ", timespec="minutes")
    cur.execute(
        "INSERT INTO clientes(nombre, direccion, celular, dni, fecha_registro) VALUES (?,?,?,?,?)",
        (nombre, direccion, celular, dni, fecha_registro),
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


def generar_hoja_pdf(conn: sqlite3.Connection, numero_orden: int, destino: Path) -> None:
    """Generate a PDF sheet for the given order number."""
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

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Orden de Servicio N° {num:05d}", ln=True)
    pdf.cell(0, 10, f"Fecha de ingreso: {fecha}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Cliente", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Nombre     : {nombre}", ln=True)
    pdf.cell(0, 8, f"Dirección  : {direccion}", ln=True)
    pdf.cell(0, 8, f"Celular    : {celular}", ln=True)
    pdf.cell(0, 8, f"DNI        : {dni}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Equipo", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Tipo       : {tipo}", ln=True)
    pdf.cell(0, 8, f"Marca      : {marca}", ln=True)
    pdf.cell(0, 8, f"Modelo     : {modelo}", ln=True)
    pdf.cell(0, 8, f"N° Serie   : {serie}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Estado del equipo", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, f"Falla reportada: {falla}")
    pdf.multi_cell(0, 8, f"Diagnóstico    : {diag}")
    pdf.multi_cell(0, 8, f"Solución       : {sol}")
    pdf.ln(10)

    pdf.cell(0, 8, "Observaciones: ________________________________", ln=True)
    pdf.ln(20)
    pdf.cell(90, 8, "Firma Cliente: __________________", ln=False)
    pdf.cell(0, 8, "Firma Técnico: __________________", ln=True)

    pdf.output(str(destino))


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
                generar_hoja_pdf(conn, numero, Path(f"orden_{numero:05d}.pdf"))
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
