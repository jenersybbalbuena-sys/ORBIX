
import streamlit as st
import fitz
import io
import os
import re
import base64
import hashlib
import zipfile
import html

from PIL import Image, ImageOps
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

# TAMAÑO DE DESCARGA
ANCHO_FINAL = 1920
ALTO_FINAL = 1080


# =========================================================
# DISEÑO VISUAL ORBIX
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');

:root {
    --purple: #7952c7;
    --purple-dark: #6240ad;
    --ink: #211a2b;
    --muted: #766d80;
    --line: #e9e2f1;
}

.stApp {
    background: #faf9fc;
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    max-width: 1080px;
    padding: 2.2rem 2rem 4rem;
}

h1, h2, h3 {
    color: var(--ink) !important;
    font-family: 'Manrope', sans-serif !important;
    letter-spacing: -0.035em;
    font-weight: 800 !important;
}

h1 { font-size: 2.7rem !important; }
h2 { font-size: 1.7rem !important; }

p, label, li, .stMarkdown {
    color: var(--muted);
}

[data-testid="stCaptionContainer"] {
    color: #91869c;
}

.orbix-brand {
    display: flex;
    align-items: center;
    gap: 13px;
    margin-bottom: 5px;
}

.orbix-mark {
    width: 46px;
    height: 46px;
    border-radius: 15px;
    display: grid;
    place-items: center;
    color: white;
    font-size: 24px;
    font-weight: 800;
    background: linear-gradient(145deg, #a78bfa, #7046bf);
    box-shadow: 0 8px 22px rgba(121,82,199,.16);
}

.orbix-kicker {
    color: #8b72b2;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .16em;
    text-transform: uppercase;
}

.orbix-subtitle {
    color: #81778b;
    font-size: 1rem;
    margin-top: 5px;
}

.step-label {
    color: #8066a8;
    font-size: .75rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: 7px;
}

.surface {
    background: white;
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 22px 24px;
    box-shadow: 0 8px 28px rgba(45, 28, 67, .035);
    margin: 12px 0 18px;
}

.soft-note {
    background: #f5f0fc;
    border: 1px solid #e9def8;
    border-radius: 14px;
    padding: 13px 16px;
    color: #65527f;
    font-size: .92rem;
}

.stButton > button,
.stDownloadButton > button {
    background: var(--purple);
    color: white !important;
    border: 1px solid var(--purple);
    border-radius: 12px;
    min-height: 46px;
    font-weight: 700;
    transition: all .2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background: var(--purple-dark);
    border-color: var(--purple-dark);
    box-shadow: 0 6px 18px rgba(121,82,199,.18);
    transform: translateY(-1px);
}

[data-testid="stFileUploader"] {
    background: #ffffff;
    border: 1.5px dashed #cbbbe3;
    border-radius: 16px;
    padding: 16px;
}

[data-testid="stFileUploader"] section {
    background: transparent;
}

div[data-testid="stExpander"] {
    background: white;
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
}

div[data-testid="stMetric"] {
    background: #f5f0fc;
    border: 1px solid #ece4f6;
    padding: 14px;
    border-radius: 14px;
}

div[data-testid="stMetric"] label {
    color: #796b89 !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #563b86 !important;
    font-weight: 800;
}

div[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #a78bfa, #7650c6);
    border-radius: 99px;
}

div[data-testid="stProgressBar"] {
    background: #eee8f5;
    border-radius: 99px;
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

div[data-testid="stImage"] img {
    border-radius: 12px;
}

input, textarea {
    border-radius: 10px !important;
}

hr {
    border-color: var(--line);
}

#MainMenu, footer {
    visibility: hidden;
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


def reiniciar():

    for clave, valor in {
        "paso": 1,
        "archivo_bytes": None,
        "archivo_nombre": None,
        "imagenes": [],
        "extraccion_realizada": False,
        "titulos_confirmados": False
    }.items():
        st.session_state[clave] = valor

    for key in list(st.session_state.keys()):
        if key.startswith("titulo_imagen_"):
            del st.session_state[key]


def avanzar(paso):
    st.session_state.paso = paso
    st.rerun()


iniciar_estado()


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
# CONVERSIÓN A FULL HD 1920 x 1080
# =========================================================

def convertir_full_hd(datos):

    imagen = Image.open(io.BytesIO(datos))

    # Corregir orientación de fotografías
    imagen = ImageOps.exif_transpose(imagen)

    # En GIF u otros formatos animados se utiliza el primer fotograma
    if getattr(imagen, "is_animated", False):
        imagen.seek(0)

    # Convertir a RGBA para conservar transparencias
    imagen = imagen.convert("RGBA")

    # Ajustar al tamaño Full HD sin deformar
    imagen_ajustada = ImageOps.contain(
        imagen,
        (ANCHO_FINAL, ALTO_FINAL),
        method=Image.Resampling.LANCZOS
    )

    # Crear lienzo transparente Full HD
    lienzo = Image.new(
        "RGBA",
        (ANCHO_FINAL, ALTO_FINAL),
        (255, 255, 255, 0)
    )

    # Centrar la imagen
    posicion_x = (ANCHO_FINAL - imagen_ajustada.width) // 2
    posicion_y = (ALTO_FINAL - imagen_ajustada.height) // 2

    lienzo.alpha_composite(
        imagen_ajustada,
        (posicion_x, posicion_y)
    )

    # Guardar como PNG para conservar transparencia
    salida = io.BytesIO()

    lienzo.save(
        salida,
        format="PNG",
        optimize=True
    )

    return salida.getvalue()


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

    try:

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

    finally:
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
# GENERAR ZIP EN FULL HD
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

            # Convertir cada imagen a 1920 x 1080
            datos_full_hd = convertir_full_hd(
                imagen["datos"]
            )

            # Todas las imágenes descargadas serán PNG
            nombre = f"{indice:02d} {titulo}.png"

            archivo_zip.writestr(
                nombre,
                datos_full_hd
            )

    memoria.seek(0)

    return memoria


# =========================================================
# CABECERA
# =========================================================

st.markdown("""
<div class="orbix-brand">
    <div class="orbix-mark">✦</div>
    <div>
        <div class="orbix-kicker">IMAGE EXTRACTOR</div>
        <div style="font-family:Manrope,sans-serif;
                    font-size:1.65rem;
                    font-weight:800;
                    color:#211a2b;">
            ORBIX
        </div>
    </div>
</div>
<div class="orbix-subtitle">
    Extrae. Organiza. Descarga.
</div>
""", unsafe_allow_html=True)


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

st.write("")
st.progress(paso / 4)

columnas = st.columns(4)

for i, nombre in enumerate(nombres_pasos, start=1):

    with columnas[i - 1]:

        if i == paso:
            st.markdown(
                f'<div class="step-label" style="color:#7046bf">'
                f'● {i:02d} · {nombre}</div>',
                unsafe_allow_html=True
            )

        elif i < paso:
            st.markdown(
                f'<div class="step-label" style="color:#5b9b7c">'
                f'✓ {i:02d} · {nombre}</div>',
                unsafe_allow_html=True
            )

        else:
            st.markdown(
                f'<div class="step-label">'
                f'○ {i:02d} · {nombre}</div>',
                unsafe_allow_html=True
            )

st.divider()


# =========================================================
# PASO 1: CARGAR DOCUMENTO
# =========================================================

if paso == 1:

    st.markdown(
        '<div class="step-label">PASO 01</div>',
        unsafe_allow_html=True
    )

    st.header("Carga tu documento")

    st.write(
        "Selecciona un archivo PDF o HTML para comenzar."
    )

    st.markdown('<div class="surface">', unsafe_allow_html=True)

    archivo = st.file_uploader(
        "Arrastra tu archivo aquí o selecciónalo desde tu equipo",
        type=["pdf", "html", "htm"],
        key="archivo_cargado"
    )

    if archivo:

        extension = os.path.splitext(archivo.name)[1].lower()

        st.success("Documento listo para procesar")

        c1, c2 = st.columns(2)

        c1.metric(
            "Formato",
            extension.replace(".", "").upper()
        )

        c2.metric(
            "Tamaño",
            f"{archivo.size / 1024:.1f} KB"
        )

        if st.button(
            "Continuar con este documento →",
            use_container_width=True
        ):

            st.session_state.archivo_bytes = archivo.getvalue()
            st.session_state.archivo_nombre = archivo.name
            st.session_state.imagenes = []
            st.session_state.extraccion_realizada = False
            st.session_state.titulos_confirmados = False

            avanzar(2)

    else:

        st.caption("Formatos admitidos: PDF, HTML y HTM.")

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# PASO 2: EXTRAER IMÁGENES
# =========================================================

elif paso == 2:

    st.markdown(
        '<div class="step-label">PASO 02</div>',
        unsafe_allow_html=True
    )

    st.header("Extrae las imágenes")

    st.write(
        f"Documento: **{st.session_state.archivo_nombre}**"
    )

    with st.expander("Opciones de extracción"):

        c1, c2 = st.columns(2)

        with c1:
            ancho_minimo = st.number_input(
                "Ancho mínimo (px)",
                min_value=1,
                max_value=5000,
                value=250,
                step=25
            )

        with c2:
            alto_minimo = st.number_input(
                "Alto mínimo (px)",
                min_value=1,
                max_value=5000,
                value=180,
                step=25
            )

        st.caption(
            "Aumenta estos valores para ignorar imágenes pequeñas."
        )

    if not st.session_state.extraccion_realizada:

        st.markdown(
            '<div class="soft-note">'
            'ORBIX analizará el archivo y conservará los datos '
            'originales de las imágenes.'
            '</div>',
            unsafe_allow_html=True
        )

        st.write("")

        if st.button(
            "✦ Iniciar extracción",
            use_container_width=True
        ):

            try:

                with st.spinner("Analizando el documento..."):

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

                st.error(
                    f"No se pudo completar la extracción: {error}"
                )

    else:

        imagenes = st.session_state.imagenes

        if imagenes:

            st.success("Extracción completada.")

            st.metric(
                "Imágenes encontradas",
                len(imagenes)
            )

            st.caption("Vista previa de los primeros resultados:")

            vista = st.columns(min(3, len(imagenes)))

            for indice, imagen in enumerate(imagenes[:3]):

                with vista[indice]:

                    st.image(
                        imagen["datos"],
                        use_container_width=True
                    )

                    st.caption(
                        f"{indice + 1:02d} · {imagen['titulo'][:42]}"
                    )

            if st.button(
                "Confirmar extracción y continuar →",
                use_container_width=True
            ):

                avanzar(3)

        else:

            st.warning(
                "No se encontraron imágenes con los criterios actuales."
            )

            st.caption(
                "Puedes reducir el ancho o alto mínimo e intentarlo de nuevo."
            )

    st.write("")

    atras, repetir = st.columns(2)

    with atras:

        if st.button("← Volver", use_container_width=True):
            avanzar(1)

    with repetir:

        if st.button(
            "Reiniciar extracción",
            use_container_width=True
        ):

            st.session_state.extraccion_realizada = False
            st.session_state.imagenes = []

            st.rerun()


# =========================================================
# PASO 3: ORGANIZAR TÍTULOS
# =========================================================

elif paso == 3:

    st.markdown(
        '<div class="step-label">PASO 03</div>',
        unsafe_allow_html=True
    )

    st.header("Organiza los títulos")

    st.write(
        "Revisa cada imagen y ajusta su nombre antes de descargarla."
    )

    st.markdown(
        '<div class="soft-note">'
        'Los títulos solo se usarán para nombrar los archivos. '
        'No se modificarán ni se escribirán sobre las imágenes.'
        '</div>',
        unsafe_allow_html=True
    )

    imagenes = st.session_state.imagenes

    st.write(f"**{len(imagenes)} imágenes para revisar**")

    for indice, imagen in enumerate(imagenes):

        with st.expander(
            f"{indice + 1:02d} · {imagen['titulo']}",
            expanded=(indice == 0)
        ):

            izquierda, derecha = st.columns([1, 1.25])

            with izquierda:

                st.image(
                    imagen["datos"],
                    use_container_width=True
                )

            with derecha:

                st.caption(
                    f"Página {imagen['pagina']} · "
                    f"{imagen['ancho']} × {imagen['alto']} px"
                )

                nuevo_titulo = st.text_input(
                    "Nombre del archivo",
                    value=imagen["titulo"],
                    key=f"titulo_imagen_{indice}"
                )

                imagen["titulo"] = nuevo_titulo

                st.caption(
                    f"Se guardará como: {indice + 1:02d} "
                    f"{nombre_seguro(nuevo_titulo)}.png"
                )

    st.write("")

    if st.button(
        "Confirmar títulos y continuar →",
        use_container_width=True
    ):

        st.session_state.titulos_confirmados = True
        avanzar(4)

    if st.button(
        "← Volver a extracción",
        use_container_width=True
    ):

        avanzar(2)


# =========================================================
# PASO 4: DESCARGAR
# =========================================================

elif paso == 4:

    st.markdown(
        '<div class="step-label">PASO 04</div>',
        unsafe_allow_html=True
    )

    st.header("Tu descarga está lista")

    imagenes = st.session_state.imagenes

    if not st.session_state.titulos_confirmados:

        st.warning("Primero debes confirmar los títulos.")

        if st.button("Volver a organizar"):
            avanzar(3)

    else:

        st.markdown(
            '<div class="soft-note">'
            'Tus imágenes se exportarán en Full HD (1920 × 1080), '
            'sin deformaciones y en formato PNG.'
            '</div>',
            unsafe_allow_html=True
        )

        st.write("")

        st.metric(
            "Imágenes organizadas",
            len(imagenes)
        )

        st.caption(
            "Resolución de descarga: 1920 × 1080 píxeles"
        )

        try:

            with st.spinner("Preparando imágenes Full HD..."):

                archivo_zip = crear_zip(imagenes)

            st.success("Todas las imágenes están preparadas.")

            st.download_button(
                "↓ Descargar imágenes Full HD (.ZIP)",
                data=archivo_zip,
                file_name="ORBIX_Imagenes_Full_HD.zip",
                mime="application/zip",
                use_container_width=True
            )

        except Exception as error:

            st.error(
                f"No se pudo preparar el ZIP: {error}"
            )

        if imagenes:

            with st.expander("Ver resumen de archivos"):

                for indice, imagen in enumerate(
                    imagenes,
                    start=1
                ):

                    st.write(
                        f"{indice:02d}. "
                        f"{nombre_seguro(imagen['titulo'])}.png"
                    )

        st.write("")

        if st.button(
            "← Volver a títulos",
            use_container_width=True
        ):

            avanzar(3)

        if st.button(
            "Iniciar una nueva extracción",
            use_container_width=True
        ):

            reiniciar()
            st.rerun()


# =========================================================
# PIE DE PÁGINA
# =========================================================

st.divider()

st.caption("ORBIX · Image Extractor · Full HD 1920 × 1080")
    
