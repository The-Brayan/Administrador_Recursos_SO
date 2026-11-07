
import tkinter as tk
from tkinter import ttk
import psutil


class AdministradorRecursos:
    def __init__(self, root):
        self.root = root
        self.root.title("Administrador de Recursos")
        self.root.geometry("1050x650")
        self.root.minsize(800, 500)
        self.root.configure(bg="#111827")

        self.color_fondo = "#111827"
        self.color_panel = "#1f2937"
        self.color_texto = "#f9fafb"
        self.color_secundario = "#9ca3af"
        self.color_acento = "#38bdf8"

        self.procesos = []
        self.orden = None
        self.direccion = False

        self.configurar_estilos()
        self.crear_interfaz()

        # Inicializar la medición de CPU de los procesos.
        for proceso in psutil.process_iter():
            try:
                proceso.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        psutil.cpu_percent(interval=None)
        self.root.after(1000, self.actualizar)

    def configurar_estilos(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure(
            "Treeview",
            background=self.color_panel,
            foreground=self.color_texto,
            fieldbackground=self.color_panel,
            rowheight=30,
            borderwidth=0,
            font=("Arial", 10)
        )

        estilo.configure(
            "Treeview.Heading",
            background="#374151",
            foreground=self.color_texto,
            font=("Arial", 10, "bold"),
            padding=8
        )

        estilo.map(
            "Treeview",
            background=[("selected", "#075985")],
            foreground=[("selected", "#ffffff")]
        )

        estilo.configure(
            "TProgressbar",
            troughcolor="#374151",
            background=self.color_acento,
            thickness=12
        )

    def crear_interfaz(self):
        # Encabezado
        encabezado = tk.Frame(self.root, bg=self.color_fondo)
        encabezado.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(
            encabezado,
            text="Administrador de Recursos",
            bg=self.color_fondo,
            fg=self.color_texto,
            font=("Arial", 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            encabezado,
            text="Monitor de procesos y rendimiento de Linux",
            bg=self.color_fondo,
            fg=self.color_secundario,
            font=("Arial", 10)
        ).pack(anchor="w", pady=(5, 0))

        # Indicadores superiores
        tarjetas = tk.Frame(self.root, bg=self.color_fondo)
        tarjetas.pack(fill="x", padx=25, pady=12)

        self.cpu_valor = self.crear_tarjeta(
            tarjetas, "USO DE CPU", "0%"
        )
        self.ram_valor = self.crear_tarjeta(
            tarjetas, "MEMORIA RAM", "0%"
        )
        self.procesos_valor = self.crear_tarjeta(
            tarjetas, "PROCESOS ACTIVOS", "0"
        )

        # Barra de CPU y memoria
        panel_recursos = tk.Frame(
            self.root, bg=self.color_panel, padx=15, pady=12
        )
        panel_recursos.pack(fill="x", padx=25, pady=8)

        tk.Label(
            panel_recursos,
            text="CPU",
            bg=self.color_panel,
            fg=self.color_texto,
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.barra_cpu = ttk.Progressbar(
            panel_recursos, maximum=100, mode="determinate"
        )
        self.barra_cpu.grid(
            row=0, column=1, sticky="ew", pady=5
        )

        tk.Label(
            panel_recursos,
            text="RAM",
            bg=self.color_panel,
            fg=self.color_texto,
            font=("Arial", 10, "bold")
        ).grid(
            row=1, column=0, sticky="w", padx=(0, 10)
        )

        self.barra_ram = ttk.Progressbar(
            panel_recursos, maximum=100, mode="determinate"
        )
        self.barra_ram.grid(
            row=1, column=1, sticky="ew", pady=5
        )

        panel_recursos.columnconfigure(1, weight=1)

        # Buscador y botón
        controles = tk.Frame(self.root, bg=self.color_fondo)
        controles.pack(fill="x", padx=25, pady=(12, 8))

        tk.Label(
            controles,
            text="Buscar proceso:",
            bg=self.color_fondo,
            fg=self.color_texto,
            font=("Arial", 10)
        ).pack(side="left", padx=(0, 8))

        self.busqueda = tk.StringVar()
        self.busqueda.trace_add(
            "write", lambda *_: self.mostrar_procesos()
        )

        entrada = tk.Entry(
            controles,
            textvariable=self.busqueda,
            bg=self.color_panel,
            fg=self.color_texto,
            insertbackground=self.color_texto,
            relief="flat",
            font=("Arial", 11)
        )
        entrada.pack(side="left", fill="x", expand=True, ipady=7)

        tk.Button(
            controles,
            text="Actualizar ahora",
            command=self.actualizar,
            bg="#0369a1",
            fg="white",
            activebackground="#0284c7",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=7
        ).pack(side="left", padx=(12, 0))

        # Tabla de procesos
        marco_tabla = tk.Frame(self.root, bg=self.color_panel)
        marco_tabla.pack(
            fill="both", expand=True, padx=25, pady=(5, 10)
        )

        columnas = ("pid", "nombre", "cpu", "memoria")

        self.tabla = ttk.Treeview(
            marco_tabla,
            columns=columnas,
            show="headings"
        )

        self.tabla.heading(
            "pid", text="PID",
            command=lambda: self.ordenar("pid")
        )
        self.tabla.heading(
            "nombre", text="PROCESO",
            command=lambda: self.ordenar("nombre")
        )
        self.tabla.heading(
            "cpu", text="CPU (%)",
            command=lambda: self.ordenar("cpu")
        )
        self.tabla.heading(
            "memoria", text="MEMORIA (%)",
            command=lambda: self.ordenar("memoria")
        )

        self.tabla.column("pid", width=90, anchor="center")
        self.tabla.column("nombre", width=400)
        self.tabla.column("cpu", width=130, anchor="center")
        self.tabla.column("memoria", width=150, anchor="center")

        scroll = ttk.Scrollbar(
            marco_tabla, orient="vertical",
            command=self.tabla.yview
        )
        self.tabla.configure(yscrollcommand=scroll.set)

        self.tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Estado
        self.estado = tk.Label(
            self.root,
            text="Iniciando monitor...",
            bg=self.color_fondo,
            fg=self.color_secundario,
            font=("Arial", 9)
        )
        self.estado.pack(anchor="w", padx=25, pady=(0, 12))

    def crear_tarjeta(self, padre, titulo, valor):
        tarjeta = tk.Frame(
            padre, bg=self.color_panel, padx=18, pady=14
        )
        tarjeta.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(
            tarjeta, text=titulo,
            bg=self.color_panel, fg=self.color_secundario,
            font=("Arial", 9, "bold")
        ).pack(anchor="w")

        etiqueta = tk.Label(
            tarjeta, text=valor,
            bg=self.color_panel, fg=self.color_acento,
            font=("Arial", 22, "bold")
        )
        etiqueta.pack(anchor="w", pady=(5, 0))

        return etiqueta

    def actualizar(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            memoria = psutil.virtual_memory().percent

            self.cpu_valor.config(text=f"{cpu:.1f}%")
            self.ram_valor.config(text=f"{memoria:.1f}%")
            self.barra_cpu["value"] = cpu
            self.barra_ram["value"] = memoria

            nuevos = []

            for proceso in psutil.process_iter(
                ["pid", "name", "memory_percent"]
            ):
                try:
                    datos = proceso.info
                    nuevos.append({
                        "pid": datos["pid"],
                        "nombre": datos["name"] or "Desconocido",
                        "cpu": proceso.cpu_percent(interval=None),
                        "memoria": datos["memory_percent"] or 0
                    })
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess
                ):
                    continue

            self.procesos = nuevos
            self.procesos_valor.config(text=str(len(nuevos)))
            self.mostrar_procesos()

            self.estado.config(
                text=f"Monitor activo | Última actualización correcta | "
                     f"{len(nuevos)} procesos consultados | "
                     f"Actualización automática cada 3 segundos"
            )

        except Exception as error:
            self.estado.config(text=f"Error al actualizar: {error}")

        finally:
            self.root.after(3000, self.actualizar)

    def mostrar_procesos(self):
        if not hasattr(self, "tabla"):
            return

        filtro = self.busqueda.get().lower().strip()

        for elemento in self.tabla.get_children():
            self.tabla.delete(elemento)

        lista = [
            p for p in self.procesos
            if filtro in p["nombre"].lower()
            or filtro in str(p["pid"])
        ]

        if self.orden:
            lista.sort(
                key=lambda p: (
                    p[self.orden] is None,
                    p[self.orden] if p[self.orden] is not None else 0
                ),
                reverse=self.direccion
            )

        for p in lista:
            self.tabla.insert(
                "", "end",
                values=(
                    p["pid"],
                    p["nombre"],
                    f"{p['cpu']:.1f}",
                    f"{p['memoria']:.2f}"
                )
            )

    def ordenar(self, columna):
        if self.orden == columna:
            self.direccion = not self.direccion
        else:
            self.orden = columna
            self.direccion = columna in ("cpu", "memoria")

        self.mostrar_procesos()


if __name__ == "__main__":
    ventana = tk.Tk()
    app = AdministradorRecursos(ventana)
    ventana.mainloop()
import psutil
import time

def mostrar_procesos():
    print("\nADMINISTRADOR DE RECURSOS")
    print("=" * 75)
    print(f"{'PID':<10}{'PROCESO':<30}{'CPU (%)':<15}{'MEMORIA (%)':<15}")
    print("-" * 75)

    for proceso in psutil.process_iter(
        ["pid", "name", "memory_percent"]
    ):
        try:
            datos = proceso.info
            cpu = proceso.cpu_percent(interval=None)
            memoria = datos["memory_percent"] or 0

            print(
                f"{datos['pid']:<10}"
                f"{(datos['name'] or 'Desconocido')[:28]:<30}"
                f"{cpu:<15.2f}"
                f"{memoria:<15.2f}"
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


if __name__ == "__main__":
    for proceso in psutil.process_iter():
        try:
            proceso.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    try:
        while True:
            mostrar_procesos()
            print("\nActualizando en 2 segundos... (Ctrl+C para salir)")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nPrograma finalizado.")
