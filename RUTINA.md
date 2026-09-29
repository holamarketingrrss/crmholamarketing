# Rutina: informe de Instagram + ideas en Notion

Instrucciones para que Claude (en una rutina o a pedido) haga el informe mensual de un cliente.
Los datos de Instagram salen de la API de Meta (variable `META_ACCESS_TOKEN`), y todo lo de
Notion se hace con el **conector de Notion**.

Si el pedido dice **"modo prueba"**, no escribas nada en Notion: mostrá el informe y las ideas en
la respuesta y listo.

## Clientes

| Cliente | Instagram | IG ID |
|---|---|---|
| HOLAMARKETING | @holamarketing | 17841449615689473 |
| iPhone Team | @iphoneteam.arg | 17841454516836263 |
| En la Cresta | @vivamosenlacresta | 17841405473067572 |
| Bunbury Miami | @bunburymiami | 17841401726909905 |
| TECNO | @tecnomorenooficial | 17841453209995629 |
| SWISS SNOW EXPERIENCE | @swisssnowexperience | 17841478412571886 |
| PAUSA | @enjoypausa | 17841472701688228 |
| Claudio García | @byclaudiogarcia | 17841409059528048 |
| Design Your Content | @designyourcontent | 17841462423348395 |

La página de cada cliente en Notion está en **Portal del cliente → Clientes**. Buscala por el
nombre del cliente; si no la encontrás con certeza, no adivines: decilo y seguí con el siguiente.

## Pasos por cliente

### 1. Datos de Instagram

```bash
pip install -q requests 2>/dev/null
python -m informes_ig.datos --ig-id <IG ID> --dias 90
```

Devuelve un JSON con el perfil y las métricas ya calculadas: rendimiento por formato, mejores y
peores posteos, frecuencia por mes, alcance por día y franja horaria, efecto de los CTA tipo
"Comentá PALABRA", tiempo de visualización de reels y si el dato de seguidores ganados es
confiable. **Usá esos números; no los recalcules ni inventes otros.**

Si falla por permisos o porque la cuenta no aparece, anotalo y seguí con el siguiente cliente.

### 2. Estrategia en Notion

Dentro de la página del cliente:
- **Estrategia**: leé pilares, ritmo editorial (cantidad de posteos, reels e historias del pack),
  tono, público, objetivos del trimestre y límites.
- **Planificación de contenido → Plan de publicaciones**: mirá las columnas de la base (los
  nombres cambian un poco entre clientes: el estado puede no tener nombre, la fecha puede estar
  sin tilde, los pilares son propios de cada cliente) y las filas de los últimos dos meses, para
  no repetir ideas.

### 3. Informe

Creá una subpágina dentro de la página del cliente:
**📊 Informe Instagram · dd/mm/aaaa al dd/mm/aaaa**

Estilo:
- Español rioplatense, claro y directo, sin jerga ni frases de gurú.
- Siempre con números concretos del JSON. Si un dato falta o no es confiable, decilo.
- Compará formatos y temas ("los carruseles educativos llegan 3 veces más lejos que los de venta").
- Nombrá los mejores posteos por su título y explicá por qué creés que funcionaron.
- Separá dato de interpretación ("creo que es por el contenido, no por el formato").
- Frecuencia real contra el ritmo editorial contratado.
- Mejores días y franjas horarias (indicá la zona horaria).
- Cerrá con recomendaciones para el mes que viene.

Secciones: resumen (3-4 oraciones) · lo que dicen los números · lo que funcionó · lo que no
funcionó · frecuencia · mejores horarios · recomendaciones · tabla top 5 por alcance (con link) ·
lista de ideas cargadas (con link a cada fila).

### 4. Ideas → Plan de publicaciones

Para el **mes siguiente**, creá una fila por idea en *Plan de publicaciones*:

| Columna | Valor |
|---|---|
| Name | Título de la idea |
| Estado | **Idea** |
| Formato | Carrusel, Reel, Foto o Stories (opciones existentes de la base) |
| Pilar | Uno de los pilares existentes de la base |
| Fecha de publicación | Fecha sugerida en los mejores días según los datos |
| Objetivo | Qué busca la pieza |
| Desarrollo | Guion del reel (gancho + escenas + cierre), texto slide por slide del carrusel, o la secuencia de historias día por día |
| Copy + CTA | Copy listo para publicar con su llamado a la acción |

Reglas:
- Cantidad: exactamente lo que marca el ritmo editorial para el mes (feed). Historias: una fila
  por semana con la secuencia diaria.
- Cada idea se apoya en algo que funcionó o corrige algo que no; explicalo al principio del cuerpo
  de la página de la idea ("Por qué esta idea: …").
- Aprovechá fechas especiales del mes relevantes para el público.
- No repitas ideas que ya están en el plan.
- Si a la base le falta alguna columna, poné ese contenido en el cuerpo de la página de la idea.

### 5. Cierre

Respondé con una línea por cliente: link al informe, cantidad de ideas cargadas, y cualquier
problema (cuenta sin datos, página no encontrada, columna faltante).

## Limitaciones conocidas

- Historias: la API solo da las de las últimas 24 h, así que el informe no las analiza (sí se
  proponen ideas de historias según el ritmo editorial).
- Meta puede tardar hasta 48 h en consolidar métricas de los posteos más nuevos.
