# Administrador de Recursos para Linux

Monitor de procesos y recursos de solo lectura con Python, Tkinter y psutil.

## Instalación en Kali Linux

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

**No ejecutes `main.py` con sudo**. El programa rechaza la ejecución como root.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py
```

## Funciones

- CPU, memoria utilizada/total y número de procesos visibles.
- PID, nombre, UID, estado, hilos, CPU %, RAM MB y RAM %.
- Búsqueda, ordenamiento y resalte de los cinco procesos con más CPU.
- Actualización configurable a 1, 2, 3 o 5 segundos, pausa y actualización manual.
- Visibilidad limitada al UID propio por defecto; opción de solicitar otros usuarios.
- Registro de auditoría en `~/.local/state/administrador_recursos/auditoria.log`.
- No lee argumentos (`cmdline`) ni variables de entorno (`environ`), ni modifica procesos.

## Limitaciones

La versión usa **psutil**, no un lector propio de `/proc`. En Linux psutil consulta información del sistema, incluida la expuesta por `/proc`. El filtro de UID es una decisión de visibilidad de la aplicación; no reemplaza los controles de acceso del kernel. La interfaz requiere una sesión gráfica Linux.

## Validación manual pendiente

Ejecuta la aplicación en Kali Linux y comprueba: métricas frente a `top`, búsqueda, pausa, cambios de intervalo, vista de otros usuarios, bitácora y rechazo de ejecución como root. Guarda capturas reales para el informe y la sustentación.
