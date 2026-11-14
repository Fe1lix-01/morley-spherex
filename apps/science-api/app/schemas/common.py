from typing import Literal

# Banda espectral admitida por los servicios SPHEREx.
Band = Literal[
    "SPHEREx-D1",
    "SPHEREx-D2",
    "SPHEREx-D3",
    "SPHEREx-D4",
    "SPHEREx-D5",
    "SPHEREx-D6",
]

# Detectores físicos admitidos por los datos de SPHEREx.
Detector = Literal[
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
]
