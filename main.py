#!/usr/bin/env python3
"""Administrador de Recursos para Linux: monitor de solo lectura."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

import psutil

INTERVALOS = (1, 2, 3, 5)


def validar_entorno(platform=None, euid=None):
    platform = sys.platform if platform is None else platform
    euid = os.geteuid() if euid is None else euid
    if not platform.startswith('linux'):
        raise RuntimeError('Este monitor solo funciona en Linux.')
    if euid == 0:
        raise PermissionError('No ejecutes el monitor como root; usa tu cuenta normal.')


def configurar_auditoria(base=None):
    """Bitácora local privada (0700/0600) y rotación a 1 MB."""
    folder = Path(base) if base else Path.home() / '.local/state/administrador_recursos'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(folder, 0o700)
    path = folder / 'auditoria.log'
    # O_NOFOLLOW evita seguir enlaces simbólicos al crear el archivo.
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    os.close(fd)
    os.chmod(path, 0o600)
    logger = logging.getLogger('administrador_recursos')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(handler)
    return logger


def visible_para_usuario(uid_proceso, uid_actual, mostrar_otros=False):
    return mostrar_otros or uid_proceso == uid_actual


def recopilar_procesos(uid_actual, mostrar_otros=False, logger=None):
    """Obtiene metadatos mínimos, sin cmdline ni environ."""
    filas = []
    for proc in psutil.process_iter(['pid', 'name', 'status', 'num_threads', 'memory_info', 'memory_percent']):
        try:
            uid = proc.uids().real
            if not visible_para_usuario(uid, uid_actual, mostrar_otros):
                continue
            info = proc.info
            mem = info.get('memory_info')
            filas.append({
                'pid': info['pid'], 'nombre': info.get('name') or '?',
                'uid': uid, 'estado': info.get('status') or '?',
                'hilos': info.get('num_threads') or 0,
                'cpu': proc.cpu_percent(interval=None),
                'ram_mb': (mem.rss / 1048576) if mem else 0.0,
                'ram_pct': info.get('memory_percent') or 0.0,
            })
        except psutil.AccessDenied:
            if logger:
                logger.warning('ACCESO_DENEGADO | pid=%d', proc.pid)
        except (psutil.NoSuchProcess, psutil.ZombieProcess, ProcessLookupError, OSError):
            continue
    return filas


class Monitor:
    COLUMNAS = ('pid', 'nombre', 'uid', 'estado', 'hilos', 'cpu', 'ram_mb', 'ram_pct')
    TITULOS = ('PID', 'Nombre', 'UID', 'Estado', 'Hilos', 'CPU %', 'RAM MB', 'RAM %')

    def __init__(self, root, logger):
        self.root, self.logger = root, logger
        self.uid = os.getuid()
        self.filas = []
        self.orden = 'cpu'
        self.descendente = True
        self.after_id = None
        self.pausado = tk.BooleanVar(value=False)
        self.otros = tk.BooleanVar(value=False)
        self.intervalo = tk.IntVar(value=3)
        self.buscar = tk.StringVar()
        self.root.title('Administrador de Recursos — Linux')
        self.root.geometry('1160x720')
        self.root.minsize(900, 560)
        self.root.configure(bg='#142039')
        self._interfaz()
        self.buscar.trace_add('write', lambda *_: self.mostrar())
        psutil.cpu_percent(interval=None)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                pass
        self.logger.info('INICIO_SESION | uid=%d', self.uid)
        self.root.protocol('WM_DELETE_WINDOW', self.cerrar)
        self.actualizar()

    def _interfaz(self):
        bg, fg = '#142039', '#f8fafc'
        tk.Label(self.root, text='ADMINISTRADOR DE RECURSOS', bg=bg, fg=fg,
                 font=('Arial', 22, 'bold')).pack(anchor='w', padx=22, pady=(20, 5))
        tk.Label(self.root, text='Monitoreo de CPU, memoria y procesos en Linux',
                 bg=bg, fg='#cbd5e1', font=('Arial', 11)).pack(anchor='w', padx=22)
        cards = tk.Frame(self.root, bg=bg)
        cards.pack(fill='x', padx=18, pady=16)
        self.cpu_label = self._card(cards, 'CPU')
        self.ram_label = self._card(cards, 'RAM')
        self.total_label = self._card(cards, 'PROCESOS VISIBLES')
        self.cpu_bar = ttk.Progressbar(self.root, maximum=100)
        self.cpu_bar.pack(fill='x', padx=25, pady=(0, 6))
        self.ram_bar = ttk.Progressbar(self.root, maximum=100)
        self.ram_bar.pack(fill='x', padx=25, pady=(0, 10))
        ctrl = tk.Frame(self.root, bg=bg)
        ctrl.pack(fill='x', padx=22, pady=8)
        tk.Label(ctrl, text='Buscar:', bg=bg, fg=fg).pack(side='left')
        tk.Entry(ctrl, textvariable=self.buscar, width=20).pack(side='left', padx=7)
        tk.Checkbutton(ctrl, text='Otros usuarios', variable=self.otros, command=self.cambiar_alcance,
                       bg=bg, fg=fg, selectcolor=bg, activebackground=bg,
                       activeforeground=fg).pack(side='left', padx=8)
        tk.Label(ctrl, text='Intervalo (s):', bg=bg, fg=fg).pack(side='left', padx=(5, 2))
        ttk.Combobox(ctrl, textvariable=self.intervalo, values=INTERVALOS,
                     width=3, state='readonly').pack(side='left')
        self.intervalo.trace_add('write', self.cambiar_intervalo)
        tk.Checkbutton(ctrl, text='Pausar', variable=self.pausado, command=self.cambiar_pausa,
                       bg=bg, fg=fg, selectcolor=bg, activebackground=bg,
                       activeforeground=fg).pack(side='left', padx=12)
        ttk.Button(ctrl, text='Actualizar ahora', command=self.actualizar).pack(side='right')
        frame = tk.Frame(self.root)
        frame.pack(fill='both', expand=True, padx=22, pady=(4, 5))
        self.tabla = ttk.Treeview(frame, columns=self.COLUMNAS, show='headings')
        widths = (75, 230, 70, 110, 65, 80, 95, 80)
        for key, label, width in zip(self.COLUMNAS, self.TITULOS, widths):
            self.tabla.heading(key, text=label, command=lambda k=key: self.ordenar(k))
            self.tabla.column(key, width=width, anchor='w' if key == 'nombre' else 'center')
        self.tabla.tag_configure('top5', background='#dbeafe')
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scrollbar.set)
        self.tabla.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.estado = tk.Label(self.root, text='', bg=bg, fg=fg, anchor='w')
        self.estado.pack(fill='x', padx=22, pady=(0, 12))

    def _card(self, parent, titulo):
        frame = tk.Frame(parent, bg='#233451', padx=18, pady=10)
        frame.pack(side='left', expand=True, fill='x', padx=5)
        tk.Label(frame, text=titulo, bg='#233451', fg='#cbd5e1').pack(anchor='w')
        label = tk.Label(frame, text='—', bg='#233451', fg='white', font=('Arial', 19, 'bold'))
        label.pack(anchor='w')
        return label

    def cambiar_alcance(self):
        self.logger.info('CAMBIO_ALCANCE | otros_usuarios=%s', self.otros.get())
        self.actualizar()

    def cambiar_intervalo(self, *_):
        self.logger.info('CAMBIO_INTERVALO | segundos=%d', self.intervalo.get())
        self.programar()

    def cambiar_pausa(self):
        self.logger.info('CAMBIO_PAUSA | pausado=%s', self.pausado.get())
        if not self.pausado.get():
            self.actualizar()
        else:
            self.programar()

    def programar(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if not self.pausado.get():
            self.after_id = self.root.after(self.intervalo.get() * 1000, self.actualizar)

    def actualizar(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            self.filas = recopilar_procesos(self.uid, self.otros.get(), self.logger)
            self.cpu_label.config(text=f'{cpu:.1f} %')
            self.ram_label.config(text=f'{ram.used / (1024**3):.1f} / {ram.total / (1024**3):.1f} GB')
            self.total_label.config(text=str(len(self.filas)))
            self.cpu_bar['value'], self.ram_bar['value'] = cpu, ram.percent
            self.mostrar()
            self.estado.config(text=f'CPU {cpu:.1f}% | RAM {ram.percent:.1f}% | '
                                    f'{len(self.filas)} procesos | '
                                    f'{"Todos los usuarios permitidos" if self.otros.get() else "Mi usuario"}')
        except (psutil.Error, OSError) as exc:
            self.estado.config(text=f'Error al actualizar: {exc}')
            self.logger.error('ERROR_ACTUALIZACION | tipo=%s', type(exc).__name__)
        finally:
            self.programar()

    def mostrar(self):
        texto = self.buscar.get().strip().lower()
        filas = [p for p in self.filas if texto in p['nombre'].lower() or texto in str(p['pid'])]
        filas.sort(key=lambda p: p[self.orden], reverse=self.descendente)
        top5 = {p['pid'] for p in sorted(self.filas, key=lambda p: p['cpu'], reverse=True)[:5]}
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        for p in filas:
            values = (p['pid'], p['nombre'], p['uid'], p['estado'], p['hilos'],
                      f"{p['cpu']:.1f}", f"{p['ram_mb']:.1f}", f"{p['ram_pct']:.2f}")
            self.tabla.insert('', 'end', values=values, tags=('top5',) if p['pid'] in top5 else ())

    def ordenar(self, key):
        self.descendente = not self.descendente if self.orden == key else key in ('cpu', 'ram_mb', 'ram_pct')
        self.orden = key
        self.mostrar()

    def cerrar(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.logger.info('FIN_SESION | uid=%d', self.uid)
        self.root.destroy()


def main():
    try:
        validar_entorno()
        logger = configurar_auditoria()
    except (RuntimeError, PermissionError, OSError) as exc:
        print(f'No se puede iniciar: {exc}', file=sys.stderr)
        return 1
    root = tk.Tk()
    Monitor(root, logger)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
