# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Un `Perfil` por modelo medido, un archivo por modelo.

`dispositivos.py` tiene el mecanismo -la clase `Perfil`, el registro, `activo()`-
y no sabe nada de ningun mouse en particular. Lo que sabe hablarle a **este**
modelo vive aca, uno por archivo: agregar un modelo es agregar un modulo con su
`Perfil` y sumarlo a `dispositivos.PERFILES`, no tocar el mecanismo.
"""
