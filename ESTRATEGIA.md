# Rutina: estrategia mensual en Notion (Agente de Estrategia)

Instrucciones para que Claude arme, unos días antes del 25, la **estrategia del mes siguiente** de
cada cliente y la deje como **boceto** en Notion para que Yvette la revise y apruebe. El día 25 la
rutina de informes (`RUTINA.md`) lee esa estrategia para cargar ideas, calendario y copys.

Si el pedido dice **"modo prueba"**, no escribas nada en Notion: mostrá la estrategia en la
respuesta y listo.

Clientes, páginas y bases: usá las mismas tablas de `RUTINA.md` ("Clientes y destinos en Notion").
Escribí solo dentro de la página **Estrategia** de cada cliente (subpágina de su *Página del
cliente*). No toques el contenido existente de esa página: todo lo nuevo va en subpáginas.

## Criterio (Hola Marketing OS, cap. Estrategia)

- Primero entender el negocio, después la marca. Una idea que no ayuda a vender no entra.
- No copiar tendencias porque sí: una tendencia entra solo si sirve al objetivo del mes.
- Menos piezas pero con intención. Cada bloque del mes tiene un para qué.
- La estrategia se revisa todos los meses con lo que pasó el mes anterior.

## Pasos por cliente

### 1. Leer lo que ya está definido

Dentro de la página **Estrategia**:
- La estrategia base: pilares, ritmo editorial, tono, público, objetivos del trimestre, límites.
  Es lo aprobado por el cliente; el mes nuevo se apoya en eso y no lo contradice.
- Los meses anteriores (bloques tipo "🔥 MAYO – …" en la página, o subpáginas
  "🧭 Estrategia · <Mes> <año> · …"), para dar continuidad y no repetir el mismo enfoque.

### 2. Insumos del mes

Buscá dentro de la página **Estrategia** la subpágina **📥 Insumos del mes**. Ahí el equipo pega
(o adjunta) el export del chat de WhatsApp con el cliente, las notas de Gemini de las reuniones y
cualquier novedad (lanzamientos, promos, cambios de precio, eventos).

- Si no existe, creala vacía con este texto y seguí sin insumos:
  "Pegá acá, antes del día 20 de cada mes, el export del chat de WhatsApp con el cliente, las
  notas de Gemini de las reuniones y cualquier novedad del negocio. El Agente de Estrategia lo lee
  para armar la estrategia del mes siguiente."
- Si existe, usá solo lo cargado desde la estrategia anterior en adelante. Sacá de ahí pedidos del
  cliente, quejas, productos o servicios a empujar, fechas y decisiones ya tomadas.
- No copies textual conversaciones privadas en la estrategia: resumí lo que importa.

### 3. Qué pasó el último mes

- El último **📊 Informe Instagram** de la página del cliente (números, qué funcionó, qué no,
  recomendaciones). Usá esos números; no inventes otros.
- Si hay `META_ACCESS_TOKEN` (o el token del cliente), podés sumar el pulso de los últimos 30 días:
  `python -m informes_ig.datos --ig-id <IG ID> --dias 30` (con `--instagram-login --token-env
  <Token>` para los clientes conectados por Instagram). Si falla, seguí con el informe.
- **Plan de publicaciones**: qué se planificó y qué se publicó el mes en curso (estado
  Publicado vs. Idea), y qué ya está cargado para el mes siguiente.

### 4. Contexto del mes siguiente

Fechas especiales relevantes para el público y el país del cliente (Argentina, Miami/EE. UU.,
etc.), temporada, fechas comerciales (Black Friday, Hot Sale, Navidad…) y cualquier evento de los
insumos. Solo las que sirvan al negocio.

### 5. Escribir el boceto

Creá una subpágina dentro de la página **Estrategia**:
**🧭 Estrategia · <Mes> <año> · Boceto** (por ejemplo "🧭 Estrategia · Noviembre 2026 · Boceto").
Si ya existe una para ese mes, no la pises: reportalo y seguí con el siguiente cliente.

Al principio, un callout: "Boceto armado por el Agente de Estrategia. Para aprobarlo, cambiá
'Boceto' por 'Aprobada' en el título (podés editar lo que quieras antes). El día 25 las ideas del
mes se arman con esta página."

Secciones (mismo estilo que los meses que ya están en la página):
- **Lectura del mes anterior**: 3 a 5 puntos con números del informe y del plan.
- **Objetivo del mes**: una oración.
- **Enfoque**: cómo vamos a lograrlo.
- **Qué trabajar**: 4 a 6 temas concretos.
- **Tipos de acciones y formatos**: con la cantidad del ritmo editorial contratado, repartida por
  formato y pilar (usá los pilares que existen en el Plan de publicaciones). Decí por qué ese
  reparto según los datos.
- **Objetivo comercial**: qué servicio o producto se empuja y con qué llamado a la acción.
- **Fechas clave del mes**: fecha y cómo la usamos (o por qué no).
- **Qué no hacer este mes**: lo que el informe mostró que no funciona, más los límites de la marca.
- **Insumos usados**: qué se leyó (informe, insumos del mes, plan). Si faltaron insumos, decilo.
- **Preguntas para Yvette**: solo si hay una duda real que cambia la estrategia.

Estilo: español rioplatense, claro y directo, sin jerga ni frases de gurú, como el resto de la
página. Separá dato de interpretación.

### 6. Cierre

Respondé con una línea por cliente: link al boceto, si había insumos del mes, y cualquier problema
(página Estrategia no encontrada, boceto ya existente, sin informe previo).
