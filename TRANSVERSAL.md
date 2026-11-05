# Rutina: área Transversal (onboarding y recordatorios)

Instrucciones para que Claude haga, todos los días a las 9 (hora de Buenos Aires), el onboarding de
los clientes nuevos y los recordatorios al equipo. Notion con el **conector de Notion**, Drive con el
**conector de Google Drive** y mails con el **conector de Gmail**.

Si el pedido dice **"modo prueba"**, no escribas ni mandes nada: mostrá lo que harías y listo.

Criterio (Hola Marketing OS, cap. 8): un cliente es cliente cuando **firmó el contrato y pagó**.
Antes de eso no se arranca nada. El objetivo es que en menos de una semana vea movimiento,
organización y un equipo trabajando detrás de su marca.

## Parte 1 · Onboarding

### 1. A quién

En la base **👥 Clientes** (`collection://2feed874-1abb-81d3-9ef8-000bcb5a45c0`): filas con
**Contrato firmado** y **Pago confirmado** tildados y **Portal Setup** sin tildar. Si no hay
ninguna, pasá a la Parte 2.

### 2. Portal en Notion

- Si la página del cliente está vacía, aplicale la plantilla de la base según **Category**:
  *Single Platform Template* (Single Social Media Management) o *Multiple Platform Template*
  (Multiple). No la armes a mano.
- Reemplazá los marcadores (`[Client Name]`, `@accountname`, `[Your Brand]`) con lo que haya en la
  ficha. Lo que no sepas, dejalo marcado para completar.
- Dentro, creá la página **Estrategia** y adentro **Insumos del mes** (📥) con el texto de
  `ESTRATEGIA.md`.

### 3. Carpeta en Drive

Dentro de **5. CLIENTES** (`15ePETYabnHP8NXaDa7VTDGkbo3QIEnlK`) creá la carpeta con el nombre del
cliente en mayúsculas, y adentro:

```
01 Marca y manuales
02 Accesos
03 Material del cliente (fotos y videos que manda)
04 Producciones
05 Contenido publicado
06 Estrategia e informes
07 Contrato y pagos
```

Si ya existe una carpeta con ese nombre, usala y creá solo las subcarpetas que falten. Pegá el link
de la carpeta en la página del cliente.

### 4. Mail de bienvenida

Armá un **borrador** en Gmail (no lo mandes: lo revisa y lo manda Yvette) para el mail del cliente
que figure en la ficha, con la plantilla `plantillas/mail-bienvenida.md`. Seguí sus reglas de
adaptación: accesos solo de lo contratado, rubro, y cronograma con fechas reales desde hoy. El
recibo del pago lo adjunta el equipo: avisalo en el cierre.

Si la ficha no tiene mail, no lo inventes: avisalo en el cierre.

**Mail de acuerdo** (`plantillas/mail-acuerdo.md`): es el que se manda cuando hay acuerdo pero
todavía no hay contrato ni pago. Esta rutina no lo dispara sola; armalo como borrador cuando lo
pidan ("mail de acuerdo para <cliente>").

### 5. Checklist interno

En la página del cliente, una sección **Onboarding · checklist interno** con tareas sin tildar
(procedimiento del cap. 8):

- [ ] Crear el grupo de WhatsApp (cliente, Juliana, Yvette y quien corresponda al servicio)
- [ ] Mandar el mail de bienvenida (borrador listo en Gmail)
- [ ] Recibir accesos y material
- [ ] Investigar la marca y la competencia (ver auditoría)
- [ ] Coordinar producción si aplica (Victoria con Matías)
- [ ] Estrategia e ideas del primer mes
- [ ] Primera entrega al cliente
- [ ] Sumar al cliente a las tablas de `RUTINA.md` (IG ID, página, Plan de publicaciones)

### 6. Auditoría inicial

Con el usuario de Instagram de la ficha:

```bash
python -m informes_ig.ugc --usuario <usuario>   # perfil público: frecuencia, interacción, formatos, mejores posteos
```

Más la web del cliente y una búsqueda de 3 a 5 competidores. Creá dentro de la página del cliente
**Auditoría inicial · dd/mm/aaaa** con: resumen · cómo está hoy el perfil (bio, link, destacadas,
estética) · números (del JSON) · qué funciona · qué corregir · competidores · oportunidades · plan
de los primeros 30 días. Separá dato de interpretación; si Meta no muestra la cuenta, decilo.

Exportala a PDF **Onboarding y auditoría · <Cliente>** en *06 Estrategia e informes*.
*(Pendiente: ajustar la estructura al ejemplo de auditoría de Yvette.)*

### 7. Cerrar

Tildá **Portal Setup**. No toques Contrato firmado, Pago confirmado ni Client Invite.

## Parte 2 · Recordatorios al equipo

Revisá el **Plan de publicaciones** de cada cliente de las tablas de `RUTINA.md`:

- Piezas con fecha de publicación **hoy, mañana o pasado** cuyo estado no sea Publicado ni
  Programado.
- Piezas con fecha **vencida** que siguen sin publicar.
- El ticket de historias del mes siguiente, si faltan 5 días o menos para fin de mes y no existe.

Mandá **un solo mail** a la casilla de Hola Marketing con asunto
**Pendientes del equipo · dd/mm**, agrupado por cliente: pieza (con link), fecha, estado y
responsable si la base lo tiene. Si no hay nada pendiente, no mandes mail.

## Cierre

Respondé con: clientes onboardeados (links a portal, carpeta, borrador y auditoría), clientes a los
que les falta algo (mail, Instagram, Category) y cantidad de recordatorios enviados.
