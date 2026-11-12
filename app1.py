
import streamlit as st
import fitz
import io
import os
import re
import base64
import hashlib
import zipfile
import html

from PIL import Image
from bs4 import BeautifulSoup


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="ORBIX | Image Extractor",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# ESTILOS: SIN BLOQUES HTML DE INTERFAZ
# =========================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at 10% 0%, #302044 0%, transparent 35%),
        radial-gradient(circle at 90% 10%, #24183a 0%, transparent 35%),
        #0b0912;
    color: #ffffff;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #efd4ff !important;
    font-weight: 850 !important;
    text-shadow: 0 0 14px rgba(194, 120, 255, .3);
}

p, label, span, li, .stMarkdown {
    color: #f2eaff !important;
}

.stCaption, [data-testid="stCaptionContainer"] {
    color: #cbb8e2 !important;
}

.stButton > button {
    background: linear-gradient(100deg, #9333ea, #c05cff);
    color: white !important;
    border: 1px solid #d5a4ff;
    border-radius: 12px;
    min-height: 46px;
    font-weight: 800;
    transition: .2s;
}

.stButton > button:hover {
    background: linear-gradient(100deg, #a855f7, #df75ff);
    box-shadow: 0 0 20px rgba(198, 120, 255, .4);
    transform: translateY(-2px);
}

.stDownloadButton > button {
    background: #7c3aed;
    color: white !important;
    border: 1px solid #d5a4ff;
    border-radius: 12px;
    min-height: 48px;
    font-weight: 800;
}

[data-testid="stFileUploader"] {
    background: #191322;
    border: 1px dashed #b77ce7;
    border-radius: 15px;
    padding: 15px;
}

[data-testid="stFileUploader"] * {
    color: #ffffff !important;
}

input, textarea {
    background: #21182e !important;
    color: white !important;
    border: 1px solid #8053a7 !important;
}

.stTextInput label {
    color: #f0d9ff !important;
    font-weight: 700 !important;
}

hr {
    border-color: #563a70;
}

div[data-testid="stImage"] img {
    border-radius: 12px;
    border: 1px solid #704c91;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# ESTADO
# =========================================================

def iniciar_estado():

    valores = {
        "paso": 1,
        "archivo_bytes": None,
        "archivo_nombre": None,
        "imagenes": [],
        "extraccion_realizada": False,
        "titulos_confirmados": False
    }

    for clave, valor in valores.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


iniciar_estado()


def reiniciar():
    st.session_state.paso = 1
    st.session_state.archivo_bytes = None
    st.session_state.archivo_nombre = None
    st.session_state.imagenes = []
    st.session_state.extraccion_realizada = False
    st.session_state.titulos_confirmados = False


def avanzar(paso):
    st.session_state.paso = paso
    st.rerun()


# =========================================================
# FUNCIONES DE TEXTO
# =========================================================

def limpiar_titulo(texto, limite=90):

    texto = html.unescape(str(texto))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip(" ._-–—\n\t")

    return texto[:limite] if texto else "Imagen sin título"


def nombre_seguro(texto):

    texto = limpiar_titulo(texto)

    texto = re.sub(r'[\\/:*?"<>|]', "", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip(" .") or "Imagen"


def obtener_hash(datos):
    return hashlib.sha256(datos).hexdigest()


def obtener_extension(ext):

    permitidas = {
        "png": "png",
        "jpg": "jpg",
        "jpeg": "jpg",
        "webp": "webp",
        "bmp": "bmp",
        "gif": "gif",
        "tiff": "tiff"
    }

    return permitidas.get(str(ext).lower().strip("."), "png")


def dimensiones(datos):

    try:
        imagen = Image.open(io.BytesIO(datos))
        return imagen.size
    except Exception:
        return None


# =========================================================
# TÍTULOS AUTOMÁTICOS EN PDF
# =========================================================

def titulo_pdf(pagina, bbox, numero_pagina, numero_imagen):

    try:
        bloques = pagina.get_text("blocks")
    except Exception:
        bloques = []

    x0, y0, x1, y1 = bbox
    candidatos = []

    for bloque in bloques:

        if len(bloque) < 5:
            continue

        texto = limpiar_titulo(bloque[4])

        if not texto or texto == "Imagen sin título":
            continue

        bx0, by0, bx1, by1 = bloque[:4]

        if by1 <= y0:
            distancia_vertical = y0 - by1
        elif by0 >= y1:
            distancia_vertical = by0 - y1
        else:
            distancia_vertical = 0

        centro_imagen = (x0 + x1) / 2
        centro_texto = (bx0 + bx1) / 2

        distancia_horizontal = abs(
            centro_imagen - centro_texto
        )

        puntuacion = (
            distancia_vertical +
            distancia_horizontal * 0.25
        )

        candidatos.append((puntuacion, texto))

    if candidatos:
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]

    return f"Página {numero_pagina} imagen {numero_imagen}"


# =========================================================
# EXTRACTOR PDF
# =========================================================

def extraer_pdf(datos_pdf, ancho_minimo, alto_minimo):

    documento = fitz.open(
        stream=datos_pdf,
        filetype="pdf"
    )

    resultados = []
    hashes = set()

    for indice, pagina in enumerate(documento):

        numero_pagina = indice + 1

        try:
            elementos = pagina.get_image_info(xrefs=True)
        except Exception:
            elementos = []

        contador_pagina = 0
        ubicaciones_vistas = set()

        for elemento in elementos:

            xref = elemento.get("xref", 0)
            ancho = elemento.get("width", 0)
            alto = elemento.get("height", 0)
            bbox = elemento.get("bbox", (0, 0, 0, 0))

            if ancho < ancho_minimo or alto < alto_minimo:
                continue

            ubicacion = (xref, tuple(bbox))

            if ubicacion in ubicaciones_vistas:
                continue

            ubicaciones_vistas.add(ubicacion)

            if xref <= 0:
                continue

            try:
                extraida = documento.extract_image(xref)
                datos = extraida["image"]
                extension = obtener_extension(
                    extraida.get("ext", "png")
                )
            except Exception:
                continue

            tamano = dimensiones(datos)

            if not tamano:
                continue

            huella = obtener_hash(datos)

            if huella in hashes:
                continue

            hashes.add(huella)
            contador_pagina += 1

            titulo = titulo_pdf(
                pagina,
                bbox,
                numero_pagina,
                contador_pagina
            )

            resultados.append({
                "datos": datos,
                "extension": extension,
                "titulo": titulo,
                "pagina": numero_pagina,
                "ancho": tamano[0],
                "alto": tamano[1]
            })

    documento.close()

    return resultados


# =========================================================
# EXTRACTOR HTML
# =========================================================

def extraer_html(datos_html):

    try:
        contenido = datos_html.decode("utf-8")
    except UnicodeDecodeError:
        contenido = datos_html.decode("latin-1", errors="ignore")

    soup = BeautifulSoup(contenido, "html.parser")

    resultados = []
    hashes = set()

    for indice, etiqueta in enumerate(
        soup.find_all("img"),
        start=1
    ):

        src = etiqueta.get("src", "")

        if not src.startswith("data:image/"):
            continue

        try:
            encabezado, contenido_base64 = src.split(",", 1)

            datos = base64.b64decode(contenido_base64)

            tamano = dimensiones(datos)

            if not tamano:
                continue

            huella = obtener_hash(datos)

            if huella in hashes:
                continue

            hashes.add(huella)

            imagen = Image.open(io.BytesIO(datos))
            formato = (imagen.format or "PNG").lower()

            extensiones = {
                "jpeg": "jpg",
                "jpg": "jpg",
                "png": "png",
                "webp": "webp",
                "gif": "gif",
                "bmp": "bmp",
                "tiff": "tiff"
            }

            extension = extensiones.get(formato, "png")

            titulo = ""

            for encabezado_html in [
                etiqueta.find_previous(["h1", "h2", "h3", "h4"]),
                etiqueta.find_next(["h1", "h2", "h3", "h4"])
            ]:

                if encabezado_html:
                    titulo = limpiar_titulo(
                        encabezado_html.get_text(" ", strip=True)
                    )
                    break

            if not titulo:
                titulo = limpiar_titulo(
                    etiqueta.get("alt", "")
                    or etiqueta.get("title", "")
                )

            if titulo == "Imagen sin título":
                titulo = f"Imagen {indice}"

            resultados.append({
                "datos": datos,
                "extension": extension,
                "titulo": titulo,
                "pagina": indice,
                "ancho": tamano[0],
                "alto": tamano[1]
            })

        except Exception:
            continue

    return resultados


# =========================================================
# GENERAR ARCHIVO ZIP
# =========================================================

def crear_zip(imagenes):

    memoria = io.BytesIO()

    with zipfile.ZipFile(
        memoria,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archivo_zip:

        for indice, imagen in enumerate(imagenes, start=1):

            titulo = nombre_seguro(imagen["titulo"])
            extension = imagen["extension"]

            nombre = f"{indice:02d} {titulo}.{extension}"

            archivo_zip.writestr(
                nombre,
                imagen["datos"]
            )

    memoria.seek(0)

    return memoria


# =========================================================
# CABECERA
# =========================================================

st.title("✦ ORBIX")
st.subheader("Scribe Image Extractor")

st.write(
    "Extrae y organiza tus imágenes originales. "
    "Sin filtros, sin retoques y sin redimensionarlas."
)

st.divider()


# =========================================================
# INDICADOR DE PASOS
# =========================================================

paso = st.session_state.paso

nombres_pasos = [
    "Cargar documento",
    "Extraer imágenes",
    "Organizar títulos",
    "Descargar"
]

st.progress(paso / 4)

st.caption(
    f"ETAPA {paso} DE 4  ·  {nombres_pasos[paso - 1]}"
)

st.divider()


# =========================================================
# PASO 1: CARGAR DOCUMENTO
# =========================================================

if paso == 1:

    st.header("01 · Cargar documento")

    st.write(
        "Selecciona el documento de Scribe que deseas procesar."
    )

    archivo = st.file_uploader(
        "Seleccionar archivo",
        type=["pdf", "html", "htm"],
        key="archivo_cargado"
    )

    if archivo:

        extension = os.path.splitext(archivo.name)[1].lower()

        st.success("Documento seleccionado correctamente.")

        st.write(f"**Archivo:** {archivo.name}")
        st.write(
            f"**Tamaño:** {archivo.size / 1024:.1f} KB"
        )
        st.write(f"**Formato:** {extension.upper()}")

        st.warning(
            "Confirma este documento para continuar."
        )

        if st.button(
            "CONFIRMAR DOCUMENTO →",
            use_container_width=True
        ):

            st.session_state.archivo_bytes = archivo.getvalue()
            st.session_state.archivo_nombre = archivo.name
            st.session_state.imagenes = []
            st.session_state.extraccion_realizada = False

            avanzar(2)

    else:
        st.info("Primero debes seleccionar un archivo.")


# =========================================================
# PASO 2: EXTRAER IMÁGENES
# =========================================================

elif paso == 2:

    st.header("02 · Extraer imágenes")

    st.write(
        f"Documento seleccionado: **{st.session_state.archivo_nombre}**"
    )

    st.write(
        "ORBIX analizará el documento y buscará las imágenes "
        "que se puedan extraer."
    )

    with st.expander("Configuración de extracción"):

        ancho_minimo = st.number_input(
            "Ancho mínimo en píxeles",
            min_value=1,
            max_value=5000,
            value=250,
            step=25
        )

        alto_minimo = st.number_input(
            "Alto mínimo en píxeles",
            min_value=1,
            max_value=5000,
            value=180,
            step=25
        )

    if not st.session_state.extraccion_realizada:

        if st.button(
            "✦ INICIAR EXTRACCIÓN",
            use_container_width=True
        ):

            try:

                with st.spinner(
                    "Analizando el documento..."
                ):

                    extension = os.path.splitext(
                        st.session_state.archivo_nombre
                    )[1].lower()

                    if extension == ".pdf":

                        imagenes = extraer_pdf(
                            st.session_state.archivo_bytes,
                            int(ancho_minimo),
                            int(alto_minimo)
                        )

                    else:

                        imagenes = extraer_html(
                            st.session_state.archivo_bytes
                        )

                    st.session_state.imagenes = imagenes
                    st.session_state.extraccion_realizada = True

                st.rerun()

            except Exception as error:
                st.error(f"Error al extraer: {error}")

    else:

        imagenes = st.session_state.imagenes

        st.success(
            f"Extracción terminada: {len(imagenes)} imágenes encontradas."
        )

        if imagenes:

            st.metric(
                "Total de imágenes encontradas",
                len(imagenes)
            )

            st.write(
                "Revisa el resultado antes de confirmar."
            )

            for indice, imagen in enumerate(imagenes[:6]):

                st.write(
                    f"{indice + 1}. {imagen['titulo']} "
                    f"({imagen['ancho']} × {imagen['alto']} px)"
                )

            if len(imagenes) > 6:
                st.caption(
                    f"Y {len(imagenes) - 6} imágenes adicionales."
                )

            st.warning(
                "La cantidad encontrada debe ser revisada antes "
                "de continuar."
            )

            if st.button(
                "CONFIRMAR EXTRACCIÓN Y CONTINUAR →",
                use_container_width=True
            ):
                avanzar(3)

        else:
            st.error(
                "No se encontraron imágenes con los criterios actuales."
            )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Volver"):
            avanzar(1)

    with col2:
        if st.button("Repetir extracción"):
            st.session_state.extraccion_realizada = False
            st.session_state.imagenes = []
            st.rerun()


# =========================================================
# PASO 3: ORGANIZAR TÍTULOS
# =========================================================

elif paso == 3:

    st.header("03 · Organizar imágenes")

    imagenes = st.session_state.imagenes

    st.write(
        "Revisa las imágenes y modifica sus títulos si lo necesitas."
    )

    st.info(
        "Los títulos se utilizarán en los nombres de los archivos. "
        "No se escribirán sobre las imágenes."
    )

    st.write(f"**Total para organizar: {len(imagenes)}**")

    for indice, imagen in enumerate(imagenes):

        with st.expander(
            f"Imagen {indice + 1:02d} · {imagen['titulo']}",
            expanded=(indice == 0)
        ):

            izquierda, derecha = st.columns([1, 1.3])

            with izquierda:

                st.image(
                    imagen["datos"],
                    use_container_width=True
                )

            with derecha:

                st.caption(
                    f"Resolución original: "
                    f"{imagen['ancho']} × {imagen['alto']} px"
                )

                nuevo_titulo = st.text_input(
                    "Título",
                    value=imagen["titulo"],
                    key=f"titulo_imagen_{indice}"
                )

                imagen["titulo"] = nuevo_titulo

                st.caption(
                    f"Nombre: {indice + 1:02d} "
                    f"{nombre_seguro(nuevo_titulo)}."
                    f"{imagen['extension']}"
                )

    st.divider()

    st.warning(
        "Al confirmar, los títulos quedarán listos para la descarga."
    )

    if st.button(
        "CONFIRMAR TÍTULOS Y CONTINUAR →",
        use_container_width=True
    ):

        st.session_state.titulos_confirmados = True
        avanzar(4)

    if st.button("← Volver a extracción"):
        avanzar(2)


# =========================================================
# PASO 4: DESCARGAR
# =========================================================

elif paso == 4:

    st.header("04 · Descargar imágenes")

    imagenes = st.session_state.imagenes

    if not st.session_state.titulos_confirmados:

        st.warning("Primero debes confirmar los títulos.")
        if st.button("Volver a organizar"):
            avanzar(3)

    else:

        st.success(
            f"¡Todo listo! Tienes {len(imagenes)} imágenes organizadas."
        )

        st.write(
            "ORBIX ha preparado el archivo con las imágenes "
            "y sus nombres correspondientes."
        )

        archivo_zip = crear_zip(imagenes)

        st.download_button(
            "⬇ DESCARGAR TODAS LAS IMÁGENES",
            data=archivo_zip,
            file_name="ORBIX_Imagenes_Scribe.zip",
            mime="application/zip",
            use_container_width=True
        )

        st.divider()

        st.subheader("Resumen")

        st.metric("Imágenes listas", len(imagenes))

        if imagenes:
            st.write(
                f"Primera imagen: {nombre_seguro(imagenes[0]['titulo'])}"
            )
            st.write(
                f"Última imagen: {nombre_seguro(imagenes[-1]['titulo'])}"
            )

        if st.button(
            "← Volver a títulos",
            use_container_width=True
        ):
            avanzar(3)

        if st.button(
            "INICIAR NUEVA EXTRACCIÓN",
            use_container_width=True
        ):
            reiniciar()
            st.rerun()


# =========================================================
# PIE DE PÁGINA
# =========================================================

st.divider()

st.caption(
    "ORBIX STUDIO · Extracción y organización de imágenes"
)
