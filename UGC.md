# Rutina: evaluación de creadoras UGC (lunes)

Instrucciones para que Claude revise las creadoras nuevas de la base **📸 UGC y Creadoras** de
Notion y deje en cada ficha un informe para decidir a quién contratar. Datos de Instagram con
`META_ACCESS_TOKEN`; todo lo de Notion con el **conector de Notion**.

Si el pedido dice **"modo prueba"**, no escribas nada en Notion: mostrá los informes en la
respuesta y listo.

- Base: https://app.notion.com/p/d41979b230f64c26b4e8f04bdda72ffc
- Data source: `collection://dcba04bc-7116-46b6-b23c-105c8b562f63`

Escribí solo en esa base. No toques la copia "UGC y Creadoras · COPIA …" ni otras bases. No
cambies Cliente, Estado, Propuesta, Precio ni los datos de contacto: esos los maneja el equipo.

## Pasos

### 1. A quién revisar

Filas con **Evaluación IA** vacía y **Estado** distinto de Descartada, de la más nueva a la más
vieja (Fecha de ingreso). Máximo 40 por corrida; si quedan más, decilo en el cierre.

El usuario sale de la columna **Instagram** (link). Si está vacía, buscalo en el cuerpo de la
ficha ("Instagram:" en las respuestas del formulario) y completá la columna con
`https://www.instagram.com/<usuario>`.

### 2. Datos del perfil

```bash
pip install -q requests 2>/dev/null
python -m informes_ig.ugc --usuario <usuario1> --usuario <usuario2> ...
```

Devuelve, por cuenta: seguidores, días desde el último posteo, posteos en 30 y 90 días,
interacción mediana y tasa de interacción, % de reels, los 3 mejores posteos y una
`sugerencia` de semáforo. **Usá esos números; no los inventes.**

Si una cuenta vuelve con `"visible": false` (cuenta personal, privada o inexistente): Evaluación
IA = 🟡 Revisar y Resumen IA = "Meta no muestra esta cuenta (personal o privada): revisar a mano".

### 3. Evaluación

Partí de la `sugerencia` y ajustala solo con un motivo concreto que tenés que escribir:
- **🟢 Recomendada**: publica seguido, tiene interacción real y hace el tipo de contenido que
  buscamos (UGC, reels de producto, hablar a cámara).
- **🟡 Revisar**: le falta algún dato, la interacción es baja o el contenido no está claro.
- **🔴 No**: inactiva (más de 60 días sin publicar) o nada de su contenido sirve para marcas.

Mirá también lo que la creadora contó en el formulario (cuerpo de la ficha): nicho, ciudad,
canales, portfolio, si trabaja por canje. Sumalo al informe si ayuda a decidir.

### 4. Escribir en Notion

En cada fila:
- **Evaluación IA**: el semáforo.
- **Resumen IA**: una o dos líneas, con números ("Publica 6 veces por mes, 4,1% de interacción,
  casi todo reels de skincare. Buena para producto.").
- **SEGUIDORES**: el número actualizado.
- Al final del cuerpo de la ficha, debajo de las respuestas del formulario, agregá:

```
### Evaluación IA · dd/mm/aaaa
- Seguidores: …
- Último posteo: hace … días · Posteos en 30 días: … · en 90 días: …
- Interacción mediana: … (… % de los seguidores)
- Formatos: …% reels
- Mejores posteos: (links)
- Lectura: 2 o 3 oraciones sobre si conviene contratarla y para qué.
```

Estilo: español rioplatense, claro y directo. Separá dato de interpretación.

### 5. Cierre

Respondé con un resumen: cuántas revisaste, cuántas 🟢, 🟡 y 🔴, la lista de las 🟢 con su link,
y cualquier problema (token vencido, cuentas no visibles, filas sin Instagram).
