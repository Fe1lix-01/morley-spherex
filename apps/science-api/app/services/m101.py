"""
Servicio de procesamiento y visualización científica de M101.

Lee los cubos FITS de SPHEREx, valida sus datos y genera
una figura PNG con la intensidad, cobertura y máscara de calidad.
"""

from pathlib import Path

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


# Política de visualización para el mosaico de M101.
M101_OVERFLOW_BIT = 1
M101_OUTLIER_BIT = 19


def crear_mascara_m101(
    imagen: np.ndarray,
    hits: np.ndarray,
    flags: np.ndarray,
) -> np.ndarray:
    """
    Genera una máscara de píxeles válidos para visualización.

    Excluye píxeles con intensidad no finita, sin cobertura,
    con cobertura no finita o con flags OVERFLOW y OUTLIER.
    """

    # Comprobamos que los tres arreglos tengan las mismas dimensiones.
    if imagen.shape != hits.shape or imagen.shape != flags.shape:
        raise ValueError(
            "IMAGE, NHITS y FLAGS deben tener dimensiones compatibles."
        )

    # Las banderas deben ser enteros para aplicar operaciones de bits.
    if not np.issubdtype(flags.dtype, np.integer):
        raise ValueError("FLAGS debe contener valores enteros.")

    # Construimos la máscara de bits que deben excluirse.
    bits_excluidos = (
        (1 << M101_OVERFLOW_BIT)
        | (1 << M101_OUTLIER_BIT)
    )

    # Conservamos los píxeles que cumplen todas las condiciones.
    return (
        np.isfinite(imagen)
        & np.isfinite(hits)
        & (hits > 0)
        & ((flags & bits_excluidos) == 0)
    )


def generar_figura_m101(
    archivo: Path,
    ruta_salida: Path,
    canal: int = 63,
) -> None:
    """
    Genera una figura científica de M101 para un canal SPHEREx.

    Parámetros:
        archivo: Ruta del archivo FITS de entrada.
        ruta_salida: Ruta donde se guardará la figura PNG.
        canal: Número de canal espectral que se visualizará.
               Los canales comienzan en 1.

    Raises:
        ValueError: Si los datos FITS no cumplen las validaciones.
    """

    # El canal debe ser un entero mayor o igual a uno; bool no es válido.
    if isinstance(canal, bool) or not isinstance(canal, int) or canal < 1:
        raise ValueError("El canal debe ser un entero mayor o igual a 1.")

    # Normalizamos las rutas recibidas.
    archivo = Path(archivo)
    ruta_salida = Path(ruta_salida)

    # Abrimos el FITS y comprobamos que contenga las extensiones necesarias.
    with fits.open(archivo) as hdul:
        extensiones_requeridas = (
            "IMAGE",
            "NHITS",
            "FLAGS",
            "SPECTRAL_CHANNELS",
        )

        for extension in extensiones_requeridas:
            if extension not in hdul:
                raise ValueError(
                    f"El FITS no contiene la extensión requerida: {extension}."
                )

        # Recuperamos los datos de cada extensión.
        datos_imagen = hdul["IMAGE"].data
        datos_hits = hdul["NHITS"].data
        datos_flags = hdul["FLAGS"].data
        datos_canales = hdul["SPECTRAL_CHANNELS"].data

        # Comprobamos que las extensiones contengan datos.
        if any(
            datos is None
            for datos in (
                datos_imagen,
                datos_hits,
                datos_flags,
                datos_canales,
            )
        ):
            raise ValueError(
                "Una o más extensiones FITS no contienen datos."
            )

        # Convertimos los datos a arreglos NumPy.
        datos_imagen = np.asarray(datos_imagen)
        datos_hits = np.asarray(datos_hits)
        datos_flags = np.asarray(datos_flags)

        # IMAGE, NHITS y FLAGS deben ser cubos tridimensionales.
        if datos_imagen.ndim != 3:
            raise ValueError(
                "La extensión IMAGE debe tener tres dimensiones."
            )

        if datos_hits.ndim != 3:
            raise ValueError(
                "La extensión NHITS debe tener tres dimensiones."
            )

        if datos_flags.ndim != 3:
            raise ValueError(
                "La extensión FLAGS debe tener tres dimensiones."
            )

        # Los tres cubos deben tener exactamente la misma estructura.
        if (
            datos_imagen.shape != datos_hits.shape
            or datos_imagen.shape != datos_flags.shape
        ):
            raise ValueError(
                "Las extensiones IMAGE, NHITS y FLAGS "
                "tienen dimensiones incompatibles."
            )

        # Comprobamos que las banderas sean enteros.
        if not np.issubdtype(datos_flags.dtype, np.integer):
            raise ValueError(
                "La extensión FLAGS debe contener valores enteros."
            )

        # Comprobamos que el canal solicitado exista en el cubo.
        numero_canales = datos_imagen.shape[0]

        if canal > numero_canales:
            raise ValueError(
                f"El FITS contiene solamente {numero_canales} canales."
            )

        # Convertimos el canal, que comienza en 1, a índice de NumPy.
        indice = canal - 1

        # La extensión de metadatos debe contener un registro por canal.
        if len(datos_canales) < numero_canales:
            raise ValueError(
                "SPECTRAL_CHANNELS no contiene metadatos para todos los canales."
            )

        # Comprobamos que exista el campo de longitud de onda.
        nombres_campos = datos_canales.dtype.names or ()

        if "WAVELENGTH" not in nombres_campos:
            raise ValueError(
                "SPECTRAL_CHANNELS no contiene el campo WAVELENGTH."
            )

        # Copiamos los planos para utilizarlos después de cerrar el FITS.
        imagen = datos_imagen[indice].copy()
        hits = datos_hits[indice].copy()
        flags = datos_flags[indice].copy()

        # Recuperamos la longitud de onda correspondiente al canal.
        longitud_onda = float(
            datos_canales["WAVELENGTH"][indice]
        )

    # Validamos que la longitud de onda sea un valor utilizable.
    if not np.isfinite(longitud_onda) or longitud_onda <= 0:
        raise ValueError(
            "La longitud de onda del canal debe ser un valor "
            "finito y positivo."
        )

    # Generamos la máscara reutilizable de calidad para visualización.
    validos = crear_mascara_m101(imagen, hits, flags)

    # Evitamos generar una figura sin información válida.
    if not np.any(validos):
        raise ValueError(
            "No hay píxeles válidos para visualizar este canal."
        )

    # Sustituimos los píxeles inválidos por NaN para excluirlos
    # del cálculo de percentiles y de la visualización.
    imagen_limpia = np.where(validos, imagen, np.nan)

    # Calculamos límites robustos para evitar que valores extremos
    # dominen el contraste de la imagen.
    vmin, vmax = np.nanpercentile(imagen_limpia, [5, 99.5])

    # Matplotlib necesita límites distintos cuando todos los
    # píxeles válidos tienen el mismo valor.
    if vmin == vmax:
        margen = max(abs(float(vmin)) * 1e-6, 1e-12)
        vmin -= margen
        vmax += margen

    # Creamos una figura sin depender de una interfaz gráfica.
    # FigureCanvasAgg permite generar imágenes PNG desde el backend.
    fig = Figure(figsize=(14, 4))
    FigureCanvasAgg(fig)

    # Distribuimos los tres paneles horizontalmente.
    axes = fig.subplots(1, 3)

    try:
        # Panel 1: intensidad científica del canal seleccionado.
        imagen_panel = axes[0].imshow(
            imagen_limpia,
            origin="lower",
            cmap="inferno",
            vmin=vmin,
            vmax=vmax,
        )

        axes[0].set_title(f"M101 - Canal {canal}")

        # Agregamos la escala de intensidad de la imagen.
        fig.colorbar(
            imagen_panel,
            ax=axes[0],
            label="MJy/sr",
            fraction=0.046,
        )

        # Panel 2: cobertura de observaciones por píxel.
        # Los píxeles sin cobertura se mantienen visibles para inspección.
        axes[1].imshow(
            hits,
            origin="lower",
            cmap="viridis",
        )

        axes[1].set_title("Cobertura NHITS")

        # Panel 3: máscara binaria de calidad.
        # Blanco representa píxeles válidos y negro los excluidos.
        axes[2].imshow(
            validos,
            origin="lower",
            cmap="gray",
            vmin=0,
            vmax=1,
        )

        axes[2].set_title("Máscara de calidad")

        # Aplicamos etiquetas espaciales consistentes a los tres paneles.
        for ax in axes:
            ax.set_xlabel("X [píxeles]")
            ax.set_ylabel("Y [píxeles]")

        # Indicamos el objeto y la longitud de onda visualizada.
        fig.suptitle(
            f"SPHEREx M101 - {longitud_onda:.3f} um"
        )

        # Ajustamos el espacio para evitar que títulos y etiquetas
        # se encimen antes de guardar la figura.
        fig.tight_layout()

        # Creamos el directorio de salida si todavía no existe.
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        # Guardamos la figura como PNG.
        fig.savefig(ruta_salida, dpi=180)

    finally:
        # Liberamos los recursos de la figura incluso si ocurre un error.
        fig.clear()
