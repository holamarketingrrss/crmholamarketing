# Informes de Instagram → Notion

Automatización para los clientes de HOLA MARKETING. Por cada cliente:

1. **Trae los datos de Instagram** directo de la API oficial de Meta (gratis, sin Metricool): alcance, guardados, compartidos, vistas, likes, comentarios, tiempo de visualización de reels y seguidores ganados por publicación.
2. **Lee la estrategia del cliente en Notion** (página *Estrategia*): pilares, **ritmo editorial / pack**, tono, público, objetivos del trimestre y límites.
3. **Calcula los números** (en Python, no los inventa la IA): rendimiento por formato, mejores y peores posteos, frecuencia por mes, mejores días y franjas horarias, efecto de los CTA tipo "Comentá KIT", historias.
4. **Claude arma el informe** con el mismo estilo que el análisis de Metricool ("Lo que dicen tus números…") y **propone ideas** de carruseles, reels, fotos e historias para el mes siguiente, respetando la cantidad del pack.
5. **Sube todo a Notion:**
   - Una página **📊 Informe Instagram · dd/mm/aaaa al dd/mm/aaaa** dentro de la página del cliente.
   - Cada idea como fila nueva en **Planificación de contenido → Plan de publicaciones**, con **Estado: Idea**, Formato, Pilar, Fecha sugerida, Objetivo, Desarrollo (guion / texto por slide / secuencia de historias) y Copy + CTA.

Las bases de los clientes no son idénticas (en LUJIS el estado no tiene nombre, en HOLAMARKETING la fecha es "Fecha de publicacion" sin tilde, los pilares cambian por cliente). El script detecta las columnas por tipo y nombre aproximado, usa los pilares propios de cada cliente, y si falta una columna pone ese contenido en el cuerpo de la página de la idea.

---

## Instalación

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # completar tokens
cp clientes.example.yaml clientes.yaml
```

### 1. Notion

1. En Notion → *Settings → Connections → Develop or manage integrations* → **New integration** (interna). Capacidades: leer, insertar y actualizar contenido.
2. Copiá el token en `NOTION_TOKEN`.
3. En la página **Portal del cliente**, menú `···` → *Connections* → agregá la integración (se hereda a todos los clientes).

### 2. Meta (Instagram)

Hace falta una app en [developers.facebook.com](https://developers.facebook.com) (tipo **Business**, gratis). Es la identidad con la que el script le pide los datos a Meta. Cada cliente se conecta de una de estas dos formas (`conexion` en `clientes.yaml`):

#### a) Clientes dentro de un Business Manager / portfolio (`conexion: facebook`, default)

Requisito: Instagram **Empresa o Creador** vinculado a su página de Facebook, y esa página dentro de un portfolio de la agencia.

1. En la app, agregá el producto *Instagram* (API con inicio de sesión de Facebook).
2. En **cada portfolio** → *Usuarios del sistema* → creá un usuario del sistema (admin) y asignale la app y las páginas / cuentas de IG de ese portfolio.
3. Generá su token (vencimiento: nunca) con `instagram_basic`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement` y `business_management`.
4. **Un token por portfolio**: el primero en `META_ACCESS_TOKEN`, los demás en otras variables (`META_TOKEN_PORTFOLIO2`, …). En `clientes.yaml`, cada cliente indica el suyo con `token_env`.
5. `python -m informes_ig cuentas --token-env META_TOKEN_PORTFOLIO2` lista las cuentas de ese token con su `ig_user_id`.

#### b) Clientes que solo tienen Instagram (`conexion: instagram`)

No necesitan Business Manager ni página de Facebook, solo que la cuenta sea **profesional** (Empresa o Creador; se cambia gratis desde la app de Instagram).

1. En la app, agregá el producto *Instagram* → **API con inicio de sesión de Instagram**. Copiá el *ID* y la *clave secreta de la app de Instagram* a `INSTAGRAM_APP_ID` e `INSTAGRAM_APP_SECRET`.
2. En esa misma pantalla, en la configuración del inicio de sesión, cargá una **URI de redireccionamiento** (puede ser `https://holamarketing.com.ar/`) y poné exactamente la misma en `INSTAGRAM_REDIRECT_URI`.
3. Mientras la app no pase la revisión de Meta, cada cliente tiene que figurar como **evaluador de Instagram** en *Roles de la app* y aceptar la invitación desde su Instagram (*Configuración → Apps y sitios web → Invitaciones de evaluador*).
4. `python -m informes_ig conectar --cliente LUJIS` muestra un link. Se lo mandás al cliente, entra con su Instagram y acepta.
5. Llega a la página de la redirect URI con un `?code=...` en la dirección. Te pasa esa dirección y corrés `python -m informes_ig conectar --cliente LUJIS --codigo "<dirección>"`. El código dura pocos minutos y sirve una sola vez.

El permiso queda guardado en `datos/tokens/` y dura 60 días; el script lo renueva solo cada vez que corre (si pasan más de 60 días sin correrlo, hay que volver a conectar).

> Los permisos, nombres de menús y versiones de la API de Meta cambian seguido: si algo no coincide, revisá la documentación vigente de la Instagram Platform.

### 3. Claude

`ANTHROPIC_API_KEY` de [console.anthropic.com](https://console.anthropic.com). Modelo por defecto: `claude-opus-5` (se cambia con `CLAUDE_MODEL`).

### 4. Clientes

En `clientes.yaml` son obligatorios `nombre` y `notion_pagina_cliente` (la URL de la página del cliente en la base *Clientes*), más `ig_user_id` si el cliente se conecta por Business Manager. Todo lo demás se descubre solo. Verificalo con:

```bash
python -m informes_ig descubrir --todos
```

Muestra, por cliente, si encontró Estrategia, la base del plan, la opción de estado "Idea", los formatos, los pilares y el ritmo editorial. Si algo no aparece, se puede fijar a mano (`notion_estrategia`, `notion_plan_base`) o definir el `pack` en el YAML.

---

## Uso

```bash
# Informe de los últimos 90 días + ideas para el mes que viene, para un cliente
python -m informes_ig informe --cliente HOLAMARKETING

# Período y mes explícitos
python -m informes_ig informe --cliente LUJIS --desde 2026-07-01 --hasta 2026-09-30 --mes 2026-10

# Todos los clientes, sin escribir en Notion (revisar antes)
python -m informes_ig informe --todos --dry-run

# Solo el informe, sin cargar ideas
python -m informes_ig informe --cliente LUJIS --sin-ideas
```

Además de Notion, cada corrida deja en `datos/<cliente>/informe-<fecha>/` los datos crudos, las métricas calculadas, el resultado en JSON y el informe en `informe.md`. Con `--dry-run` solo se genera eso, para revisar antes de cargar.

Si una idea tiene el mismo título que una fila que ya existe en el plan, no se duplica.

### Historias

La API de Instagram **solo devuelve las historias de las últimas 24 horas**. Para que el informe incluya historias hay que capturarlas todos los días:

```bash
python -m informes_ig snapshot-historias --todos
```

Se guardan en `datos/<cliente>/historias.jsonl`. Hasta que se acumulen capturas, el informe dice que no hay datos de historias (pero igual propone ideas de historias según el ritmo editorial).

### Programarlo

Con `cron` en cualquier compu o servidor que quede prendido:

```cron
# Historias: dos veces por día
0 12,23 * * *  cd /ruta/crmholamarketing && .venv/bin/python -m informes_ig snapshot-historias --todos
# Informe + ideas: el día 25 de cada mes, para el mes siguiente
0 9 25 * *     cd /ruta/crmholamarketing && .venv/bin/python -m informes_ig informe --todos
```

---

## Qué tener en cuenta

- **Demora de datos:** Meta puede tardar hasta 48 h en consolidar métricas; los posteos de los últimos dos días pueden aparecer bajos.
- **Seguidores ganados por post:** muchas veces Meta lo devuelve en 0. El script lo detecta y el informe lo marca como dato no confiable en vez de sacar conclusiones.
- **Mejor horario:** se calcula con los datos propios del cliente (alcance mediano por día y franja), en la zona horaria configurada para cada cliente.
- **Costo:** la API de Meta y la de Notion son gratis. Claude cobra por uso: con `claude-opus-5`, un informe con ideas para un cliente cuesta del orden de US$0,50 a US$1, según la cantidad de publicaciones e ideas.

## Estructura

```
informes_ig/
  instagram.py   API de Meta: publicaciones, métricas, historias
  metricas.py    cálculos (formatos, tops, frecuencia, horarios, CTA)
  notion.py      lectura de estrategia, detección de columnas, carga de ideas e informe
  analisis.py    prompt y llamada a Claude con salida estructurada
  cli.py         comandos
tests/           pruebas (python -m pytest)
```
