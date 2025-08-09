# compucell_os.py
# Compucell-Services - Órdenes de Servicio (MVP)
# Python 3.x | Tkinter + SQLite + ReportLab (PDF)
# Autor: ChatGPT para Abel (Compucell)
# Uso: python compucell_os.py

import os
import sqlite3
from datetime import datetime
from tkinter import Tk, StringVar, IntVar, DoubleVar, END, BOTH, LEFT, RIGHT, X, Y, N, E, W
from tkinter import messagebox, filedialog
from tkinter import ttk

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

APP_TITLE = "Compucell-OS (MVP)"
DB_FILE = "compucell.db"
OUT_DIR = os.path.join(".", "salidas")
LOGO_PATH = os.path.join(".", "logo", "logo.png")

MARCAS = [
    "Lenovo","HP","Dell","Asus","MSI","Huawei","Apple","Acer",
    "Epson","Canon","Brother","Samsung","Toshiba"
]
TIPOS = ["Computadora","Laptop","Impresora"]
ESTADOS = ["Ingresado","En diagnóstico","En reparación","Listo","Entregado"]

# ---------- DB ----------
def get_conn():
    return sqlite3.connect(DB_FILE)

def init_dirs():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(".", "logo"), exist_ok=True)

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_completo TEXT NOT NULL,
        direccion TEXT,
        celular TEXT NOT NULL,
        dni TEXT UNIQUE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_dni ON clientes(dni)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cel ON clientes(celular)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS equipos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        marca TEXT NOT NULL,
        modelo TEXT,
        numero_serie TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ordenes_servicio(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_orden TEXT UNIQUE NOT NULL,
        cliente_id INTEGER NOT NULL,
        equipo_id INTEGER NOT NULL,
        falla_reportada TEXT NOT NULL,
        diagnostico TEXT,
        solucion TEXT,
        estado TEXT NOT NULL,
        fecha_ingreso TEXT NOT NULL,
        fecha_entrega TEXT,
        tecnico TEXT,
        costo_mano_obra REAL DEFAULT 0,
        costo_repuestos REAL DEFAULT 0,
        garantia_dias INTEGER DEFAULT 0,
        observaciones TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(equipo_id) REFERENCES equipos(id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orden_num ON ordenes_servicio(numero_orden)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orden_cli ON ordenes_servicio(cliente_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orden_eq ON ordenes_servicio(equipo_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orden_estado ON ordenes_servicio(estado)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orden_fecha ON ordenes_servicio(fecha_ingreso)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS secuencias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anio INTEGER NOT NULL,
        contador INTEGER NOT NULL
    )
    """)
    con.commit()
    con.close()

def next_numero_orden():
    """Genera CS-YYYY-00001 con transacción."""
    year = datetime.now().year
    con = get_conn()
    try:
        con.isolation_level = "EXCLUSIVE"
        cur = con.cursor()
        cur.execute("BEGIN EXCLUSIVE")
        cur.execute("SELECT id, contador FROM secuencias WHERE anio=?", (year,))
        row = cur.fetchone()
        if row is None:
            contador = 1
            cur.execute("INSERT INTO secuencias(anio, contador) VALUES(?,?)", (year, contador))
        else:
            contador = row[1] + 1
            cur.execute("UPDATE secuencias SET contador=? WHERE anio=?", (contador, year))
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise e
    con.close()
    return f"CS-{year}-{contador:05d}"

# ---------- PDF ----------
def draw_label_value(c, x, y, label, value, label_w=42*mm, line_h=5.5*mm):
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, f"{label}:")
    c.setFont("Helvetica", 9)
    c.drawString(x + label_w, y, str(value) if value is not None else "")
    return y - line_h

def render_multiline(c, x, y, w, text, max_lines=5, line_h=5.5*mm):
    if not text:
        return y - line_h
    c.setFont("Helvetica", 9)
    words = text.split()
    line = ""
    lines = []
    for wd in words:
        test = (line + " " + wd).strip()
        if c.stringWidth(test, "Helvetica", 9) > w - 4*mm:
            lines.append(line)
            line = wd
            if len(lines) >= max_lines:
                break
        else:
            line = test
    if len(lines) < max_lines and line:
        lines.append(line)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_h
    return y

def generar_pdf(numero_orden):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    SELECT o.numero_orden, o.fecha_ingreso, o.fecha_entrega, o.estado, o.tecnico,
           o.costo_mano_obra, o.costo_repuestos, o.garantia_dias, o.observaciones,
           o.falla_reportada, o.diagnostico, o.solucion,
           c.nombre_completo, c.direccion, c.celular, c.dni,
           e.tipo, e.marca, e.modelo, e.numero_serie
    FROM ordenes_servicio o
    JOIN clientes c ON o.cliente_id = c.id
    JOIN equipos e ON o.equipo_id = e.id
    WHERE o.numero_orden=?
    """, (numero_orden,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise ValueError("Orden no encontrada para PDF.")

    (nro, f_ing, f_ent, estado, tecnico,
     mano, rep, garantia, obs,
     falla, diag, sol,
     nom, dirc, cel, dni,
     tipo, marca, modelo, serie) = row

    pdf_path = os.path.join(OUT_DIR, f"{nro}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    W, H = A4
    margin = 15*mm

    # Encabezado
    y = H - margin
    if os.path.exists(LOGO_PATH):
        try:
            img = ImageReader(LOGO_PATH)
            # logo alto aprox 18mm
            c.drawImage(img, margin, y-18*mm, width=30*mm, height=18*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin + 35*mm, y-6*mm, "Compucell-Services")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 35*mm, y-12*mm, "Órden de Servicio")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - margin, y-6*mm, f"N° {nro}")
    c.setFont("Helvetica", 9)
    c.drawRightString(W - margin, y-12*mm, datetime.now().strftime("%d/%m/%Y %H:%M"))

    y -= 22*mm
    c.setLineWidth(0.7)
    c.line(margin, y, W - margin, y)
    y -= 4*mm

    # Datos del cliente
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Datos del cliente")
    y -= 7*mm
    y = draw_label_value(c, margin, y, "Nombre", nom)
    y = draw_label_value(c, margin, y, "Dirección", dirc)
    y = draw_label_value(c, margin, y, "Celular", cel)
    y = draw_label_value(c, margin, y, "DNI", dni)
    y -= 4*mm

    # Datos del equipo
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Datos del equipo")
    y -= 7*mm
    y = draw_label_value(c, margin, y, "Tipo", tipo)
    y = draw_label_value(c, margin, y, "Marca", marca)
    y = draw_label_value(c, margin, y, "Modelo", modelo)
    y = draw_label_value(c, margin, y, "N° Serie", serie)
    y -= 4*mm

    # Estado del equipo
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Estado del equipo")
    y -= 7*mm
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "Falla reportada:"); y -= 5.5*mm
    y = render_multiline(c, margin+2*mm, y, W-2*margin, falla, 5)
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "Diagnóstico:"); y -= 5.5*mm
    y = render_multiline(c, margin+2*mm, y, W-2*margin, diag, 6)
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "Solución:"); y -= 5.5*mm
    y = render_multiline(c, margin+2*mm, y, W-2*margin, sol, 6)
    y -= 4*mm

    # Costos y garantía
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Costos y garantía")
    y -= 7*mm
    total = (mano or 0) + (rep or 0)
    y = draw_label_value(c, margin, y, "Mano de obra (S/.)", f"{mano:.2f}" if mano else "0.00")
    y = draw_label_value(c, margin, y, "Repuestos (S/.)", f"{rep:.2f}" if rep else "0.00")
    y = draw_label_value(c, margin, y, "Total (S/.)", f"{total:.2f}")
    y = draw_label_value(c, margin, y, "Garantía (días)", garantia)

    # Fechas y estado
    y -= 2*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Fechas y estado")
    y -= 7*mm
    y = draw_label_value(c, margin, y, "Fecha ingreso", f_ing)
    y = draw_label_value(c, margin, y, "Fecha entrega", f_ent if f_ent else "")
    y = draw_label_value(c, margin, y, "Estado", estado)
    y = draw_label_value(c, margin, y, "Técnico", tecnico)

    # Observaciones
    y -= 2*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Observaciones")
    y -= 7*mm
    y = render_multiline(c, margin+2*mm, y, W-2*margin, obs, 6)

    # Firmas
    y = max(y, 40*mm)
    c.line(margin+10*mm, 35*mm, margin+70*mm, 35*mm)
    c.drawString(margin+25*mm, 30*mm, "Firma del Cliente")
    c.line(W - margin - 70*mm, 35*mm, W - margin - 10*mm, 35*mm)
    c.drawString(W - margin - 55*mm, 30*mm, "Firma del Técnico")

    c.showPage()
    c.save()
    return pdf_path

# ---------- APP ----------
class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1100x720")
        root.minsize(980, 680)

        self.current_order_id = None
        self.current_numero_orden = None
        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        self.tab_nuevo = ttk.Frame(nb)
        self.tab_hist = ttk.Frame(nb)
        nb.add(self.tab_nuevo, text="Nueva Orden")
        nb.add(self.tab_hist, text="Historial")
        nb.pack(fill=BOTH, expand=True)

        self._build_tab_nuevo()
        self._build_tab_hist()

    # ----- TAB NUEVO -----
    def _build_tab_nuevo(self):
        pad = {'padx':8, 'pady':6}

        # Variables
        self.v_nombre = StringVar()
        self.v_direccion = StringVar()
        self.v_celular = StringVar()
        self.v_dni = StringVar()

        self.v_tipo = StringVar(value=TIPOS[0])
        self.v_marca = StringVar()
        self.v_modelo = StringVar()
        self.v_serie = StringVar()

        self.v_falla = StringVar()
        self.v_diag = StringVar()
        self.v_sol = StringVar()

        self.v_estado = StringVar(value=ESTADOS[0])
        self.v_tecnico = StringVar()
        self.v_mano = DoubleVar(value=0.0)
        self.v_rep = DoubleVar(value=0.0)
        self.v_garantia = IntVar(value=0)
        self.v_obs = StringVar()

        self.v_fecha_ing = StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.v_fecha_ent = StringVar(value="")

        top = ttk.LabelFrame(self.tab_nuevo, text="Datos del cliente")
        top.pack(fill=X, **pad)

        ttk.Label(top, text="Nombre completo *").grid(row=0, column=0, sticky=E, **pad)
        ttk.Entry(top, textvariable=self.v_nombre, width=40).grid(row=0, column=1, sticky=W, **pad)

        ttk.Label(top, text="Dirección").grid(row=0, column=2, sticky=E, **pad)
        ttk.Entry(top, textvariable=self.v_direccion, width=40).grid(row=0, column=3, sticky=W, **pad)

        ttk.Label(top, text="Celular *").grid(row=1, column=0, sticky=E, **pad)
        ttk.Entry(top, textvariable=self.v_celular, width=20).grid(row=1, column=1, sticky=W, **pad)

        ttk.Label(top, text="DNI").grid(row=1, column=2, sticky=E, **pad)
        ttk.Entry(top, textvariable=self.v_dni, width=20).grid(row=1, column=3, sticky=W, **pad)

        btn_buscar = ttk.Button(top, text="Buscar cliente (DNI/Celular)", command=self.buscar_cliente_dialog)
        btn_buscar.grid(row=0, column=4, rowspan=2, sticky=N+E+W, **pad)

        # Equipo
        eq = ttk.LabelFrame(self.tab_nuevo, text="Datos del equipo"_
