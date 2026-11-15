/**
 * Base de conocimiento del asistente de \u00c9TER.
 *
 * Para agregar una respuesta, copia una entrada y cambia:
 *  - q:    la pregunta t\u00edpica (tambi\u00e9n sale como bot\u00f3n sugerido)
 *  - keys: palabras y frases que la gente usar\u00eda (sin\u00f3nimos, sin importar acentos)
 *  - a:    la respuesta (usa \n para saltos de l\u00ednea)
 * Las entradas con "REVISAR" se redactaron a partir del c\u00f3digo; conviene confirmarlas
 * contra la interfaz real.
 */

export type ChatMode = "explorar" | "cientifico";

export type Entry = {
  id: string;
  q: string;
  keys: string[];
  a: string;
  /** true = explica COMO funciona algo (paso a paso), no solo que es. */
  how?: boolean;
};

export const GREETING: Record<ChatMode, string> = {
  explorar:
    "Hola, soy el asistente de \u00c9TER. Te explico c\u00f3mo usar el visor de forma sencilla. \u00bfQu\u00e9 quieres saber?",
  cientifico:
    "Modo cient\u00edfico: detalles t\u00e9cnicos sobre bandas, filtros, datos y contratos. \u00bfQu\u00e9 necesitas?",
};

export const FALLBACK =
  "No tengo una respuesta para eso todav\u00eda. Puedo ayudarte con filtros, men\u00fa, fen\u00f3menos, \u00e9pocas, objetos en movimiento, SIMBAD y el mosaico SPHEREx. Prueba con una de estas:";

/** Ids de las preguntas que salen como botones al abrir cada modo. */
export const FALLBACK_SCI =
  "No consta en el material verificado. Para responderlo har\u00eda falta una prueba o un documento concreto (por ejemplo, una ejecuci\u00f3n con una pareja Level 2 espectralmente compatible). Puedo ayudarte con WCS, fotometr\u00eda, ePSF, ZOGY, hip\u00f3tesis H0\u2013H3, Gaia, el estado de las pruebas, Radon\u2013Nikodym y los datos de SPHEREx. Prueba con una de estas:";

export const SUGGESTED: Record<ChatMode, string[]> = {
  explorar: ["que-es", "filtros", "f-nir", "epocas", "alternar-visor"],
  cientifico: ["m-estado", "m-zogy", "m-h0h3", "m-parejas", "sci-bandas"],
};

export const KNOWLEDGE: Record<ChatMode, Entry[]> = {
  // \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 EXPLORAR \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
  explorar: [
    {
      id: "ayuda",
      q: "\u00bfQu\u00e9 puedes responder?",
      keys: ["ayuda", "ayudar", "puedes", "que sabes", "preguntar", "opciones", "temas"],
      a: "Puedo explicarte c\u00f3mo usar el visor \u00c9TER: los filtros, el men\u00fa, los seis fen\u00f3menos, las \u00e9pocas, los objetos que se mueven, SIMBAD y el mosaico SPHEREx. Elige una pregunta sugerida o escribe la tuya.",
    },
    {
      id: "que-es",
      q: "\u00bfQu\u00e9 es \u00c9TER?",
      keys: ["eter", "proyecto", "morley", "visor", "app", "aplicacion", "para que sirve", "sirve", "que hace", "de que trata", "que es este visor", "que es esto", "que es la pagina"],
      a: "\u00c9TER es un visor divulgativo del Proyecto Morley: una invitaci\u00f3n a explorar c\u00f3mo cambia el cielo al mirar m\u00e1s all\u00e1 de la luz visible.\nPuedes comparar filtros, ajustar cu\u00e1nto se aplican y su luminosidad, y explorar seis tipos de fen\u00f3menos del cosmos.",
    },
    {
      id: "nombre",
      q: "\u00bfPor qu\u00e9 se llama \u00c9TER?",
      keys: ["nombre", "quien es michelson", "quien fue michelson", "quien es morley", "llama", "michelson", "morley", "1887", "historia", "luminifero", "experimento", "pusieron", "puso", "por que se llama", "origen del nombre"],
      a: "Nos inspira el experimento de Michelson y Morley (1887), que busc\u00f3 el \u00e9ter lumin\u00edfero sin hallar evidencia de \u00e9l. El nombre alude a esa historia; no propone un medio f\u00edsico.",
    },
    {
      id: "spherex",
      q: "\u00bfQu\u00e9 es SPHEREx?",
      keys: ["spherex", "que es spherex", "que es la mision spherex", "satelite", "mision", "nasa", "telescopio", "observa", "cada cuanto", "frecuencia", "meses", "cobertura", "cubre", "que satelite"],
      a: "SPHEREx es un sat\u00e9lite de la NASA que observa el cielo en infrarrojo, aproximadamente entre 0.75 y 5 \u00b5m. Cubre todo el cielo cada ~6 meses, por eso se pueden comparar observaciones (\u00e9pocas) de una misma zona.",
    },
    {
      id: "infrarrojo",
      q: "\u00bfQu\u00e9 es la luz infrarroja?",
      keys: ["infrarrojo", "infrarroja", "ir", "luz", "no vemos", "mas alla", "invisible", "que significa infrarrojo", "significa infrarrojo", "que quiere decir infrarrojo", "luz que no se ve", "luz invisible", "luz no visible", "que no vemos"],
      a: "Es luz que el ojo humano no ve, con longitudes de onda m\u00e1s largas que la roja. Atraviesa mejor el polvo que la luz visible, por eso permite sugerir estrellas y regiones ocultas.",
    },
    {
      id: "reales",
      q: "\u00bfLos datos son reales?",
      keys: ["reales", "real", "ciencia real", "es ciencia real", "es una simulacion", "observados", "observado", "simulado", "simulados", "datos", "verdad", "falso", "mediciones", "medicion", "orientativas", "inventada", "inventado", "informacion real", "de verdad"],
      a: "Los filtros de \u00c9TER son representaciones orientativas: no son mediciones ni datos observados de SPHEREx. Las ilustraciones de los fen\u00f3menos son de referencia, no im\u00e1genes observadas.\nEl mosaico SPHEREx DR1 se muestra desde el cubo oficial del archivo IRSA. Algunos objetos pueden ser datos de prueba (simulados).",
    },
    {
      id: "filtros",
      q: "\u00bfQu\u00e9 son los filtros?",
      keys: ["filtro", "filtros", "bandas", "banda", "colores", "cambiar", "aplicar", "comparar", "opciones", "opciones de filtros", "lista de filtros", "cuales filtros", "que filtros hay"],
      a: "Cada filtro es una interpretaci\u00f3n visual del cielo. Hay seis:\n\u2022 Visible (0.38\u20130.75 \u00b5m)\n\u2022 IR cercano (0.75\u20132.5 \u00b5m)\n\u2022 IR medio (2.5\u20135 \u00b5m)\n\u2022 Hielos (2.7\u20134.8 \u00b5m)\n\u2022 T\u00e9rmico (8\u201314 \u00b5m)\n\u2022 Compuesto (varias bandas)\nSPHEREx observa aproximadamente 0.75\u20135 \u00b5m; los rangos del visor son orientativos.",
    },
    {
      id: "f-visible",
      q: "\u00bfQu\u00e9 muestra el filtro Visible?",
      keys: ["filtro visible", "visible", "optico", "ojo humano", "ojo", "luz normal", "luz visible", "normal", "colores reales"],
      a: "Visible (0.38\u20130.75 \u00b5m) es la referencia \u00f3ptica: una aproximaci\u00f3n al cielo que percibe el ojo humano. Sirve para comparar con los dem\u00e1s filtros.",
    },
    {
      id: "f-nir",
      q: "\u00bfQu\u00e9 muestra el filtro IR cercano?",
      keys: ["ir cercano", "infrarrojo cercano", "nir", "cercano"],
      a: "IR cercano (0.75\u20132.5 \u00b5m) sugiere estrellas y regiones ocultas tras el polvo.",
    },
    {
      id: "f-mir",
      q: "\u00bfQu\u00e9 muestra el filtro IR medio?",
      keys: ["ir medio", "infrarrojo medio", "mir", "medio", "polvo calido", "moleculares"],
      a: "IR medio (2.5\u20135 \u00b5m) evoca polvo c\u00e1lido y se\u00f1ales moleculares. Es solo un tramo orientativo del infrarrojo medio.",
    },
    {
      id: "f-ice",
      q: "\u00bfQu\u00e9 muestra el filtro Hielos?",
      keys: ["hielo", "hielos", "ice", "congelado", "congelados", "filtro hielos"],
      a: "Hielos (2.7\u20134.8 \u00b5m) es un realce ilustrativo de bandas asociadas a hielos. No identifica mol\u00e9culas.",
    },
    {
      id: "f-thermal",
      q: "\u00bfQu\u00e9 muestra el filtro T\u00e9rmico?",
      keys: ["termico", "termica", "calor", "temperatura", "emision termica", "filtro termico"],
      a: "T\u00e9rmico (8\u201314 \u00b5m) est\u00e1 fuera del rango de SPHEREx. Es una representaci\u00f3n de emisi\u00f3n t\u00e9rmica, no una temperatura medida.",
    },
    {
      id: "f-comp",
      q: "\u00bfQu\u00e9 muestra el filtro Compuesto?",
      keys: ["compuesto", "falso color", "rojo verde azul", "superpone", "combinar", "filtro compuesto"],
      a: "Compuesto superpone varias bandas en un solo falso color: rojo = t\u00e9rmico, verde = IR, azul = visible. Es una composici\u00f3n ilustrativa.",
    },
    {
      // REVISAR: confirmar nombres y ubicaci\u00f3n de los controles.
      id: "ajustar",
      q: "\u00bfC\u00f3mo ajusto un filtro?",
      keys: ["ajustar", "slider", "sliders", "deslizador", "luminosidad", "brillo", "aplicacion", "intensidad", "control", "controles", "mover filtro", "cuanta luz", "cuanta luz tiene", "cambiar cuanta", "cantidad de luz", "mas luz", "menos luz"],
      a: "Elige un filtro y usa los controles deslizantes del panel para ajustar cu\u00e1nto se aplica y su luminosidad. El cambio se ve al instante en el cielo.",
    },
    {
      // REVISAR: confirmar d\u00f3nde est\u00e1 el bot\u00f3n del men\u00fa.
      id: "menu",
      q: "\u00bfC\u00f3mo abro el men\u00fa?",
      keys: ["menu", "abrir menu", "secciones", "acerca", "hamburguesa", "navegacion", "boton del menu", "donde esta el menu", "donde esta el boton"],
      a: "Abre el men\u00fa desde el bot\u00f3n del encabezado del visor. Tiene tres secciones: Acerca del proyecto, Filtros y Fen\u00f3menos.",
    },
    {
      id: "fenomenos",
      q: "\u00bfQu\u00e9 son los seis fen\u00f3menos?",
      keys: ["fenomeno", "fenomenos", "nebulosa", "nebulosas", "galaxia", "galaxias", "protoestrella", "protoestrellas", "cometa", "cometas", "estructura", "cosmos", "categorias", "seis", "6"],
      a: "Son seis formas de explorar el cosmos: Nebulosas, Galaxias, Protoestrellas, Hielos, Cometas y Estructura. Las ilustraciones son de referencia, no im\u00e1genes observadas.",
    },
    {
      id: "alternar-visor",
      q: "\u00bfC\u00f3mo cambio entre el visor \u00c9TER y el mosaico?",
      keys: ["alternar", "como paso al mosaico", "como paso del visor al mosaico", "paso al mosaico", "pasar del visor", "cambiar visor", "mosaico", "otro visor", "boton de arriba", "pastilla", "switch", "volver", "cambio a spherex", "cambiar a spherex", "ir al mosaico", "pasar al mosaico", "ver spherex", "ver el mosaico"],
      a: "Arriba al centro hay dos botones: \u00abVisor \u00c9TER\u00bb (filtros, \u00e9pocas, SIMBAD, men\u00fa) y \u00abMosaico SPHEREx DR1\u00bb (el mosaico del cielo). Pulsa el que quieras; puedes volver cuando quieras.",
    },
    {
      id: "allwise-spherex",
      q: "\u00bfQu\u00e9 diferencia hay entre AllWISE y SPHEREx DR1?",
      keys: ["allwise", "wise", "spherex dr1", "dr1", "fuente", "diferencia", "cual elegir", "mosaico spherex", "que es el mosaico", "las dos fuentes", "diferencia entre"],
      a: "En el mosaico, \u00abFuente\u00bb elige la imagen de fondo:\n\u2022 AllWISE: mapa infrarrojo de todo el cielo, sirve de referencia visual.\n\u2022 SPHEREx DR1: el mosaico espectral de SPHEREx; muestra un canal (una banda de longitud de onda) a la vez.",
    },
    {
      id: "vistas",
      q: "\u00bfQu\u00e9 hacen \u00abCielo completo\u00bb y \u00abCentro gal\u00e1ctico\u00bb?",
      keys: ["cielo completo", "centro galactico", "vista", "vistas", "full sky", "galactic center", "via lactea", "centro de la galaxia", "centro galaxia", "ir al centro", "todo el cielo", "cielo entero"],
      a: "En el mosaico, \u00abVista\u00bb mueve la c\u00e1mara:\n\u2022 Cielo completo: todo el cielo en un \u00f3valo (360\u00b0).\n\u2022 Centro gal\u00e1ctico: un acercamiento de unos 10\u00b0 al centro de nuestra galaxia.",
    },
    {
      id: "mosaico-falla",
      q: "\u00bfPor qu\u00e9 el mosaico sale en negro o no carga?",
      keys: ["no carga", "pantalla oscura", "cargo", "vacio", "error", "tiles", "no se ve", "en blanco", "cargando", "lento", "vacia", "imagen vacia", "sin imagen", "no sale"],
      a: "Elegir una fuente no garantiza que sus im\u00e1genes (tiles) hayan cargado. Prueba esperar unos segundos, revisar tu conexi\u00f3n, cambiar a AllWISE y volver, o recargar la p\u00e1gina.",
    },
    {
      // REVISAR: confirmar que los gestos coinciden en el visor \u00c9TER.
      id: "mover",
      q: "\u00bfC\u00f3mo me muevo y acerco?",
      keys: ["zoom", "acercar", "alejar", "mover", "arrastrar", "rueda", "navegar", "desplazar", "pan"],
      a: "Arrastra con el mouse para mover el cielo y usa la rueda (o los botones + y \u2212) para acercar o alejar.",
    },
    {
      id: "epocas",
      q: "\u00bfQu\u00e9 son las \u00e9pocas?",
      keys: ["epoca", "epocas", "reproducir", "tiempo", "temporal", "linea del tiempo", "play", "animacion"],
      a: "Una \u00e9poca es una observaci\u00f3n de SPHEREx. Como el sat\u00e9lite cubre todo el cielo cada ~6 meses, comparar \u00e9pocas permite ver c\u00f3mo cambia la posici\u00f3n de un objeto con el tiempo.",
    },
    {
      id: "objetos",
      q: "\u00bfQu\u00e9 son los objetos que se mueven?",
      keys: ["objeto", "objetos", "mueve", "movimiento", "asteroide", "trayectoria", "rastro", "marcador", "marcadores", "candidato", "lineas de movimiento", "lineas", "rayas", "flechas"],
      a: "Son objetos cuya posici\u00f3n cambia entre \u00e9pocas, como asteroides, cometas o estrellas con movimiento. Cada uno se marca en el cielo y, si hay datos suficientes, puede traer una predicci\u00f3n de d\u00f3nde estar\u00e1.",
    },
    {
      id: "como-usar",
      how: true,
      q: "\u00bfC\u00f3mo uso el visor paso a paso?",
      keys: ["como uso", "como se usa", "como empiezo", "empezar", "tutorial", "guia", "paso a paso", "instrucciones", "como funciona el visor", "como funciona la aplicacion", "primeros pasos"],
      a: "As\u00ed se usa el visor \u00c9TER:\n1. Arrastra con el mouse para mover el cielo y usa la rueda para acercar o alejar.\n2. Elige un filtro para ver el cielo con otra interpretaci\u00f3n de luz.\n3. Ajusta cu\u00e1nto se aplica el filtro y su luminosidad con los controles.\n4. Abre el men\u00fa para ver los seis fen\u00f3menos y la informaci\u00f3n del proyecto.\n5. Arriba al centro puedes pasar al Mosaico SPHEREx DR1.",
    },
    {
      id: "como-filtros",
      how: true,
      q: "\u00bfC\u00f3mo funcionan los filtros?",
      keys: ["como funcionan los filtros", "como funciona un filtro", "como trabajan los filtros", "como se hacen los filtros", "que hace un filtro", "como cambia el color", "por que cambian los colores", "como se aplica un filtro"],
      a: "C\u00f3mo funcionan los filtros:\n1. El visor tiene el cielo dividido en canales (visible, infrarrojo, hielos, t\u00e9rmico).\n2. Cada filtro toma uno o varios canales y les pone una paleta de color; por ejemplo, el IR cercano va de negro a \u00e1mbar y crema.\n3. Con los controles eliges cu\u00e1nto se mezcla el filtro con el cielo original y qu\u00e9 tan luminoso se ve.\nEs falso color: sirve para notar diferencias, no para ver colores reales. Los canales son orientativos, no datos observados de SPHEREx.",
    },
    {
      id: "como-epocas",
      how: true,
      q: "\u00bfC\u00f3mo funcionan las \u00e9pocas?",
      keys: ["como funcionan las epocas", "como funciona una epoca", "como trabajan las epocas", "para que sirven las epocas", "como cambio de epoca", "linea del tiempo"],
      a: "C\u00f3mo funcionan las \u00e9pocas:\n1. SPHEREx recorre todo el cielo y lo completa cada ~6 meses; cada pasada es una \u00e9poca.\n2. Cada \u00e9poca guarda una imagen de la zona que miras y la posici\u00f3n de los objetos en ese momento.\n3. Al pasar de una \u00e9poca a otra, el visor cambia la imagen y mueve las marcas a donde estaba cada objeto.\n4. Si un objeto cambia de lugar entre \u00e9pocas, sabemos que se mueve.",
    },
    {
      id: "como-objetos",
      how: true,
      q: "\u00bfC\u00f3mo se detectan los objetos que se mueven?",
      keys: ["como se mueven los objetos", "como detecta", "como se detectan", "como se que algo se mueve", "como saben que se mueve", "como funcionan los objetos", "detectar", "detecta"],
      a: "C\u00f3mo se ven los objetos que se mueven:\n1. Cada objeto trae su posici\u00f3n en cada \u00e9poca.\n2. Si esa posici\u00f3n cambia entre \u00e9pocas, se marca como objeto en movimiento (asteroide, cometa, estrella con movimiento...).\n3. Al cambiar de \u00e9poca, su marca se mueve en el cielo.\n4. Si hay suficientes \u00e9pocas, puede traer una predicci\u00f3n de d\u00f3nde estar\u00e1 despu\u00e9s.",
    },
    {
      id: "como-prediccion",
      how: true,
      q: "\u00bfC\u00f3mo funciona la predicci\u00f3n de un objeto?",
      keys: ["como funciona la prediccion", "como se predice", "como predice", "como adivina", "predecir", "predice", "donde estara"],
      a: "C\u00f3mo funciona la predicci\u00f3n:\n1. Con las posiciones del objeto en varias \u00e9pocas se estima d\u00f3nde estar\u00e1 en una fecha futura.\n2. Esa posici\u00f3n se muestra con un c\u00edrculo de incertidumbre: mientras m\u00e1s grande, menos seguro.\n3. Si no hay suficientes \u00e9pocas, no hay predicci\u00f3n.\nEs una predicci\u00f3n, no una observaci\u00f3n.",
    },
    {
      id: "como-mosaico",
      how: true,
      q: "\u00bfC\u00f3mo funciona el mosaico?",
      keys: ["como funciona el mosaico", "como funcionan los mosaicos", "como se arma el mosaico", "como se forma el mosaico"],
      a: "C\u00f3mo funciona el mosaico:\n1. Es un mapa de todo el cielo dividido en teselas (tiles) a varias resoluciones.\n2. Al acercar, el visor carga teselas m\u00e1s detalladas de esa zona; por eso al principio puede verse borroso o vac\u00edo unos segundos.\n3. En SPHEREx DR1 se muestra un solo canal (una banda de longitud de onda) a la vez.\n4. \u00abFuente\u00bb cambia de mapa y \u00abVista\u00bb mueve la c\u00e1mara.",
    },
    {
      // REVISAR: confirmar c\u00f3mo se activa SIMBAD en la interfaz.
      id: "como-simbad",
      how: true,
      q: "\u00bfC\u00f3mo funciona SIMBAD en el visor?",
      keys: ["como funciona simbad", "como uso simbad", "como se usa simbad", "como consulto simbad"],
      a: "C\u00f3mo funciona SIMBAD en el visor:\n1. SIMBAD es una base de datos astron\u00f3mica del CDS de Estrasburgo; cada objeto tiene un identificador, sus coordenadas, su tipo y la bibliograf\u00eda donde se estudi\u00f3.\n2. Se puede consultar por identificador (el nombre del objeto), por coordenadas o por referencia bibliogr\u00e1fica. El visor la consulta por la zona que miras para mostrar los objetos conocidos.\n3. Al seleccionar un objeto aparece una tarjeta con su informaci\u00f3n.",
    },
    {
      id: "irsa",
      q: "\u00bfQu\u00e9 es IRSA y qu\u00e9 datos de SPHEREx tiene?",
      keys: ["irsa", "ipac", "caltech", "archivo de ciencia infrarroja", "archivo infrarrojo", "donde estan los datos", "donde se guardan los datos", "quien guarda los datos", "de donde vienen los datos"],
      a: "IRSA es el Archivo de Ciencia Infrarroja de NASA/IPAC (Caltech). Ah\u00ed se publican los datos de SPHEREx y de otras misiones infrarrojas. Ofrece las im\u00e1genes espectrales de SPHEREx, el cubo de todo el cielo del lanzamiento DR1, herramientas para recortar y combinar im\u00e1genes, y acceso por Python y por la nube (AWS). El mosaico del visor sale de este archivo.",
    },
    {
      id: "datos-spherex",
      how: true,
      q: "\u00bfC\u00f3mo consigo y uso los datos de SPHEREx?",
      keys: ["como consigo los datos", "como descargo", "descargar datos", "bajar datos", "acceder a los datos", "astroquery", "como uso astroquery", "usar astroquery", "notebook", "notebooks", "cuaderno", "cuadernos", "tutorial de spherex", "tutoriales de spherex", "data explorer", "usar los datos de spherex", "herramientas de spherex", "herramientas de irsa"],
      a: "C\u00f3mo conseguir los datos de SPHEREx en IRSA:\n1. B\u00fascalos y desc\u00e1rgalos con el SPHEREx Data Explorer, con el m\u00f3dulo astroquery de Python o desde la nube (AWS S3).\n2. Para trabajar con ellos hay herramientas: Cutout (recorta una regi\u00f3n), Mosaic (mosaicos de varias longitudes de onda), Spectrophotometry (saca espectros), Source Discovery (encuentra fuentes) y MOST (busca im\u00e1genes donde pasa un objeto del Sistema Solar).\n3. IRSA tiene cuadernos Jupyter de Python con ejemplos paso a paso: https://caltech-ipac.github.io/irsa-tutorials/spherex/\nM\u00e1s informaci\u00f3n: https://irsa.ipac.caltech.edu/Missions/spherex.html",
    },
    {
      id: "wiseview",
      q: "\u00bfQu\u00e9 es WiseView y en qu\u00e9 se parece a \u00c9TER?",
      keys: ["wiseview", "wise view", "byw", "backyard worlds", "flipbook", "parpadeo", "inspiracion", "herramienta parecida", "enanas marrones"],
      a: "WiseView es una herramienta p\u00fablica, hecha para la misi\u00f3n WISE, que muestra im\u00e1genes del mismo punto del cielo en distintas \u00e9pocas como un flipbook que alterna; si un objeto cambia de lugar, se nota que se mueve. El p\u00fablico la ha usado para hacer cientos de descubrimientos. Se parece a la idea de las \u00e9pocas de \u00c9TER: comparar el cielo en el tiempo para ver qu\u00e9 se mueve. Est\u00e1 en http://byw.tools/wiseview",
    },
    {
      id: "gaia",
      q: "\u00bfQu\u00e9 es Gaia y para qu\u00e9 sirve aqu\u00ed?",
      keys: ["gaia", "dr3", "gaia dr3", "estrellas gaia", "catalogo gaia", "paralaje", "movimiento propio"],
      a: "Gaia es la misi\u00f3n de la ESA que midi\u00f3 con mucha precisi\u00f3n posiciones y movimientos de estrellas. Su versi\u00f3n de datos 3 (DR3, 2022) tiene unos 1,800 millones de fuentes, de las que cerca de 1,470 millones tienen astrometr\u00eda completa. Es \u00fatil como referencia de estrellas conocidas para comparar con lo que se ve en el cielo. Para el proyecto se recomienda usar la \u00faltima versi\u00f3n de datos (DR3).",
    },
    {
      id: "neossat",
      q: "\u00bfQu\u00e9 es NEOSSat?",
      keys: ["neossat", "csa", "agencia espacial canadiense", "desechos espaciales", "basura espacial", "satelite canadiense"],
      a: "NEOSSat es el microsat\u00e9lite canadiense de la CSA para vigilar asteroides cercanos a la Tierra y tambi\u00e9n sat\u00e9lites y basura espacial. Tiene un telescopio de 15 cm y orbita a unos 786 km. Fue lanzado en 2013. Sus datos son p\u00fablicos y sirven como ejemplo de c\u00f3mo se detectan y siguen objetos que se mueven. M\u00e1s info: https://www.asc-csa.gc.ca/eng/satellites/neossat/",
    },
    {
      id: "cadc",
      q: "\u00bfQu\u00e9 es el CADC?",
      keys: ["cadc", "centro canadiense de datos astronomicos", "canadian astronomy data centre", "datos astronomicos canadienses"],
      a: "El CADC (Centro Canadiense de Datos Astron\u00f3micos) es un archivo fundado en 1986 por el Consejo Nacional de Investigaci\u00f3n de Canad\u00e1. Guarda observaciones de telescopios y misiones canadienses e internacionales, y sus datos son p\u00fablicos. Sirve para explorar datos cient\u00edficos reales de estrellas, galaxias, asteroides y m\u00e1s. Est\u00e1 en https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/",
    },
    {
      id: "recursos",
      q: "\u00bfD\u00f3nde puedo aprender m\u00e1s y ver datos reales?",
      keys: ["recursos", "enlaces", "links", "mas informacion", "aprender mas", "donde aprendo", "referencias", "paginas utiles", "fuentes de datos", "creditos"],
      a: "Recursos \u00fatiles:\n\u2022 IRSA (datos de SPHEREx): https://irsa.ipac.caltech.edu/Missions/spherex.html\n\u2022 Tutoriales de SPHEREx en Python: https://caltech-ipac.github.io/irsa-tutorials/spherex/\n\u2022 WiseView (im\u00e1genes de WISE en el tiempo): http://byw.tools/wiseview\n\u2022 Datos de Gaia: https://archive.stsci.edu/missions-and-data/gaia\n\u2022 NEOSSat (CSA): https://www.asc-csa.gc.ca/eng/satellites/neossat/\n\u2022 CADC: https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/",
    },
    {
      id: "m-que-es",
      q: "\u00bfQu\u00e9 es MORLEY?",
      keys: ["morley", "que es morley", "proyecto morley", "plataforma", "space apps", "nasa space apps", "concurso", "reto", "desafio", "que hace morley", "de que trata morley", "objetivo del proyecto", "para que sirve morley", "en una frase"],
      a: "MORLEY (\u00c9TER es su visor) es una plataforma experimental que explora im\u00e1genes infrarrojas de SPHEREx y compara observaciones de distintas \u00e9pocas, para estudiar variaciones de brillo y desplazamientos aparentes, siempre con controles de calidad y con el origen de cada dato registrado.\nNo es un telescopio: procesa observaciones que ya existen. Naci\u00f3 para el NASA Space Apps Challenge 2026.\nDatos que usa: AllWISE (fondo visual), SPHEREx HiPS/All-Sky Cube (exploraci\u00f3n espectral), SPHEREx Level 2 (exposiciones individuales para comparar \u00e9pocas) y Gaia como referencia de posiciones.",
    },
    {
      id: "m-planetx",
      q: "\u00bfSe descubri\u00f3 Planet X o un objeto nuevo?",
      keys: ["planet x", "planeta x", "planeta 9", "planet 9", "planeta9", "planeta nueve", "planet nine", "descubrimiento", "descubrieron", "descubrio", "nuevo planeta", "encontraron un planeta", "deteccion confirmada", "se detecto", "hallazgo", "objeto nuevo", "confirmaron"],
      a: "No. Nada en los resultados revisados respalda un descubrimiento astron\u00f3mico ni una detecci\u00f3n real confirmada de movimiento.\nLo que existe son pruebas controladas (sint\u00e9ticas) y an\u00e1lisis preliminares con datos reales que, hasta ahora, no han pasado la validaci\u00f3n espectral. MORLEY es una herramienta para explorar y comparar, no una afirmaci\u00f3n de hallazgo.",
    },
    {
      id: "m-102-fechas",
      q: "\u00bfLas 102 bandas son 102 fechas?",
      keys: ["102 fechas", "102 canales son fechas", "bandas son fechas", "canales o epocas", "bandas vs epocas", "diferencia entre banda y epoca", "canal y epoca", "espectral vs temporal", "eje temporal", "eje espectral", "son 102 observaciones", "102 epocas", "102 observaciones"],
      a: "No. Los 102 canales son longitudes de onda (el \"color\" infrarrojo), no 102 momentos en el tiempo.\nHay tres ejes distintos: el espectral (\u03bb), el temporal (la fecha real de cada exposici\u00f3n) y el espacial (RA/Dec). Para comparar \u00e9pocas se necesitan exposiciones Level 2 con fechas independientes; un mosaico HiPS o un cubo combinado sirve para ver el espectro, no para restar \u00e9pocas.\nPor eso el visor mantiene separados los controles de \u00e9poca y de longitud de onda.",
    },
    {
      id: "m-97",
      q: "\u00bfLa precisi\u00f3n del proyecto es 97.5 %?",
      keys: ["97.5", "97 5", "39/40", "39 de 40", "precision", "que tan preciso", "exactitud", "porcentaje de acierto", "tasa de acierto", "que tan bueno es", "acierta", "fiabilidad"],
      a: "No en cielo real. El 97.5 % es 39 aciertos de 40 clasificaciones (H0\u2013H3) en un experimento sint\u00e9tico controlado, con ruido y fuentes simuladas.\nNo mide el desempe\u00f1o sobre observaciones reales de SPHEREx ni ejecut\u00f3 ZOGY real.\nTipo de evidencia: simulaci\u00f3n.",
    },
    {
      id: "m-interferometro",
      q: "\u00bfMORLEY funciona como un interfer\u00f3metro?",
      keys: ["interferometro", "interferometro real", "es real", "es literal", "interferometro temporal", "michelson morley interferometro", "franjas", "interferencia", "analogia", "como un interferometro", "es literal", "recombina ondas", "interferencia optica"],
      a: "Solo como analog\u00eda. La idea es cancelar lo que dos observaciones tienen en com\u00fan para que aparezca lo que cambi\u00f3. Pero MORLEY no recombina ondas ni produce franjas de interferencia \u00f3ptica coherente como un interfer\u00f3metro f\u00edsico.\nMatem\u00e1ticamente: I\u2082 \u2212 I\u2081 = \u0394S + (B\u2082 \u2212 B\u2081) + (\u03b5\u2082 \u2212 \u03b5\u2081), es decir, el cambio de la se\u00f1al m\u00e1s diferencias de fondo y ruido. Si el fondo, la PSF y la escala est\u00e1n bien controlados, queda el cambio.\nTipo: analog\u00eda conceptual.",
    },
    {
      id: "m-estado",
      q: "\u00bfEn qu\u00e9 estado est\u00e1n las pruebas hoy?",
      keys: ["estado", "estado de las pruebas", "avance", "progreso", "que falta", "pendiente", "pendientes", "resultados", "que se ha probado", "que funciona", "como va el proyecto", "a que fecha", "corte", "en que van", "que hay hecho", "resultados reales"],
      a: "Estado al 14-11-2026:\n\u2022 Se descargaron 5 de 6 recortes FITS de muestra (la sexta respondi\u00f3 HTTP 503).\n\u2022 Se evaluaron 6 parejas temporales: todas con incompatibilidad espectral. La mejor, C001, tiene m\u03bb \u2248 1.5064, separaci\u00f3n de 364.8583 d\u00edas y solapamiento \u2248 0, as\u00ed que qued\u00f3 bloqueada.\n\u2022 Dos consultas a IRSA TAP agotaron el tiempo de espera (problema de acceso, no prueba de que no haya observaciones).\n\u2022 ZOGY: la prueba sint\u00e9tica pas\u00f3 (SNR \u2248 9.5038), pero no hay ZOGY real validado.\n\u2022 Clasificaci\u00f3n H0\u2013H3: 39/40 en simulaci\u00f3n.\nNo consta una detecci\u00f3n real confirmada.",
    },
    {
      id: "m-sin-evidencia",
      q: "\u00bfQu\u00e9 hace el asistente si algo no consta en el material?",
      keys: ["no consta", "no hay evidencia", "falta evidencia", "que pasa si no sabes", "que haces si no sabes", "inventas", "puedes inventar", "confiable", "fuentes del asistente", "de donde sacas"],
      a: "Responde \u00abno consta en el material verificado\u00bb y explica qu\u00e9 prueba har\u00eda falta (por ejemplo, una ejecuci\u00f3n con una pareja Level 2 espectralmente compatible). Nunca inventa un estado PASS ni una detecci\u00f3n.\nDistingue siempre cuatro cosas: teor\u00eda est\u00e1ndar, observaci\u00f3n real, simulaci\u00f3n y propuesta a\u00fan sin validar.",
    },
    {
      id: "m-niveles",
      q: "\u00bfQu\u00e9 significan observed, catalog_prediction, simulation y visualization?",
      keys: ["evidence kind", "evidence_kind", "observed", "catalog prediction", "catalog_prediction", "simulation", "visualization", "niveles de evidencia", "tipo de evidencia", "que tan confiable", "como se distingue", "etiquetas de datos", "observado simulado predicho"],
      a: "Son las etiquetas de procedencia de un dato:\n\u2022 observed: sale de observaciones reales (por ejemplo, FITS Level 2 de SPHEREx).\n\u2022 catalog_prediction: una posici\u00f3n esperada seg\u00fan un cat\u00e1logo (por ejemplo, Gaia propagado en el tiempo).\n\u2022 simulation: datos sint\u00e9ticos o de prueba.\n\u2022 visualization: una imagen para explorar (mosaicos, filtros), no una medici\u00f3n.\nImportante: \u00abobserved\u00bb significa que las entradas son reales, no que el algoritmo haya confirmado movimiento. No se sustituyen datos ausentes por simulaciones sin avisar.",
    },
    {
      // REVISAR: confirmar c\u00f3mo se activa SIMBAD en la interfaz.
      id: "simbad",
      q: "\u00bfQu\u00e9 es SIMBAD?",
      keys: ["simbad", "catalogo", "buscar", "nombre del objeto", "consultar", "base de datos"],
      a: "SIMBAD es una base de datos astron\u00f3mica del CDS de Estrasburgo. Se puede consultar por identificador, por coordenadas o por referencia bibliogr\u00e1fica. El visor puede consultarla para mostrarte informaci\u00f3n de los objetos conocidos en la zona que miras.",
    },
  ],

  // \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 CIENT\u00cdFICO \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
  cientifico: [
    {
      id: "m-pipeline",
      how: true,
      q: "\u00bfCu\u00e1l es la l\u00f3gica matem\u00e1tica y el flujo de an\u00e1lisis?",
      keys: ["pipeline", "flujo", "logica matematica", "logica del proyecto", "paso a paso del analisis", "etapas", "como se analiza", "metodo cientifico", "proceso cientifico", "como procesa", "cadena de analisis", "flujo de trabajo", "como esta armado el analisis"],
      a: "Flujo conceptual:\n1. Selecci\u00f3n de regi\u00f3n (RA/Dec, campo de visi\u00f3n).\n2. Exploraci\u00f3n del cielo (AllWISE y SPHEREx HiPS).\n3. B\u00fasqueda de exposiciones SPHEREx Level 2 y selecci\u00f3n de \u00e9pocas independientes con bandas compatibles.\n4. Validaci\u00f3n de FITS, WCS, m\u00e1scaras, varianza y espectro.\n5. Correcci\u00f3n de fondo, calibraci\u00f3n fotom\u00e9trica y registro astrom\u00e9trico.\n6. Posiciones y flujos con ePSF.\n7. Sustracci\u00f3n ZOGY cuando se cumplan sus condiciones.\n8. Comparaci\u00f3n de hip\u00f3tesis H0\u2013H3.\n9. Contraste astrom\u00e9trico con Gaia e incertidumbre.\n10. Resultado con procedencia \u2192 API \u2192 interfaz.\nObjetivo: distinguir cambios reales de efectos del instrumento o del procesamiento.",
    },
    {
      id: "m-modelo-imagen",
      q: "\u00bfQu\u00e9 modelo matem\u00e1tico describe una imagen observada?",
      keys: ["modelo de imagen", "modelo de observacion", "y_t", "ecuacion de la imagen", "modelo estadistico", "modelo de la imagen", "que es y t", "observacion calibrada", "t*p", "se\u00f1al mas fondo mas ruido", "signal plus noise"],
      a: "En palabras: la imagen es el cielo suavizado por la PSF, escalado, m\u00e1s fondo y ruido.\nF\u00f3rmula: Y\u209c(x,y) \u2248 B\u209c(x,y) + F\u209c\u00b7[T\u209c \u2217 P\u209c](x,y) + \u03b5\u209c(x,y)\nY\u209c imagen observada \u00b7 T\u209c cielo verdadero en esa banda \u00b7 P\u209c PSF efectiva \u00b7 F\u209c escala fotom\u00e9trica \u00b7 B\u209c fondo \u00b7 \u03b5\u209c ruido \u00b7 \u2217 convoluci\u00f3n.\nLimitaci\u00f3n: si cambian a la vez T y la banda, no es leg\u00edtimo atribuir toda la diferencia al tiempo.\nTipo: teor\u00eda est\u00e1ndar.",
    },
    {
      id: "m-ejes",
      q: "\u00bfQu\u00e9 ejes tiene la informaci\u00f3n de SPHEREx (\u03bb, t, \u03b1, \u03b4)?",
      keys: ["ejes", "cubo ideal", "i(alpha", "cobertura uniforme", "matriz completa", "tres ejes", "dimensiones de los datos", "cubo de datos", "cuatro dimensiones", "lambda y t", "historia temporal"],
      a: "Eje espectral \u03bb: color infrarrojo f\u00edsico (absorci\u00f3n, emisi\u00f3n, energ\u00eda). Se obtiene variando la longitud de onda, no el tiempo.\nEje temporal t: fecha real de la observaci\u00f3n (DATE-OBS), para estudiar brillo y posici\u00f3n entre exposiciones.\nEje espacial (\u03b1,\u03b4): regi\u00f3n del cielo.\nUn cubo ideal ser\u00eda I(\u03b1, \u03b4, \u03bb, t), pero los productos disponibles no son necesariamente una matriz completa con cobertura uniforme: hay que comprobar qu\u00e9 muestras existen antes de ofrecer controles en pantalla. No todo p\u00edxel tiene historia temporal completa.",
    },
    {
      id: "m-lvf",
      q: "\u00bfC\u00f3mo mide SPHEREx el espectro (filtros variables lineales)?",
      keys: ["lvf", "filtro variable lineal", "filtros variables lineales", "seis detectores", "6 detectores", "como mide spherex", "respuesta espectral cambia", "apuntado", "por que el pixel cambia de banda", "respuesta del filtro"],
      a: "SPHEREx mide \u2248 0.75\u20135.0 \u00b5m con seis conjuntos detector/filtro variable lineal (LVF). En un LVF, la banda que ve cada p\u00edxel depende de su posici\u00f3n en el detector.\nPor eso el p\u00edxel de una exposici\u00f3n no representa autom\u00e1ticamente el mismo intervalo espectral que el de otra: la respuesta var\u00eda espacialmente y cambia con la configuraci\u00f3n de apuntado. Ese es el motivo de validar la compatibilidad espectral antes de restar \u00e9pocas.\nEl cubo del cielo organiza todo en 102 canales.",
    },
    {
      id: "m-productos-nivel",
      q: "\u00bfQu\u00e9 diferencia hay entre HiPS, All-Sky Cube y Level 2?",
      keys: ["hips vs level 2", "diferencia hips level 2", "level 2", "level2", "exposiciones individuales", "mosaico vs level 2", "que productos usa morley", "que datos usa morley", "fuentes de datos morley", "hips y level 2", "para que sirve level 2", "spectral image level 2"],
      a: "\u2022 AllWISE: fondo contextual y orientaci\u00f3n visual; no reemplaza datos temporales.\n\u2022 SPHEREx DR1 HiPS / All-Sky Cube: exploraci\u00f3n del cielo y canales espectrales; es un producto agregado, no un contador de \u00e9pocas.\n\u2022 SPHEREx Level 2 (Spectral Images): exposiciones individuales FITS multiextensi\u00f3n, con metadatos y fechas; es el insumo principal de la comparaci\u00f3n temporal.\n\u2022 Gaia DR3: referencia astrom\u00e9trica y predicciones de posici\u00f3n, con limitaciones de \u00e9poca, paralaje y geometr\u00eda del observador.\nUn mosaico HiPS no equivale a un par v\u00e1lido de exposiciones para ZOGY.",
    },
    {
      id: "m-extensiones",
      q: "\u00bfQu\u00e9 contienen las extensiones del FITS Level 2 (IMAGE, VARIANCE, FLAGS, ZODI, EPSF)?",
      keys: ["extensiones", "extension fits", "image", "variance", "flags", "zodi", "epsf extension", "que contiene el fits", "que trae un fits", "hdu", "hdus", "mjy/sr", "brillo superficial", "extensiones de level 2"],
      a: "\u2022 IMAGE: brillo superficial calibrado (MJy/sr).\n\u2022 VARIANCE: varianza por p\u00edxel (MJy/sr)\u00b2; \u03c3 = \u221aVARIANCE.\n\u2022 FLAGS: mapa de bits de calidad; su significado depende de las definiciones oficiales de la versi\u00f3n.\n\u2022 ZODI: modelo de luz zodiacal; NO viene sustra\u00eddo de IMAGE.\n\u2022 EPSF: PSF instrumental efectiva, variable en el detector.\n\u2022 WCS-WAVE: centro y ancho de banda aproximados por p\u00edxel (para exploraci\u00f3n).\nHDU = cada unidad de datos dentro del FITS. MJy/sr = megajanskys por estereorradi\u00e1n.",
    },
    {
      id: "m-fits",
      q: "\u00bfQu\u00e9 es un FITS?",
      keys: ["que es un fits", "formato fits", "archivo fits", "fits", "fits aut\u00e9nticos", "fits autenticos", "fits reales"],
      a: "FITS es el formato est\u00e1ndar de la astronom\u00eda: un archivo con una imagen y varias extensiones (HDU) que guardan metadatos, incertidumbres, m\u00e1scaras y modelos del instrumento.\nEn el proyecto, \u00abFITS aut\u00e9nticos\u00bb son los Level 2 reales de SPHEREx; pueden traer restricciones de calibraci\u00f3n y no todo FITS es apto para comparar \u00e9pocas.",
    },
    {
      id: "m-wave",
      q: "\u00bfQu\u00e9 diferencia hay entre WCS-WAVE y CWAVE/CBAND?",
      keys: ["wcs-wave", "wcs wave", "cwave", "cband", "calibracion espectral", "longitud central", "ancho de banda", "visualizacion espectral", "que usar para espectro", "respuesta espectral", "funcion de transmision"],
      a: "\u2022 WCS-WAVE: tabla aproximada de longitud de onda y ancho de banda por p\u00edxel. IRSA la recomienda para visualizaci\u00f3n y prefiltrado, no como calibraci\u00f3n espectral final.\n\u2022 CWAVE (longitud central) y CBAND (ancho de banda): capas de calibraci\u00f3n espectral por p\u00edxel, necesarias para an\u00e1lisis cuantitativos.\nPara ciencia espectral superior se usa adem\u00e1s la funci\u00f3n completa de transmisi\u00f3n R(\u03bb). Nunca se debe tomar WCS-WAVE como calibraci\u00f3n final.",
    },
    {
      id: "m-radec",
      q: "\u00bfQu\u00e9 son RA, Dec e ICRS?",
      keys: ["ra", "dec", "ascension recta", "declinacion", "icrs", "coordenadas celestes", "que son ra y dec", "grados", "marco de referencia celeste"],
      a: "RA (\u03b1, ascensi\u00f3n recta) es la longitud angular celeste, en [0\u00b0, 360\u00b0). Dec (\u03b4, declinaci\u00f3n) es la latitud angular, en [\u221290\u00b0, +90\u00b0]. ICRS es el marco de referencia de esas coordenadas.\nUn grado de RA no mide la misma separaci\u00f3n en todo el cielo: depende de cos \u03b4.",
    },
    {
      id: "m-wcs",
      q: "\u00bfQu\u00e9 es WCS y qu\u00e9 proyecciones se usan?",
      keys: ["wcs", "world coordinate system", "proyeccion", "proyecciones", "tan", "distorsion", "pixel a coordenada", "transformacion de coordenadas", "coordenadas a pixeles", "registro astrometrico", "hammer aitoff", "aitoff"],
      a: "WCS (World Coordinate System) transforma entre coordenadas celestes y p\u00edxeles: (x,y) = WCS\u207b\u00b9(\u03b1,\u03b4) y (\u03b1,\u03b4) = WCS(x,y).\nNo es una regla de tres: depende de la proyecci\u00f3n, orientaci\u00f3n, escala, distorsiones y metadatos. La vista de cielo completo puede usar Hammer-Aitoff (AIT); las vistas peque\u00f1as suelen usar TAN o SIN.\nPara comparar \u00e9pocas hay que comprobar que la fuente cae en el campo \u00fatil de ambas im\u00e1genes y que se registran en un marco com\u00fan.",
    },
    {
      id: "m-sip",
      q: "\u00bfQu\u00e9 advertencia hay con SIP en los FITS?",
      keys: ["sip", "coeficientes sip", "ctype sip", "advertencia de astropy", "warning astropy", "distorsion sip", "sufijo -sip", "discrepancia de cabecera"],
      a: "SIP es un modelo de distorsi\u00f3n dentro del WCS. Los FITS reales probados emitieron avisos de Astropy: coeficientes SIP presentes sin el sufijo -SIP en CTYPE.\nNo se deben descartar ni ignorar autom\u00e1ticamente: hay que verificar la geometr\u00eda y compararla con estrellas de referencia antes de hacer astrometr\u00eda precisa.\nTipo: observaci\u00f3n (FITS reales).",
    },
    {
      id: "m-separacion",
      q: "\u00bfC\u00f3mo se calcula un desplazamiento angular?",
      keys: ["desplazamiento angular", "separacion angular", "segundos de arco", "arcsec", "formula de desplazamiento", "cos dec", "skycoord", "separation", "calcular desplazamiento", "delta theta", "distancia angular"],
      a: "Para desplazamientos peque\u00f1os lejos de los polos, con \u0394\u03b1 y \u0394\u03b4 en grados:\n\u0394\u03b8[arcsec] \u2248 3600 \u00b7 \u221a[(\u0394\u03b1\u00b7cos \u03b4)\u00b2 + (\u0394\u03b4)\u00b2]\nEl cos \u03b4 importa porque un grado de RA no es la misma separaci\u00f3n en todo el cielo. Para \u00e1ngulos grandes se usan relaciones esf\u00e9ricas exactas (por ejemplo SkyCoord.separation).",
    },
    {
      id: "m-prop-mp",
      how: true,
      q: "\u00bfC\u00f3mo se propaga el movimiento propio?",
      keys: ["movimiento propio", "propagacion", "propagar posicion", "mu alpha", "mas por a\u00f1o", "mas/a\u00f1o", "pmra", "pmdec", "propagar movimiento propio", "formula de movimiento propio", "deriva secular"],
      a: "Concepto: el movimiento propio es la deriva secular aparente de una estrella en RA/Dec.\nCon \u03bc\u03b1* = \u03bc\u03b1\u00b7cos \u03b4 y \u03bc\u03b4 en mas/a\u00f1o, para intervalos moderados y lejos de los polos:\n\u03b1(t) \u2248 \u03b1\u2080 + \u03bc\u03b1*\u00b7(t\u2212t\u2080) / (3.6\u00d710\u2076 \u00b7 cos \u03b4\u2080)\n\u03b4(t) \u2248 \u03b4\u2080 + \u03bc\u03b4\u00b7(t\u2212t\u2080) / 3.6\u00d710\u2076\nMagnitud anual: \u03bc = \u221a(\u03bc\u03b1*\u00b2 + \u03bc\u03b4\u00b2) [mas/a\u00f1o].\nLimitaci\u00f3n: esto NO incluye paralaje, el movimiento del observador SPHEREx, perspectiva ni velocidad radial.",
    },
    {
      id: "m-paralaje",
      q: "\u00bfQu\u00e9 es el paralaje y por qu\u00e9 importa?",
      keys: ["paralaje", "posicion del observador", "paralaje anual", "geometria del observador", "efemerides", "observador spherex", "cambio de posicion por el observador"],
      a: "El paralaje es el cambio de posici\u00f3n aparente por el movimiento del observador. Para SPHEREx hay que usar la posici\u00f3n del observatorio y la fecha de cada exposici\u00f3n, no solo el movimiento propio de Gaia.\nUn punto m\u00f3vil del Sistema Solar requiere efem\u00e9rides y geometr\u00eda del observador, no solo movimiento propio estelar.",
    },
    {
      id: "m-gaia-contraste",
      q: "\u00bfPor qu\u00e9 Gaia no confirma autom\u00e1ticamente un movimiento?",
      keys: ["gaia confirma", "gaia no basta", "gaia no alcanza", "gaia no confirma", "por que gaia no", "contraste con gaia", "comparar con gaia", "gaia vs spherex", "residuo gaia", "prediccion gaia", "gaia automaticamente", "validar con gaia", "comprobacion independiente"],
      a: "Gaia entrega un modelo/predicci\u00f3n catalogada. Para contrastarla con SPHEREx hay que propagar en el tiempo, incluir paralaje, incertidumbres, WCS y asociaci\u00f3n de fuente.\nLa comparaci\u00f3n es entre: la predicci\u00f3n Gaia (d\u00f3nde deber\u00eda verse tras transportarla a la fecha y posici\u00f3n del observador), la medici\u00f3n SPHEREx (centroide con ePSF) y el residuo, con incertidumbres y sistem\u00e1ticos.\nUn residuo \u00abSPHEREx vs Gaia\u00bb no es un planeta oculto ni una \u00f3rbita nueva.",
    },
    {
      id: "m-mov-aparente",
      how: true,
      q: "\u00bfUn desplazamiento medido prueba que algo se mueve?",
      keys: ["movimiento aparente", "movimiento real", "desplazamiento real", "medir movimiento", "separar efectos", "que causa un desplazamiento aparente", "errores wcs", "se mueve de verdad", "prueba de movimiento", "movimiento fisico", "como saber si se mueve"],
      a: "No por s\u00ed solo. Una diferencia de posici\u00f3n medida en im\u00e1genes mezcla varios efectos que hay que separar:\n1. Instrumental: forma de la PSF/ePSF y el modelo usado.\n2. Registro WCS y distorsi\u00f3n (SIP).\n3. Paralaje del observador.\n4. Movimiento propio.\n5. Asociaci\u00f3n err\u00f3nea de fuentes.\n6. F\u00edsica real.\nEjemplo real del proyecto: para la fuente A, el desplazamiento aparente pas\u00f3 de \u2248 0.312\u2033 (modelo gaussiano) a \u2248 0.038\u2033 (ePSF). Conclusi\u00f3n v\u00e1lida: la posici\u00f3n depende del modelo instrumental; no v\u00e1lida: \u00abse detect\u00f3 un m\u00f3vil\u00bb.\nHay que reportar siempre las incertidumbres.",
    },
    {
      id: "m-parejas",
      how: true,
      q: "\u00bfQu\u00e9 necesita una pareja de im\u00e1genes para poder restarlas?",
      keys: ["restar imagenes", "comparar epocas", "pareja de imagenes", "pareja temporal", "restar 2025 con 2026", "cualquier imagen", "parejas fits", "criterios de pareja", "seleccion de parejas", "puedo restar", "dos imagenes", "2025 contra 2026", "duplicados", "fechas independientes", "date-obs"],
      a: "No cualquier par vale. Deben:\n1. Cubrir la misma posici\u00f3n.\n2. Ser exposiciones independientes (\u0394t = t\u2082 \u2212 t\u2081 > 0, y no duplicados: se revisa SHA256 e identificadores).\n3. Tener respuestas espectrales compatibles.\n4. Tener controles v\u00e1lidos de ruido, fondo y PSF.\nEn los ensayos se us\u00f3 un umbral exploratorio \u0394t \u2265 180 d\u00edas; no es una ley astron\u00f3mica ni garantiza detecci\u00f3n.\nSi dos filtros son incompatibles, se bloquea la resta aunque las fechas y coordenadas coincidan.",
    },
    {
      id: "m-desajuste",
      how: true,
      q: "\u00bfC\u00f3mo se calcula el desajuste espectral entre dos im\u00e1genes?",
      keys: ["desajuste espectral", "m lambda", "m\u03bb", "m_lambda", "overlap", "solapamiento", "umbral 0.25", "0.25", "compatibilidad espectral", "bandas compatibles", "filtros incompatibles", "incompatibilidad espectral", "como se mide el desajuste"],
      a: "Con \u03bb\u2081, \u03bb\u2082 (centros de banda) y w\u2081, w\u2082 (anchos aproximados):\nm\u03bb = |\u03bb\u2081 \u2212 \u03bb\u2082| / [(w\u2081 + w\u2082)/2]\nSe prob\u00f3 el criterio exploratorio m\u03bb \u2264 0.25. Para bandas rectangulares:\noverlap = max(0, min(\u03bb\u2081+w\u2081/2, \u03bb\u2082+w\u2082/2) \u2212 max(\u03bb\u2081\u2212w\u2081/2, \u03bb\u2082\u2212w\u2082/2)), y la fracci\u00f3n es overlap/min(w\u2081,w\u2082).\nOjo: son aproximaciones de filtros rectangulares, no un umbral universal. Lo m\u00e1s riguroso es comparar las respuestas reales R\u2081(\u03bb) y R\u2082(\u03bb): I\u1d62 \u221d \u222b R\u1d62(\u03bb)\u00b7F_\u03bb(\u03bb) d\u03bb. Si difieren, un cambio puede ser puramente espectral aunque el objeto est\u00e9 fijo.",
    },
    {
      id: "m-seis-parejas",
      q: "\u00bfPor qu\u00e9 fallaron las seis parejas de prueba?",
      keys: ["seis parejas", "6 parejas", "por que fallaron", "c001", "blocked spectral", "blocked_spectral", "review spectral mismatch", "1.5064", "364.8583", "05_science_gate", "pareja c001", "parejas evaluadas", "recortes descargados", "5 de 6"],
      a: "La prevalidaci\u00f3n calcul\u00f3 desajustes espectrales mayores al umbral exploratorio 0.25 en las seis parejas (todas quedaron en REVIEW_SPECTRAL_MISMATCH).\nLa mejor, C001 (2025W39_1A_0331_1 con 2026W39_1A_0563_4), dio m\u03bb \u2248 1.5064, separaci\u00f3n \u2248 364.8583 d\u00edas y solapamiento rectangular \u2248 0 %, y 05_science_gate.py devolvi\u00f3 BLOCKED_SPECTRAL.\nSe descargaron 5 de 6 recortes; la sexta URL de 2026 respondi\u00f3 HTTP 503.\nNo consta una corrida exitosa que confirme una pareja apta para ZOGY real.\nTipo: observaci\u00f3n.",
    },
    {
      id: "m-tap",
      how: true,
      q: "\u00bfQu\u00e9 pas\u00f3 con el servicio TAP y qu\u00e9 hacer si IRSA falla?",
      keys: ["tap", "readtimeout", "timeout", "tiempo de espera", "http 503", "503", "irsa falla", "irsa no responde", "servicio caido", "sia2", "inventario historico", "que hacer si irsa falla", "cache", "error de disponibilidad", "no responde"],
      a: "Dos consultas a IRSA TAP agotaron el tiempo de lectura (~30 s). Es un problema de acceso, no evidencia de que no haya observaciones.\nQu\u00e9 hacer: registrar el error de disponibilidad, conservar cach\u00e9 leg\u00edtima y buscar otra v\u00eda con procedencia (se prepar\u00f3 SIA2 / inventario hist\u00f3rico). Nunca simular en silencio una respuesta real.\nTipo: observaci\u00f3n / procedimiento.",
    },
    {
      id: "m-mascaras",
      q: "\u00bfC\u00f3mo se usan las m\u00e1scaras y FLAGS?",
      keys: ["mascaras", "pixeles validos", "pixeles buenos", "flags bits", "calidad del pixel", "pixel inutilizable", "bits de calidad", "mascara de pixeles", "pixeles malos"],
      a: "Una medici\u00f3n se acepta donde IMAGE sea finita, VARIANCE > 0 y los bits pertinentes de FLAGS indiquen calidad suficiente.\nNo es correcto tratar todo bit distinto de cero como \u00abp\u00edxel inutilizable\u00bb: ciertas banderas informan estados diferentes; hay que consultar las definiciones de la versi\u00f3n.",
    },
    {
      id: "m-fondo-zodi",
      q: "\u00bfQu\u00e9 pasa con el fondo y la luz zodiacal?",
      keys: ["fondo", "luz zodiacal", "zodi", "restar fondo", "doble correccion", "sustraer fondo", "modelo de fondo", "background", "fondo del cielo", "zodiacal"],
      a: "Modelo por p\u00edxel: I\u209a = B\u209a + f\u00b7P\u209a + \u03b5\u209a. B\u209a puede incluir contribuciones instrumentales y astrof\u00edsicas.\nEn SPHEREx, ZODI modela la luz zodiacal y NO viene sustra\u00edda de IMAGE. Para restar fondo hay que evaluar el producto y evitar dobles correcciones.",
    },
    {
      id: "m-varianza",
      q: "\u00bfC\u00f3mo se manejan la varianza, los pesos y las incertidumbres?",
      keys: ["varianza", "pesos", "desviacion estandar", "incertidumbre", "ruido correlacionado", "covarianza", "propagar errores", "sigma", "peso estadistico", "error por pixel", "significancia"],
      a: "\u03c3\u209a = \u221aVARIANCE\u209a. Si los errores son independientes, el peso es w\u209a = 1/\u03c3\u209a\u00b2. Con covarianza entre p\u00edxeles se usa una matriz de covarianza C en lugar de pesos simples.\nLa significancia ingenua se\u00f1al/ruido depende de ese modelo: reproyecci\u00f3n, interpolaci\u00f3n, m\u00e1scaras, brillo de fuentes y fondo pueden correlacionar o cambiar el ruido. Los errores deben propagarse, no darse por desaparecidos.",
    },
    {
      id: "m-fotometria",
      how: true,
      q: "\u00bfC\u00f3mo se mide el brillo (fotometr\u00eda de apertura) y se convierte MJy/sr a Jy?",
      keys: ["fotometria", "fotometria de apertura", "mjy sr a jy", "jy", "flujo", "jansky", "apertura", "anillo", "correccion de apertura", "convertir a jy", "flujo en jy", "angulo solido", "medir brillo", "como se mide el brillo"],
      a: "Concepto: se suma el brillo dentro de un c\u00edrculo alrededor de la fuente y se resta el fondo (a menudo de un anillo exterior).\nCon Level 2 en MJy/sr:\nF\u03bd[Jy] = 10\u2076 \u00b7 \u03a3\u209a\u2208A (I\u03bd,p \u2212 B\u03bd,p)[MJy/sr] \u00b7 \u03a9\u209a[sr]\n\u03a9\u209a es el \u00e1ngulo s\u00f3lido del p\u00edxel. Para ruido independiente y fondo conocido: Var(F\u03bd) \u2248 10\u00b9\u00b2 \u00b7 \u03a3 \u03a9\u209a\u00b2 \u00b7 Var(I\u03bd,p). Si el fondo tambi\u00e9n se estima, hay que sumar su contribuci\u00f3n y las covarianzas.\nPuede requerir correcci\u00f3n de apertura y modelado de fuentes vecinas. Un espectro F\u03bd(\u03bb) son flujos en distintas bandas, no una curva temporal.",
    },
    {
      id: "m-curva-luz",
      q: "\u00bfQu\u00e9 es una curva de luz y en qu\u00e9 se diferencia de un espectro?",
      keys: ["curva de luz", "curvas de luz", "variabilidad", "espectro vs curva de luz", "brillo constante", "chi cuadrada constante", "flujo vs tiempo", "periodo", "curva temporal", "variable"],
      a: "Una curva de luz es el flujo de la misma banda a lo largo del tiempo, F\u03bd(t). Un espectro es el flujo contra la longitud de onda, F\u03bd(\u03bb). No deben confundirse.\nPrueba exploratoria de brillo constante: \u03c7\u00b2const = \u03a3 (F\u1d62 \u2212 F\u0304w)\u00b2 / \u03c3F\u1d62\u00b2, con F\u0304w = \u03a3(F\u1d62/\u03c3F\u1d62\u00b2) / \u03a3(1/\u03c3F\u1d62\u00b2).\nDos mediciones no bastan para reconstruir un per\u00edodo ni para afirmar una clase astrof\u00edsica.",
    },
    {
      id: "m-psf",
      q: "\u00bfQu\u00e9 son la PSF y la ePSF?",
      keys: ["psf", "epsf", "epsf vs psf", "funcion de dispersion", "por que no vemos puntos perfectos", "mancha de una estrella", "sobremuestreo", "fase subpixel", "zona del detector", "psf efectiva", "respuesta instrumental"],
      a: "Una estrella puntual se registra como una mancha: la \u00f3ptica, el detector y el muestreo la extienden. La PSF es esa respuesta; la ePSF es la PSF efectiva instrumental, sobremuestreada, que puede variar con el detector, la zona y la \u00e9poca, y ayuda a reducir sesgos de posici\u00f3n.\nEn un FITS recortado, la ePSF debe elegirse con la zona del detector original, no con la posici\u00f3n en el recorte; hay que respetar el sobremuestreo y la fase subp\u00edxel.",
    },
    {
      id: "m-epsf-ajuste",
      how: true,
      q: "\u00bfC\u00f3mo se ajusta una ePSF a una fuente?",
      keys: ["ajuste epsf", "chi cuadrado", "chi2", "chi cuadrado reducido", "chi2nu", "centroide", "minimizar", "ajustar psf", "como se ajusta la epsf", "ajustar la epsf", "ajuste de fuentes", "chi 2"],
      a: "Modelo local: I\u209a \u2248 B\u209a + f\u00b7P_ePSF(x\u209a \u2212 x\u2080, y\u209a \u2212 y\u2080) + \u03b5\u209a.\nSe estiman el centroide (x\u2080,y\u2080), la amplitud f y el fondo minimizando, con ruido independiente:\n\u03c7\u00b2(\u03d1) = \u03a3\u209a\u2208ROI [I\u209a \u2212 M\u209a(\u03d1)]\u00b2 / VARIANCE\u209a, y \u03c7\u00b2\u03bd = \u03c7\u00b2/(n \u2212 k)\n(n = p\u00edxeles v\u00e1lidos, k = par\u00e1metros). Un \u03c7\u00b2\u03bd menor suele favorecer el ajuste, pero no demuestra que las astrometr\u00edas entre exposiciones est\u00e9n calibradas.",
    },
    {
      id: "m-gauss-epsf",
      q: "\u00bfQu\u00e9 mostraron las pruebas gaussiana vs ePSF?",
      keys: ["gaussiana vs epsf", "gaussiana", "0.312", "0.038", "tabla chi2", "fuente a fuente b", "experimento epsf", "4.0818", "modelo gaussiano", "gaussiana contra epsf", "resultados epsf"],
      a: "Resultados hist\u00f3ricos con datos reales (trabajo previo, no nueva detecci\u00f3n), \u03c7\u00b2\u03bd gaussiana \u2192 ePSF:\n\u2022 Fuente A 2025: 4.0818 \u2192 1.5937\n\u2022 Fuente A 2026: 3.6388 \u2192 1.3551\n\u2022 Fuente B 2025: 2.3342 \u2192 2.0373\n\u2022 Fuente B 2026: 2.5518 \u2192 1.1082\nPara A, el desplazamiento aparente cay\u00f3 de \u2248 0.312\u2033 (gaussiana) a \u2248 0.038\u2033 (ePSF). Conclusi\u00f3n v\u00e1lida: la posici\u00f3n depende del modelo instrumental. No v\u00e1lida: \u00abdetectamos un objeto m\u00f3vil\u00bb.\nTipo: experimento con datos reales.",
    },
    {
      id: "m-fourier",
      q: "\u00bfPara qu\u00e9 sirve Fourier en MORLEY?",
      keys: ["fourier", "transformada de fourier", "fft", "convolucion", "dominio de frecuencias", "teorema de convolucion", "transformada", "frecuencias"],
      a: "La transformada de Fourier convierte la convoluci\u00f3n con la PSF en una multiplicaci\u00f3n: F{T\u2217P} = T\u0302\u00b7P\u0302. Eso permite construir ZOGY en el dominio de frecuencias de forma simple y r\u00e1pida (con FFT).",
    },
    {
      id: "m-zogy",
      q: "\u00bfQu\u00e9 es ZOGY? \u00bfSolo quita ruido?",
      keys: ["zogy", "zackay", "ofek", "gal-yam", "sustraccion propia", "proper image subtraction", "resta optima", "sustraccion optima", "elimina ruido", "quita ruido", "1601.02655", "que es zogy", "resta de imagenes astronomicas"],
      a: "ZOGY es el m\u00e9todo de sustracci\u00f3n propia de im\u00e1genes de Zackay, Ofek y Gal-Yam (2016, ApJ 830, 27). Construye una imagen de diferencia y un estad\u00edstico de detecci\u00f3n que consideran la PSF y el ruido tanto de la referencia como de la nueva imagen.\nNO es \u00abquitar ruido\u00bb: es una sustracci\u00f3n estad\u00edstica de dos im\u00e1genes comparables. Sin calibraci\u00f3n de bandas, WCS y ruido puede producir artefactos.\nTipo: teor\u00eda est\u00e1ndar. Fuente: arxiv.org/abs/1601.02655",
    },
    {
      id: "m-zogy-formulas",
      how: true,
      q: "\u00bfCu\u00e1les son las f\u00f3rmulas de ZOGY (D, P_D, S)?",
      keys: ["formula de zogy", "ecuacion de zogy", "ecuacion de d", "formula de d", "d en fourier", "ecuaciones de zogy", "d gorro", "d hat", "imagen de diferencia", "p_d", "f_d", "puntuacion", "imagen de puntuacion", "correlacion con p_d", "ecuacion 13", "ecuacion 14", "ecuacion 15", "que es d", "que es p_d", "diferencia propia"],
      a: "Con R referencia, N nueva, Pr y Pn sus PSF, Fr y Fn escalas fotom\u00e9tricas, \u03c3r y \u03c3n ruido de fondo:\nD\u0302 = (Fr\u00b7P\u0302r\u00b7N\u0302 \u2212 Fn\u00b7P\u0302n\u00b7R\u0302) / \u221a(\u03c3n\u00b2\u00b7Fr\u00b2\u00b7|P\u0302r|\u00b2 + \u03c3r\u00b2\u00b7Fn\u00b2\u00b7|P\u0302n|\u00b2)\nF_D = Fr\u00b7Fn / \u221a(\u03c3n\u00b2\u00b7Fr\u00b2 + \u03c3r\u00b2\u00b7Fn\u00b2)\nP\u0302_D = Fr\u00b7Fn\u00b7P\u0302r\u00b7P\u0302n / [F_D\u00b7\u221a(\u03c3n\u00b2\u00b7Fr\u00b2\u00b7|P\u0302r|\u00b2 + \u03c3r\u00b2\u00b7Fn\u00b2\u00b7|P\u0302n|\u00b2)]\nS = F_D\u00b7[D \u22c6 P_D] (correlaci\u00f3n)\nD = IFFT(D\u0302) es la diferencia propia; P_D es su PSF efectiva, usada para el filtro de detecci\u00f3n. Con Fr = Fn = 1 queda la forma de la prueba sint\u00e9tica.\nSupuestos: ruido gaussiano independiente y homog\u00e9neo, im\u00e1genes registradas y calibradas. La puntuaci\u00f3n idealizada no es una significancia corregida sobre datos reales.",
    },
    {
      id: "m-zogy-real",
      q: "\u00bfSe ejecut\u00f3 ZOGY con SPHEREx real? \u00bfQu\u00e9 le falta?",
      keys: ["zogy real", "zogy con spherex", "se ejecuto zogy", "falta zogy", "s_corr", "ecuacion 25", "que le falta a zogy", "zogy validado", "zogy con datos reales", "zogy spherex real"],
      a: "No hay una ejecuci\u00f3n validada cient\u00edficamente sobre una pareja espectralmente compatible. La Pr\u00e1ctica 05 hizo una prueba matem\u00e1tica sint\u00e9tica.\nFalta: compatibilidad de respuestas espectrales, coordenadas registradas, ePSF locales en p\u00edxeles nativos, escalas de flujo, fondo, m\u00e1scaras, varianzas, incertidumbre del registro y ruido correlacionado. El prototipo tampoco implementa S_corr (ecuaci\u00f3n 25 del art\u00edculo) ni demuestra control de falsos positivos sobre im\u00e1genes reales.\nEstado: existe c\u00f3digo experimental y una prueba sint\u00e9tica reproducible; ZOGY real validado, pendiente.",
    },
    {
      id: "m-snr",
      q: "\u00bfQu\u00e9 significa SNR 9.5038 y PASS en la Pr\u00e1ctica 05?",
      keys: ["9.5038", "snr 9.5", "practica 05", "pass", "self-test", "self test", "simulation_only", "synthetic_null_std", "0.9950", "128x128", "fuente inyectada", "transitorio sintetico", "prueba sintetica", "practica cinco", "snr"],
      a: "La Pr\u00e1ctica 05 (05_science_gate.py) simula im\u00e1genes de 128\u00d7128, PSF gaussianas de anchos 1.5 y 2.1 p\u00edxeles, ruido independiente \u03c3r = \u03c3n = 2.0, fuentes est\u00e1ticas y un transitorio artificial de amplitud 180.\nResultados: Controlled ZOGY test: PASS, synthetic_null_std \u2248 0.9950, synthetic_injected_snr \u2248 9.5038, y con --self-test: FINAL STATUS: SIMULATION_ONLY.\nEl SNR es de una fuente inyectada artificialmente; no identifica ning\u00fan objeto real. PASS significa que pas\u00f3 el ensayo idealizado. La pareja real C001 sali\u00f3 BLOCKED_SPECTRAL; ambas frases son compatibles: el c\u00e1lculo funciona y ese dato no es apto.\nTipo: simulaci\u00f3n.",
    },
    {
      id: "m-h0h3",
      q: "\u00bfQu\u00e9 son las hip\u00f3tesis H0, H1, H2 y H3?",
      keys: ["h0", "h1", "h2", "h3", "hipotesis", "h0 h1 h2 h3", "cuatro hipotesis", "comparador", "sin cambio", "cambio de brillo", "cambio de posicion", "plantilla", "modelos h"],
      a: "Tras comparar im\u00e1genes comparables, se distingue la forma del cambio:\n\u2022 H0: sin cambio detectable \u2192 D \u2248 ruido.\n\u2022 H1: cambia el flujo, no la posici\u00f3n \u2192 D \u2248 \u0394F\u00b7P_D.\n\u2022 H2: cambia la posici\u00f3n con flujo constante \u2192 D \u2248 F[P_D(q\u2212\u0394q) \u2212 P_D(q)] (residual tipo dipolo).\n\u2022 H3: cambian posici\u00f3n y flujo \u2192 D \u2248 F_new\u00b7P_D(q\u2212\u0394q) \u2212 F_ref\u00b7P_D(q).\nClasificar con H0\u2013H3 no demuestra que un objeto exista, sea un planeta o sea un descubrimiento.",
    },
    {
      id: "m-dipolo",
      how: true,
      q: "\u00bfQu\u00e9 es un dipolo residual y por qu\u00e9 aparece?",
      keys: ["dipolo", "residual positivo negativo", "taylor", "desplazamiento pequeno", "patron positivo negativo", "por que aparece un dipolo", "derivada de la psf", "residual", "residuo positivo negativo"],
      a: "Un dipolo es un par de residuos de signo opuesto muy cerca uno del otro. Aparece cuando una fuente se desplaza un poco: para desplazamientos peque\u00f1os,\nP_D(q\u2212\u0394q) \u2248 P_D(q) \u2212 \u0394x\u00b7\u2202\u2093P_D \u2212 \u0394y\u00b7\u2202\u1d67P_D, de modo que D \u2248 \u2212F(\u0394x\u00b7\u2202\u2093P_D + \u0394y\u00b7\u2202\u1d67P_D) + \u03b5.\nEs compatible con movimiento, pero tambi\u00e9n con errores de registro, de PSF o de calibraci\u00f3n: no es prueba inequ\u00edvoca. Otros residuos: positivo localizado (m\u00e1s se\u00f1al en la \u00e9poca nueva o fuente emergente), negativo (menos se\u00f1al u otras causas) y estructuras extensas (fondo, mala reproyecci\u00f3n o respuesta espectral distinta).",
    },
    {
      id: "m-bic",
      q: "\u00bfQu\u00e9 es el BIC y es una probabilidad?",
      keys: ["bic", "criterio de informacion", "k ln n", "delta bic", "modelo de menor bic", "probabilidad posterior", "chi2 modelo", "seleccion de modelo", "criterio bayesiano", "complejidad del modelo"],
      a: "Para ruido gaussiano conocido: \u03c7\u00b2_H = \u03a3 [D\u1d62 \u2212 M_H,\u1d62]\u00b2/\u03c3\u1d62\u00b2, y BIC_H = \u03c7\u00b2_H + k_H\u00b7ln n (k = par\u00e1metros libres, n = p\u00edxeles independientes). Se elige el modelo de menor BIC y puede reportarse \u0394BIC.\nNO es una probabilidad posterior ni garant\u00eda de descubrimiento. P\u00edxeles correlacionados, otra ROI, degeneraci\u00f3n entre H1 y H3 o una PSF incorrecta invalidan interpretaciones ingenuas.",
    },
    {
      id: "m-validacion-h",
      q: "\u00bfC\u00f3mo fue la prueba controlada H0\u2013H3 (39/40)?",
      keys: ["tabla de confusion", "matriz de confusion", "validacion h0 h3", "prueba controlada historica", "semilla 2026", "10 repeticiones", "snr de pico 20", "10.435", "1.55", "razon de brillo", "prueba h0 h3", "39/40 detalle"],
      a: "Simulaci\u00f3n con calibraciones instrumentales de SPHEREx: semilla 2026, 10 repeticiones por hip\u00f3tesis, SNR de pico 20, movimiento inyectado de +8.0\u2033 este y +6.7\u2033 norte (\u2248 10.435\u2033) y raz\u00f3n de brillo 1.55 en los casos variables.\nResultado: H0 acert\u00f3 9/10 (una vez se predijo H1); H1, H2 y H3 acertaron 10/10 \u2192 39/40 = 97.5 %.\nEs solo ese experimento sint\u00e9tico: no mide precisi\u00f3n astron\u00f3mica real y no ejecut\u00f3 ZOGY real.\nTipo: simulaci\u00f3n.",
    },
    {
      id: "m-rn",
      how: true,
      q: "\u00bfQu\u00e9 papel tiene Radon\u2013Nikodym?",
      keys: ["radon nikodym", "radon-nikodym", "razon de verosimilitud", "verosimilitud", "lambda", "dp1", "densidades", "medida dominada", "teorema de radon", "rn", "likelihood ratio", "densidad de probabilidad", "que es radon"],
      a: "Concepto: al asociar detecciones de varias \u00e9pocas con un objeto, conviene comparar \u00abdatos bajo asociaci\u00f3n\u00bb (P\u2081) contra \u00abdatos bajo fondo\u00bb (P\u2080) con una raz\u00f3n de verosimilitud.\nSi una medida \u03bc domina a ambas, el teorema de Radon\u2013Nikodym permite hablar de densidades dP\u2081/d\u03bc y dP\u2080/d\u03bc, y donde el denominador sea positivo:\n\u039b(z) = (dP\u2081/d\u03bc)/(dP\u2080/d\u03bc)(z), con costo K_\u03bc(z) = \u2212log \u039b(z).\n\u039b > 1 favorece la asociaci\u00f3n; \u039b < 1 favorece el fondo, sujeto a los modelos estad\u00edsticos usados.\nMadurez: propuesta de investigaci\u00f3n, no implementada en el producto. El teorema justifica las densidades; no prueba por s\u00ed mismo que dos algoritmos de asociaci\u00f3n sean equivalentes.",
    },
    {
      id: "m-asignacion",
      how: true,
      q: "\u00bfCu\u00e1l es el problema de asignaci\u00f3n y su funci\u00f3n objetivo?",
      keys: ["x_ito", "x ito", "asignacion", "funcion objetivo", "j=gamma", "y_o", "penalizacion gamma", "restricciones", "asociar detecciones", "asociacion de detecciones", "problema de asignacion", "min j", "variable binaria", "detecciones y objetos"],
      a: "Con detecciones i, \u00e9pocas t y objetos candidatos o:\n\u2022 x_ito \u2208 {0,1}: asigna la detecci\u00f3n i de la \u00e9poca t al candidato o.\n\u2022 y_o \u2208 {0,1}: activa el candidato o.\n\u2022 \u039b_ito: raz\u00f3n de verosimilitud asociaci\u00f3n vs fondo.\n\u2022 \u03b3 > 0: penalizaci\u00f3n por proponer demasiados objetos.\nObjetivo propuesto: min J = \u03b3\u00b7\u03a3_o y_o \u2212 \u03a3_{i,t,o} x_ito\u00b7log \u039b_ito\nsujeto a \u03a3_o x_ito \u2264 1 (una detecci\u00f3n no va a dos objetos) y x_ito \u2264 y_o (no se asigna a un objeto desactivado).\nFaltar\u00edan m\u00e1s restricciones y pruebas (cadencias, trayectorias, no-detecciones, objetos nuevos). Formulaci\u00f3n a\u00fan por validar.\nTipo: propuesta de investigaci\u00f3n.",
    },
    {
      id: "m-invariancia",
      how: true,
      q: "\u00bfCu\u00e1l es la condici\u00f3n de invariancia de costos y la estabilidad?",
      keys: ["invariancia", "invariancia de costos", "kernel", "ker t", "nucleo", "equivalencia", "equivalencia de optimizadores", "espacio cociente", "c_mu", "cmu", "minimizadores", "estabilidad", "brecha", "cota", "condicion algebraica", "mismos minimizadores", "operador de diferencias"],
      a: "Sea F = {x \u2208 {0,1}^m : Ax = b} el conjunto factible, con costos J_G = c_G\u1d40x (gaussiano) y J_\u03bc = c_\u03bc\u1d40x (otra verosimilitud).\n\u2022 Si c_\u03bc = a\u00b7c_G + A\u1d40u + r, entonces J_\u03bc(x) = a\u00b7J_G(x) + u\u1d40b + r\u1d40x. Con r = 0 y a > 0 el t\u00e9rmino u\u1d40b es constante: ambos problemas tienen los mismos minimizadores.\n\u2022 Con T(c)(x) = c\u1d40(x \u2212 x\u2080), una condici\u00f3n suficiente es c_\u03bc \u2212 a\u00b7c_G \u2208 ker T, a > 0.\n\u2022 Estabilidad: si x*_G es el \u00f3ptimo \u00fanico y \u0394 = m\u00edn [J_G(x) \u2212 J_G(x*_G)] > 0, el \u00f3ptimo se conserva si m\u00e1x |r\u1d40(x \u2212 x*_G)| < a\u00b7\u0394.\nEs una propiedad algebraica condicional, no una consecuencia autom\u00e1tica de Radon\u2013Nikodym; su utilidad sobre el cat\u00e1logo real sigue sin validar.\nTipo: propuesta de investigaci\u00f3n.",
    },
    {
      id: "m-rn-originalidad",
      q: "\u00bfRadon\u2013Nikodym es un teorema nuevo o ya est\u00e1 implementado?",
      keys: ["rn demuestra", "originalidad", "nuevo teorema", "teorema nuevo", "inventaron radon", "ley nueva", "es original", "aporte teorico", "que puede decir morley sobre rn", "implementado", "optimizador en el backend", "ya esta en produccion", "demostraron un teorema"],
      a: "No. MORLEY no invent\u00f3 el teorema de Radon\u2013Nikodym ni demostr\u00f3 un nuevo teorema universal, y el optimizador no est\u00e1 implementado en el backend.\nLo que puede decirse: \u00abMORLEY estudia una formulaci\u00f3n de asignaci\u00f3n con costos basados en verosimilitud y condiciones algebraicas bajo las cuales ciertos cambios en los costos preservan el resultado \u00f3ptimo\u00bb. Radon\u2013Nikodym ayuda a definir densidades y costos; preservar los \u00f3ptimos exige la propiedad algebraica de diferencias de costos y restricciones, demostrada por separado.\nNivel: investigaci\u00f3n por validar.",
    },
    {
      id: "m-rn-vs-zogy",
      q: "\u00bfRadon\u2013Nikodym es lo mismo que ZOGY?",
      keys: ["rn es zogy", "zogy y radon", "diferencia entre zogy y radon nikodym", "radon nikodym zogy", "zogy vs rn", "son lo mismo"],
      a: "No. ZOGY es una construcci\u00f3n concreta de diferencia de im\u00e1genes (con PSF y ruido). Radon\u2013Nikodym aparece en una formulaci\u00f3n te\u00f3rica general de razones de verosimilitud para asociar detecciones entre \u00e9pocas. Se ubican en etapas distintas: primero se comparan im\u00e1genes, despu\u00e9s se decide qu\u00e9 detecciones pertenecen a un mismo objeto.",
    },
    {
      id: "m-cnn",
      q: "\u00bfYa tiene una red neuronal (CNN)?",
      keys: ["cnn", "red neuronal", "redes neuronales", "convolucional", "machine learning", "aprendizaje automatico", "inteligencia artificial", "entrenada", "deep learning", "modelo entrenado", "neural network"],
      a: "No consta una CNN de producci\u00f3n entrenada y validada en los materiales revisados. Se plantea como m\u00f3dulo futuro para priorizar candidatos, rechazar artefactos o ayudar a clasificar patrones.\nUna convoluci\u00f3n discreta: Y_{i,j,k} = \u03c3(b_k + \u03a3_{u,v,c} W_{u,v,c,k}\u00b7X_{i+u,j+v,c}). La entrada X podr\u00eda incluir diferencia, puntuaci\u00f3n, varianza, m\u00e1scaras, ePSF y metadatos compatibles.\nNo sustituye WCS, calibraci\u00f3n espectral, ZOGY ni la validaci\u00f3n, y exige etiquetas fiables.\nTipo: propuesta.",
    },
    {
      id: "m-integracion",
      how: true,
      q: "\u00bfC\u00f3mo conecta Science con la API y el frontend?",
      keys: ["science api", "integracion", "como conecta science", "science frontend", "json cientifico", "fits en json", "separar tiempo y longitud de onda", "que se entrega al frontend", "que recibe el frontend", "health", "ruta de analisis", "backend cientifico", "science backend"],
      a: "Science produce resultados y metadatos trazables; la API los expone en JSON con URLs de productos; la interfaz separa tiempo y longitud de onda y muestra niveles de evidencia.\n\u2022 Frontend: elige coordenadas RA/Dec, dibuja regiones y compara mapas. No puede calcular \u00abmovimiento real\u00bb midiendo desplazamientos visuales entre mosaicos sin el pipeline cient\u00edfico; es v\u00e1lido mostrar datos y visualizaciones etiquetadas.\n\u2022 API: valida l\u00edmites de la selecci\u00f3n, activa scripts o servicios, expone estados y entrega productos peque\u00f1os. No se mezclan arreglos FITS gigantes en el JSON.\n\u2022 Un backend que responde \u00abhealth\u00bb no implica que exista una ruta de an\u00e1lisis cient\u00edfico completo, y un resultado bloqueado no se presenta como detecci\u00f3n real.\nTipo: arquitectura.",
    },
    {
      id: "m-json",
      q: "\u00bfC\u00f3mo es el JSON cient\u00edfico de ejemplo?",
      keys: ["ejemplo json", "json de ejemplo", "schema version", "morley.science.v1", "evidence_kind json", "motion_detected", "campos del json", "formato de salida", "respuesta de la api", "status incompatible_wavelength", "esquema json"],
      a: "Ejemplo EXPLICATIVO (no una respuesta real de la API), esquema morley.science.v1:\n\u2022 target: ra_deg 295.4097841, dec_deg \u221215.2231692, frame ICRS\n\u2022 evidence_kind: observed \u00b7 status: incompatible_wavelength \u00b7 source: spherex_level2\n\u2022 observations: 2025W39_1A_0331_1 y 2026W39_1A_0563_4\n\u2022 metrics: spectral_mismatch_approx 1.5064, time_separation_days 364.8583\n\u2022 methods: wcs_checked true, spectral_precheck true, real_zogy_executed false\n\u2022 result: motion_detected null, hypothesis null\n\u2022 limitations: \u00abBandas incompatibles: no ejecutar ZOGY real\u00bb\n\u00abobserved\u00bb se refiere a que las entradas son FITS observados; motion_detected = null indica que no hay medici\u00f3n v\u00e1lida.",
    },
    {
      id: "m-procedencia",
      q: "\u00bfQu\u00e9 se registra para la reproducibilidad y la procedencia?",
      keys: ["reproducibilidad", "procedencia", "sha256", "trazabilidad", "semilla", "versiones", "que se registra", "metadatos de procedencia", "reproducible", "registro de origen"],
      a: "Siempre: ID y URL de la observaci\u00f3n, fecha, versi\u00f3n/release, detector, SHA256 de los FITS, calibraci\u00f3n de longitudes de onda, tratamiento de banderas, PSF, coordenadas, semilla (si hay simulaci\u00f3n), dependencias y comando de ejecuci\u00f3n.\nUna descarga fallida por HTTP 503 o un TAP con ReadTimeout es un problema de disponibilidad, no prueba de que no existan objetos.",
    },
    {
      id: "m-no-afirmar",
      q: "\u00bfQu\u00e9 est\u00e1 probado, qu\u00e9 falta y qu\u00e9 no se debe afirmar?",
      keys: ["no se puede afirmar", "que no afirmar", "limitaciones", "limites", "que no hace", "alcance", "honestidad", "rigor", "advertencia", "integridad cientifica", "que esta probado", "probado", "tabla de estado", "que si se puede afirmar"],
      a: "\u2022 Visualizaci\u00f3n SPHEREx/AllWISE y selecci\u00f3n celeste: existe; no afirmar que todo p\u00edxel tenga historia temporal.\n\u2022 FITS Level 2 y WCS: se descargaron y leyeron recortes; no todo FITS es apto.\n\u2022 Preselector de fechas/espectro/varianza: operativo; bloque\u00f3 parejas incompatibles; no hay pareja aprobada.\n\u2022 ZOGY (Pr\u00e1ctica 05): sint\u00e9tico PASS, SNR \u2248 9.5038; no afirmar ZOGY real validado.\n\u2022 Gaussiana vs ePSF: experimento con datos reales; no afirmar movimiento f\u00edsico.\n\u2022 H0\u2013H3: 39/40 en simulaci\u00f3n; no afirmar 97.5 % en cielo real.\n\u2022 Gaia: prototipos preliminares; el paralaje del observador no est\u00e1 resuelto del todo.\n\u2022 Radon\u2013Nikodym: formulaci\u00f3n te\u00f3rica; no es teorema original ni producci\u00f3n.\n\u2022 CNN: propuesta futura.\n\u2022 Science\u2192API\u2192UI: partes exploradas; no afirmar un pipeline de detecci\u00f3n real de punta a punta.",
    },
    {
      id: "m-glosario",
      q: "\u00bfQu\u00e9 significan las siglas (glosario r\u00e1pido)?",
      keys: ["glosario", "que es fov", "que es hdu", "que es lvf", "siglas", "abreviaturas", "acronimos", "lista de terminos", "diccionario", "significado de las siglas", "terminos", "vocabulario"],
      a: "\u2022 RA/Dec: coordenadas celestes \u00b7 ICRS: marco de referencia \u00b7 WCS: transformaci\u00f3n celeste\u2194p\u00edxel \u00b7 AIT/TAN/SIN: proyecciones \u00b7 FOV: campo de visi\u00f3n.\n\u2022 FITS: formato astron\u00f3mico \u00b7 HDU: unidad de datos dentro de un FITS \u00b7 HiPS: mapas del cielo en teselas \u00b7 Level 2: exposiciones individuales calibradas \u00b7 LVF: filtro variable lineal \u00b7 \u00b5m: micr\u00f3metro \u00b7 MJy/sr: brillo superficial.\n\u2022 PSF/ePSF: respuesta a una fuente puntual / efectiva \u00b7 ZODI: luz zodiacal \u00b7 FLAGS: calidad de p\u00edxeles \u00b7 \u03c3\u00b2 (VARIANCE): varianza.\n\u2022 ZOGY: sustracci\u00f3n propia \u00b7 D: diferencia propia \u00b7 P_D: su PSF \u00b7 S/SNR: estad\u00edstico de detecci\u00f3n \u00b7 \u03c7\u00b2, \u03c7\u00b2\u03bd, BIC: ajuste y comparaci\u00f3n de modelos.\n\u2022 H0\u2013H3: hip\u00f3tesis de cambio \u00b7 Gaia: cat\u00e1logo astrom\u00e9trico \u00b7 Procedencia: registro del origen y m\u00e9todos \u00b7 Dipolo: residual +/\u2212.",
    },
    {
      id: "m-compatible",
      q: "\u00bfQu\u00e9 es una banda compatible?",
      keys: ["banda compatible", "bandas compatibles", "respuesta compatible", "compatible espectralmente", "misma banda", "filtros iguales"],
      a: "Una banda compatible tiene una respuesta espectral suficientemente parecida a la otra, validada para el an\u00e1lisis espec\u00edfico. Si R\u2081(\u03bb) y R\u2082(\u03bb) difieren, un cambio entre im\u00e1genes puede ser puramente espectral aunque el objeto permanezca fijo, as\u00ed que se bloquea la interpretaci\u00f3n temporal de la resta.",
    },
    {
      id: "m-michelson-math",
      q: "\u00bfC\u00f3mo es la matem\u00e1tica de la analog\u00eda del interfer\u00f3metro temporal?",
      keys: ["comparacion diferencial", "cancelar componente comun", "i2 i1", "diferencia ingenua", "resta ingenua", "cancelacion diferencial"],
      a: "I\u2081 = S + B\u2081 + \u03b5\u2081 y I\u2082 = S + \u0394S + B\u2082 + \u03b5\u2082, as\u00ed que I\u2082 \u2212 I\u2081 = \u0394S + (B\u2082 \u2212 B\u2081) + (\u03b5\u2082 \u2212 \u03b5\u2081).\nSi el fondo, la PSF y la escala est\u00e1n controlados, la se\u00f1al com\u00fan se reduce y puede aparecer el cambio. ZOGY generaliza estad\u00edsticamente esa comparaci\u00f3n para PSF distintas y ruido espec\u00edfico. No hay interferencia \u00f3ptica de fase.",
    },
    {
      id: "m-objetivo",
      q: "\u00bfCu\u00e1l es el objetivo de investigaci\u00f3n y de producto?",
      keys: ["objetivo de investigacion", "objetivo de producto", "objetivo cientifico", "que busca morley", "que se busca", "meta del proyecto"],
      a: "Investigaci\u00f3n: distinguir cambios reales de efectos de la instrumentaci\u00f3n o del procesamiento, comparando una misma regi\u00f3n celeste a lo largo del tiempo.\nProducto: convertir procesos astron\u00f3micos complejos en una exploraci\u00f3n comprensible sin ocultar el nivel de evidencia.",
    },
    {
      id: "sci-productos",
      q: "\u00bfQu\u00e9 productos de datos de SPHEREx hay en IRSA?",
      keys: ["productos", "producto", "spectral image", "mef", "fits", "nivel 2", "level 2", "all sky cube", "cubo de todo el cielo", "healpix", "12288", "cutouts", "mjy", "extensiones", "psf", "epsf", "zodiacal", "luz zodiacal", "calibracion"],
      a: "Los principales productos de SPHEREx en IRSA:\n\u2022 Spectral Image MEF (nivel 2): archivo FITS de ~70 MB por detector con 6 extensiones: imagen calibrada en MJy/sr, banderas, varianza, modelo de luz zodiacal (sin restar), PSF y tabla WCS-WAVE. Es el producto principal de DR1 y de los Quick Releases.\n\u2022 Cutouts: recortes de esos archivos, hechos por el servicio de IRSA.\n\u2022 All-Sky Cube (solo DR1): 12,288 teselas HEALPix de ~1.8\u00b0 con 102 canales y la luz zodiacal ya restada. Las im\u00e1genes HiPS en PNG son solo para visualizaci\u00f3n.\nAdem\u00e1s hay productos de calibraci\u00f3n (ganancia, ePSF, corriente oscura, WCS espectral, etc.).",
    },
    {
      id: "sci-lanzamientos",
      q: "\u00bfCu\u00e1les son los lanzamientos de datos de SPHEREx (QR y DR1)?",
      keys: ["quick release", "qr", "qr1", "qr2", "qr3", "dr1", "lanzamiento de datos", "lanzamientos", "data release", "cuando salen los datos", "fechas", "semanal", "version de datos", "reprocesado"],
      a: "Seg\u00fan IRSA:\n\u2022 Quick Release 1: julio de 2025.\n\u2022 QR2 (reprocesado): octubre de 2025.\n\u2022 QR3: septiembre de 2026.\n\u2022 Data Release 1 (DR1): noviembre de 2026; reprocesa los datos de QR2.\nLos Quick Releases publican im\u00e1genes espectrales de forma semanal. Tras DR1, las b\u00fasquedas en IRSA ya no devuelven QR2, aunque sigue disponible para descarga directa hasta febrero de 2027.",
    },
    {
      id: "sci-herramientas",
      q: "\u00bfQu\u00e9 herramientas cient\u00edficas ofrece IRSA para SPHEREx?",
      keys: ["herramientas", "herramienta", "most", "moving object search", "spectrophotometry", "espectrofotometria", "mosaic tool", "cutout tool", "source discovery", "splices", "3i atlas", "atlas", "astroquery", "sia"],
      a: "Herramientas de IRSA para SPHEREx:\n\u2022 Spectrophotometry Tool: extrae espectros de las im\u00e1genes espectrales con fotometr\u00eda forzada.\n\u2022 Mosaic Tool: mosaicos de varias longitudes de onda.\n\u2022 Cutout Tool: recorta subconjuntos de los FITS multi-extensi\u00f3n.\n\u2022 Source Discovery Tool: encuentra y caracteriza fuentes en una regi\u00f3n usando solo datos de SPHEREx.\n\u2022 MOST (Moving Object Search Tool): calcula la \u00f3rbita de un objeto del Sistema Solar y busca im\u00e1genes de SPHEREx que lo cubran.\nAcceso: SPHEREx Data Explorer, astroquery, SIA, directorios en IPAC y la nube (AWS S3). Tambi\u00e9n hay el cat\u00e1logo SPLICES (fuentes con hielo) y espectros del cometa 3I/ATLAS.",
    },
    {
      id: "sci-wiseview",
      q: "\u00bfC\u00f3mo funciona WiseView?",
      how: true,
      keys: ["wiseview", "unwise", "panstarrs", "pan starrs", "w1", "w2", "campo de vision wiseview", "trim bright", "asinh", "flipbook", "movimiento propio", "backyard worlds"],
      a: "WiseView (de Dan Caselden y Paul Westin) es una interfaz para las im\u00e1genes de unWISE, que reprocesa las exposiciones de WISE.\n\u2022 Arriba: recortes coa\u00f1adidos de WISE que alternan como flipbook, para ver si un objeto se mueve entre \u00e9pocas.\n\u2022 Abajo: composici\u00f3n de PanSTARRS-1, que ayuda a descartar fuentes no deseadas.\n\u2022 Controles: campo de visi\u00f3n, zoom, banda (W1, W2 o ambas), velocidad y normalizaci\u00f3n del brillo (asinh, con recorte de brillos altos).\nFue hecha para verificar el movimiento propio de candidatos en Backyard Worlds: Planet 9.",
    },
    {
      id: "sci-gaia",
      q: "\u00bfQu\u00e9 contiene Gaia DR3?",
      keys: ["gaia", "dr3", "edr3", "astrometria", "fotometria", "velocidades radiales", "bp rp", "rvs", "epoca de referencia", "2016", "fuentes gaia", "cuasar", "quasar", "estrellas variables"],
      a: "Gaia DR3 se public\u00f3 el 13 de junio de 2022 con observaciones de julio de 2014 a mayo de 2017 (34 meses), con \u00e9poca de referencia 2016.0.\n\u2022 Fuentes: 1,811,709,771.\n\u2022 Astrometr\u00eda completa: 1,467,744,818 (5 par\u00e1metros: 585 M; 6 par\u00e1metros: 882 M; solo posici\u00f3n: 344 M).\n\u2022 Fotometr\u00eda G: 1,806,254,432 fuentes.\n\u2022 Velocidades radiales: 33,812,183.\n\u2022 Objetos del Sistema Solar: 158,152.\n\u2022 Candidatos a cu\u00e1sar: 6,649,162.\nCombina Gaia EDR3 (2020) con productos nuevos; no trae astrometr\u00eda nueva.",
    },
    {
      id: "sci-neossat",
      q: "\u00bfCu\u00e1les son las caracter\u00edsticas t\u00e9cnicas de NEOSSat?",
      keys: ["neossat", "ness", "heoss", "maksutov", "ccd", "orbita heliosincronica", "elongacion", "magnitud 13.5", "pslv", "datos de neossat"],
      a: "NEOSSat (CSA y DRDC), lanzado el 25 de febrero de 2013 en un PSLV-C20 desde India.\n\u2022 Telescopio Maksutov-Cassegrain de 15 cm; focal 893 mm (f/5.7); campo de 0.85\u00b0 \u00d7 0.85\u00b0; dos CCD de 1024 \u00d7 1024; rango 350\u20131050 nm.\n\u2022 \u00d3rbita helios\u00edncrona de amanecer-atardecer: ~786 km, inclinaci\u00f3n 98.55\u00b0, periodo 100.6 min.\n\u2022 Misiones: NESS (asteroides cercanos al Sol, elongaci\u00f3n 45\u201355\u00b0) y HEOSS (sat\u00e9lites y restos en MEO/GEO), 50 % del tiempo cada una.\n\u2022 Masa ~72\u201374 kg. Detecta objetos de magnitud ~13.5.\nTuvo fallas en 2016 y se recuper\u00f3 en 2018 con un sensor de actitud basado en GPS.",
    },
    {
      id: "sci-bandas",
      q: "\u00bfCu\u00e1ntas bandas tiene SPHEREx?",
      keys: ["bandas", "banda", "102", "canales", "canal", "resolucion espectral", "espectro", "cuantas", "resolucion", "espectrales", "cuantas bandas", "bandas infrarrojas", "numero de bandas"],
      a: "SPHEREx cubre aproximadamente 0.75\u20135 \u00b5m en 102 bandas (f\u00edsicamente son 6 bandas de detector, con resoluciones espectrales R de 39, 41, 41, 35, 112 y 128; el cubo de todo el cielo DR1 las organiza en 102 canales). En el contrato de datos, cada banda (Band) trae su \u00edndice (1 a 102) y su rango en \u00b5m (wavelengthMinUm, wavelengthMaxUm). Las im\u00e1genes se piden aparte.",
    },
    {
      id: "sci-unidades",
      q: "\u00bfQu\u00e9 unidades y sistema de coordenadas se usan?",
      keys: ["unidades", "coordenadas", "icrs", "grados", "micrometros", "ra", "dec", "ascension recta", "declinacion", "sistema", "marco de referencia", "referencia"],
      a: "Coordenadas en grados (ICRS): ascensi\u00f3n recta (ra) y declinaci\u00f3n (dec). Longitudes de onda en micr\u00f3metros (\u00b5m), fechas en ISO 8601 y m\u00e1rgenes de error en segundos de arco.",
    },
    {
      id: "sci-filtros-metodo",
      how: true,
      q: "\u00bfC\u00f3mo se generan los filtros del visor?",
      keys: ["generan", "metodo", "algoritmo", "por dentro", "internamente", "tecnicamente", "como se construye", "como se construyen", "como funcionan los filtros", "como se calculan", "paleta", "paletas", "lut", "falso color", "canales sinteticos", "sinteticos", "calculo"],
      a: "Cada filtro es una funci\u00f3n que combina canales sint\u00e9ticos (visible, IR, t\u00e9rmico, hielos) con paletas de color (tablas de consulta) y produce un falso color. Por ejemplo:\n\u2022 IR cercano: paleta negro\u2192\u00e1mbar\u2192crema sobre el canal IR.\n\u2022 Hielos: paleta azul-cian sobre el canal de hielos, m\u00e1s un poco de visible.\n\u2022 T\u00e9rmico: paleta negro\u2192p\u00farpura\u2192rojo\u2192naranja\u2192amarillo p\u00e1lido sobre el canal t\u00e9rmico.\n\u2022 Compuesto: rojo = t\u00e9rmico, verde = IR, azul = visible.\nNo son mediciones de SPHEREx.",
    },
    {
      id: "sci-termico",
      q: "\u00bfPor qu\u00e9 el filtro T\u00e9rmico (8\u201314 \u00b5m) no es de SPHEREx?",
      keys: ["termico", "8 14", "fuera de spherex", "rango", "fuera de rango", "emision termica"],
      a: "Porque 8\u201314 \u00b5m queda fuera del rango de SPHEREx (\u22480.75\u20135 \u00b5m). El filtro es una representaci\u00f3n de emisi\u00f3n t\u00e9rmica, no una temperatura medida.",
    },
    {
      id: "sci-hielos",
      q: "\u00bfQu\u00e9 relaci\u00f3n tiene el filtro Hielos con las bandas de absorci\u00f3n?",
      keys: ["hielos", "hielo", "absorcion", "h2o", "co2", "co", "moleculas", "agua", "2 7 4 8"],
      a: "El filtro cubre 2.7\u20134.8 \u00b5m, donde caen bandas de absorci\u00f3n de hielos como H2O (~3.0 \u00b5m), CO2 (~4.27 \u00b5m) y CO (~4.67 \u00b5m). El filtro del visor es un realce ilustrativo y no identifica mol\u00e9culas.",
    },
    {
      id: "sci-epocas",
      q: "\u00bfQu\u00e9 es una \u00e9poca en los datos?",
      keys: ["epoca", "epocas", "epoch", "observedat", "cobertura", "6 meses", "baseline", "cadencia"],
      a: "Una \u00e9poca (Epoch) es una de las observaciones de SPHEREx, con id (e1, e2, e3\u2026), fecha observedAt en ISO 8601 y una etiqueta. El sat\u00e9lite cubre todo el cielo cada ~6 meses, as\u00ed que \u00e9pocas distintas dan la base temporal para detectar cambios de posici\u00f3n.",
    },
    {
      id: "sci-posiciones",
      q: "\u00bfQu\u00e9 datos trae cada posici\u00f3n de un objeto?",
      keys: ["posicion", "posiciones", "skyposition", "imageurl", "fovdeg", "recorte", "observedat", "campos", "sky position", "observed at", "image url", "fov deg"],
      a: "Cada SkyPosition trae epochId, ra y dec (grados). Los candidatos con datos reales traen adem\u00e1s observedAt (fecha real), imageUrl (imagen de esa \u00e9poca) y fovDeg (ancho real del recorte, en grados). Los simulados no los traen y comparten las im\u00e1genes del recuadro de prueba.",
    },
    {
      id: "sci-prediccion",
      how: true,
      q: "\u00bfC\u00f3mo funciona la predicci\u00f3n de posici\u00f3n?",
      keys: ["prediccion", "predecir", "incertidumbre", "confianza", "como funciona la prediccion", "como se predice", "confidence", "uncertainty", "arcsec", "futuro", "predice", "uncertainty arcsec"],
      a: "Un objeto puede traer prediction: fecha futura (atDate), ra y dec predichas, uncertaintyArcsec (radio del c\u00edrculo de incertidumbre en segundos de arco) y confidence (de 0 a 1). Es opcional: no siempre hay suficientes \u00e9pocas para predecir. Es una predicci\u00f3n, no una observaci\u00f3n.",
    },
    {
      id: "sci-tipos",
      q: "\u00bfQu\u00e9 tipos de objeto existen?",
      keys: ["tipos", "tipo", "kind", "asteroide", "cometa", "estrella", "enana marr\u00f3n", "enana marron", "planeta", "nebulosa", "desconocido", "clasificacion", "clases", "clase", "clases de objeto", "categorias de objeto"],
      a: "ObjectKind admite: asteroid, comet, star, brown_dwarf, planet_candidate, nebula y unknown. Los valores van en ingl\u00e9s en los datos; la interfaz los traduce al espa\u00f1ol.",
    },
    {
      id: "sci-simulado",
      q: "\u00bfQu\u00e9 es dato observado, simulado o predicho?",
      keys: ["observado", "simulado", "simulados", "predicho", "procedencia", "real", "reales", "prueba", "datos de prueba", "catalogo", "distinguir", "etiqueta", "simulated", "simulated true", "observed"],
      a: "El proyecto distingue tres cosas: datos observados, simulaciones y predicciones de cat\u00e1logo.\n\u2022 La respuesta de objetos trae simulated: true cuando son datos de prueba.\n\u2022 Los candidatos con datos reales se bajaron de IRSA con su propio recorte por \u00e9poca.\n\u2022 Los filtros del visor \u00c9TER no usan datos observados de SPHEREx: son bandas orientativas.",
    },
    {
      id: "sci-frames",
      q: "\u00bfC\u00f3mo se organizan las im\u00e1genes de cada \u00e9poca?",
      keys: ["frame", "frames", "imagen", "imagenes", "png", "cuadrada", "recuadro", "fov", "campo de vision"],
      a: "Cada Frame tiene epochId, imageUrl (PNG ya convertido), ra y dec del centro (ICRS) y fovDeg, el ancho de la imagen en grados; la imagen es cuadrada. Sobre ella se dibujan los objetos de esa \u00e9poca.",
    },
    {
      id: "sci-mosaico",
      q: "\u00bfDe d\u00f3nde sale el mosaico SPHEREx DR1?",
      keys: ["mosaico", "dr1", "irsa", "cubo", "slice", "canal 62", "canal usa", "62", "50 51", "tiles", "fuente", "origen", "cubo de spherex"],
      a: "Es el cubo espectral HiPS de todo el cielo de SPHEREx DR1, servido por IRSA (irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube) y cargado con Aladin Lite. Muestra un canal a la vez: se pide el canal 62 para evitar los canales 50 y 51, documentados como vac\u00edos. Es solo para visualizaci\u00f3n, y elegir la fuente no garantiza que los tiles hayan cargado.",
    },
    {
      id: "sci-hips",
      q: "\u00bfQu\u00e9 es HiPS?",
      keys: ["hips", "hierarchical", "progressive", "survey", "teselas", "tesela", "aladin", "formato hips"],
      a: "HiPS (Hierarchical Progressive Surveys) es un est\u00e1ndar de la IVOA para publicar mapas del cielo en teselas (tiles) a varias resoluciones, que Aladin Lite carga seg\u00fan el zoom. El cubo de SPHEREx a\u00f1ade un eje extra: el canal espectral.",
    },
    {
      id: "sci-allwise",
      q: "\u00bfQu\u00e9 es AllWISE y qu\u00e9 bandas muestra?",
      keys: ["allwise", "wise", "w1", "w2", "w4", "rgb", "referencia", "compuesto wise", "bandas wise"],
      a: "AllWISE es el mapa infrarrojo de todo el cielo de la misi\u00f3n WISE, servido por IRSA como el HiPS \u00abRGB-W4-W2-W1\u00bb, un compuesto de color. Se usa como referencia visual junto al mosaico de SPHEREx.",
    },
    {
      id: "sci-vistas",
      q: "\u00bfQu\u00e9 proyecciones y vistas usa el mosaico?",
      keys: ["proyeccion", "ait", "sin", "aitoff", "centro galactico", "sagitario", "266", "campo de vision", "fov", "cielo completo"],
      a: "\u2022 Cielo completo: proyecci\u00f3n AIT (Aitoff), centrada en ra 0, dec 0, con campo de visi\u00f3n de 360\u00b0.\n\u2022 Centro gal\u00e1ctico: proyecci\u00f3n SIN, centrada en ra 266.4168, dec \u221229.0078 (zona de Sagitario A*), con campo de visi\u00f3n de 10\u00b0.",
    },
    {
      // REVISAR: confirmar c\u00f3mo se usa SIMBAD en la interfaz.
      id: "sci-simbad",
      q: "\u00bfC\u00f3mo se usa SIMBAD en el visor?",
      keys: ["simbad", "cds", "consulta", "catalogo", "objetos conocidos", "estrasburgo", "base de datos"],
      a: "SIMBAD es la base de datos astron\u00f3mica del CDS (Estrasburgo). El visor la consulta para mostrar los objetos conocidos de la zona observada, con una tarjeta de informaci\u00f3n para el objeto seleccionado.",
    },
    {
      id: "sci-contrato",
      q: "\u00bfEn qu\u00e9 estado est\u00e1 el contrato de datos con el back?",
      keys: ["contrato", "api", "back", "backend", "borrador", "contracts", "tipos", "esquema", "endpoint"],
      a: "El contrato de datos (data/contracts.ts) es un BORRADOR, pendiente de acordar con el back. Define Epoch, Band, SkyPosition, MovingObject, SkyRegion, ObjectsResponse y Frame.",
    },
    {
      id: "sci-proxy",
      q: "\u00bfC\u00f3mo carga el fondo el visor \u00c9TER?",
      keys: ["proxy", "sky hips", "fondo", "ruta", "servidor", "cors", "api sky"],
      a: "El fondo del visor \u00c9TER carga sus tiles a trav\u00e9s de una ruta propia del servidor de Next.js (/api/sky-hips), no directamente desde el navegador.",
    },
  ],
};

/**
 * Sinonimos: palabra que escribe la gente -> palabras que si aparecen en la base.
 * Claves en minuscula y sin acentos. Agrega aqui lo que la gente suele decir distinto.
 */
export const SYNONYMS: Record<string, string[]> = {
  zogi: ["zogy"], sogy: ["zogy"], zogui: ["zogy"],
  // general
  usa: ["ayuda"], usas: ["ayuda"], acerco: ["acercar"], acercarme: ["acercar"], alejo: ["alejar"], alejarme: ["alejar"],
  construye: ["generan", "metodo"], construyen: ["generan", "metodo"], construccion: ["generan", "metodo"], elabora: ["generan", "metodo"],
  inventadas: ["simulado"], inventados: ["simulado"],
  tutorial: ["ayuda"], guia: ["ayuda"], instrucciones: ["ayuda"], empezar: ["ayuda"], comenzar: ["ayuda"],
  help: ["ayuda"], ayudame: ["ayuda"], socorro: ["ayuda"], funciona: ["ayuda"], usar: ["ayuda"], uso: ["ayuda"],
  pagina: ["visor", "app"], sitio: ["visor", "app"], programa: ["visor", "app"], plataforma: ["visor", "app"],
  trata: ["proyecto"], objetivo: ["proyecto", "sirve"], proposito: ["proyecto", "sirve"],
  creo: ["proyecto"], hizo: ["proyecto"], equipo: ["proyecto"], autor: ["proyecto"],
  // nombre / historia
  asi: ["nombre"], significa: ["nombre"],
  // spherex / infrarrojo
  sphere: ["spherex"], esferex: ["spherex"], sferex: ["spherex"],
  observatorio: ["satelite"], nasa: ["spherex"],
  calor: ["infrarrojo", "termico"], heat: ["infrarrojo"],
  // datos
  verdadero: ["real"], verdaderos: ["real"], autentico: ["real"], oficial: ["real"], inventado: ["simulado"],
  falsos: ["simulado"], ficticio: ["simulado"], fake: ["simulado"], prueba: ["simulado"],
  // filtros
  filter: ["filtro"], filters: ["filtro"], efecto: ["filtro"], efectos: ["filtro"], modo: ["filtro"],
  color: ["filtro", "colores"], tonos: ["filtro"], paleta: ["filtro"],
  optico: ["visible"],
  cercano: ["ir cercano"], medio: ["ir medio"],
  hielo: ["hielos"], agua: ["hielos"], congelado: ["hielos"],
  mezcla: ["compuesto"], combinado: ["compuesto"], rojo: ["compuesto"], verde: ["compuesto"], azul: ["compuesto"],
  // controles
  brillo: ["luminosidad", "ajustar"], intensidad: ["ajustar"], fuerza: ["ajustar"], regular: ["ajustar"],
  slider: ["ajustar"], barra: ["ajustar"], perilla: ["ajustar"], palanca: ["ajustar"],
  // menu
  opciones: ["menu"], hamburguesa: ["menu"], rayitas: ["menu"], lateral: ["menu"], panel: ["menu"],
  // fenomenos
  fenomeno: ["fenomenos"], nubes: ["nebulosas"], nebulosa: ["fenomenos"], galaxia: ["fenomenos"],
  // alternar visor
  regreso: ["volver"], regresar: ["volver"], cambio: ["alternar"], cambiar: ["alternar", "ajustar"], otro: ["alternar"],
  switch: ["alternar"], boton: ["alternar"], pastilla: ["alternar"],
  // mosaico
  mapa: ["mosaico"], atlas: ["mosaico"], cielo: ["mosaico"], panorama: ["mosaico"],
  capa: ["fuente"], survey: ["mosaico"], mosaicos: ["mosaico"],
  // vistas / movimiento
  centro: ["centro galactico"], completo: ["cielo completo"], entero: ["cielo completo"],
  agrandar: ["acercar"], ampliar: ["acercar"], aumentar: ["acercar"], achicar: ["alejar"], reducir: ["alejar"],
  desplazo: ["mover"], muevo: ["mover"], mueves: ["mover"], navego: ["navegar"], rotar: ["mover"], girar: ["mover"],
  // fallas
  negra: ["negro"], oscuro: ["negro"], oscura: ["negro"], apagado: ["negro"], pantalla: ["negro"],
  trabado: ["no carga"], trabada: ["no carga"], congelada: ["no carga"], atorado: ["no carga"], bug: ["error"],
  falla: ["error"], fallo: ["error"], roto: ["error"], rota: ["error"], tarda: ["lento"], tardado: ["lento"],
  // epocas / objetos
  fecha: ["epocas"], fechas: ["epocas"], historial: ["epocas"], pasado: ["epocas"], futuro: ["prediccion"],
  cambios: ["epocas"], evolucion: ["epocas"], reproduccion: ["reproducir"], pausa: ["reproducir"], velocidad: ["reproducir"],
  mueven: ["mueve"], rastros: ["rastro"], seguir: ["rastro"], asteroides: ["asteroide"],
  puntos: ["marcador"], circulos: ["marcador"], circulo: ["marcador"], estrellas: ["objeto"], planetas: ["objeto"],
  // simbad
  base: ["catalogo"], tarjeta: ["simbad"],
  // cientifico
  longitud: ["bandas", "micrometros"], onda: ["bandas", "micrometros"], micras: ["micrometros"], micrometro: ["micrometros"],
  wavelength: ["bandas"], espectral: ["bandas", "espectro"],
  coordenada: ["coordenadas"], ubicacion: ["posicion"], formato: ["unidades"],
  equatorial: ["coordenadas"], sistema: ["unidades"], medida: ["unidades"], medidas: ["unidades"],
  formula: ["algoritmo", "metodo"], matematica: ["algoritmo"], codigo: ["algoritmo", "metodo"], calculan: ["calculo"],
  predicen: ["prediccion"], pronostico: ["prediccion"], adivinar: ["prediccion"], estimar: ["prediccion"],
  margen: ["incertidumbre"], precision: ["incertidumbre"], seguridad: ["confianza"],
  certeza: ["confianza"], probabilidad: ["confianza"],
  dato: ["datos"], confiable: ["procedencia", "real"],
  json: ["contrato"], integracion: ["contrato"], conexion: ["contrato"],
  teselas: ["hips"], aladin: ["hips"], proyecciones: ["proyeccion"],
};
