# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Puente Linux entre el web driver de szslxd-tech.com y un Attack Shark X8 Pro."""

__version__ = "0.1.0"

# Registra el unico modelo que este codigo sabe hablar. Va aca -y no dentro de
# `dispositivos.py`- porque cada modulo de `perfiles/` importa `Perfil` y
# `Usb` **desde** `dispositivos.py`: si `dispositivos.py` importara a su vez a
# `perfiles/` para poblarse solo, el ciclo no cierra. El import de un paquete
# corre este archivo antes que cualquier submodulo, asi que para cuando algo
# usa `dispositivos.activo()` el registro ya paso. Agregar un modelo es sumar
# una linea aca.
from . import dispositivos as _dispositivos            # noqa: E402
from .perfiles.x8pro import X8_PRO as _X8_PRO          # noqa: E402

_dispositivos.registrar(_X8_PRO, predeterminado=True)
del _dispositivos, _X8_PRO
