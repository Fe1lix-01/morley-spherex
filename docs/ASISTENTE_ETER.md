# Asistente ÉTER (chatbot local)

Asistente de ayuda del visor. Responde preguntas sobre la interfaz, la lógica del proyecto y el material MORLEY.
**Es local: no usa API, no cuesta nada, no necesita internet ni backend.** Responde solo con lo que está escrito en su base de conocimiento; si no lo sabe, lo dice ("No consta en el material verificado") y nunca inventa.

Autor: Alex (`dev_alex`).

## Qué hace

- Botón flotante **Ayuda** (abajo a la derecha) con el robot **Astro**. Abre un chat.
- Dos modos:
  - **Explorar**: explica cómo usar el visor, en sencillo.
  - **Científico**: detalles técnicos (bandas, filtros, ZOGY, contratos, estado del proyecto). Astro se pone lentes.
- Entiende errores de ortografía, sinónimos y preguntas libres ("como funcionan las epocas", "q es zogi").
- Las respuestas a "¿cómo funciona…?" van paso a paso.
- Se puede **mover** (arrastrando la cabecera), **redimensionar** (esquinas), cambiar **transparencia** y **tamaño** con los botones de la barra, y **restablecer** con el botón de reinicio o doble clic en la cabecera.
- La posición y el tamaño se guardan en el navegador de cada persona (`localStorage`, clave `eter-chat-rect`).

## Archivos (4)

| Archivo | Qué es |
|---|---|
| `apps/web/src/components/chat/ChatBot.tsx` | La interfaz: botón, ventana, arrastre, mensajes |
| `apps/web/src/components/chat/Robot.tsx` | El robot Astro (SVG) |
| `apps/web/src/components/chat/chatEngine.ts` | El buscador de respuestas (sin modelo de IA) |
| `apps/web/src/data/chatKnowledge.ts` | La base de conocimiento (aprox. 120 entradas) |

Se monta en **`apps/web/src/app/preview/layout.tsx`**:

```tsx
import ChatBot from "@/components/chat/ChatBot";
// ...
return <Providers>{children}<ChatBot /></Providers>;
```

Por eso **solo aparece en `/preview`** (no en `/catalog` ni en `/`). Para que salga en otra ruta, se agrega `<ChatBot />` en el layout de esa ruta.

No requiere paquetes nuevos: usa MUI, que ya está en el proyecto.

## Cómo agregar o corregir una respuesta

Todo se edita en `apps/web/src/data/chatKnowledge.ts`. Cada respuesta es una entrada:

```ts
{
  id: "como-epocas",              // identificador único
  q: "¿Cómo funcionan las épocas simuladas?",   // pregunta típica (también sale como botón)
  keys: ["epoca", "épocas simuladas", "reproducir"], // palabras o frases que la gente usaría
  a: "Texto de la respuesta.\nUsa \\n para saltos de línea.",
  how: true,                      // opcional: true si explica CÓMO funciona algo
}
```

- Las entradas están en dos listas: `explorar` y `cientifico`.
- `keys` no necesita acentos ni mayúsculas. Conviene poner frases completas y sinónimos.
- Los botones sugeridos al abrir cada modo están en `SUGGESTED`.
- Los sinónimos globales (por ejemplo "zogi" → "zogy") están en `SYNONYMS`.
- Las entradas marcadas `// REVISAR` se redactaron a partir del código y falta confirmarlas contra la interfaz real (menú, SIMBAD, gestos, ajuste de controles). **Si alguien conoce el dato correcto, corríjalo ahí.**
- La entrada `m-estado` tiene el estado del proyecto con fecha (14-11-2026). Hay que actualizarla cuando cambie.

## Si a alguien no le carga igual

Revisar en este orden:

1. **Rama.** El chat completo (robot, translúcido, movible) está en `dev_alex` y en las ramas que ya la mezclaron. `develop` **todavía no lo tiene** hasta que se haga el PR de `dev_alex`. Quien parta de `develop` no lo va a ver.
   Comprobar: `git log --oneline -3` debe mostrar un commit de `feat(web): agrega asistente de ayuda...` o posterior.
2. **Ruta.** Abrir `http://localhost:3000/preview`. En otras rutas no hay chat.
3. **Reiniciar.** Parar `pnpm dev` (Ctrl+C), correr `pnpm install` y volver a `pnpm dev`. Luego recargar con **Ctrl+Shift+R**.
4. **Posición rara o fuera de pantalla.** Se guardó un tamaño o lugar distinto en ese navegador. Doble clic en la cabecera del chat, o en la consola del navegador: `localStorage.removeItem("eter-chat-rect")` y recargar.
5. **Traductor de Chrome.** Si Chrome traduce la página, la hidratación falla y puede romper componentes. `app/layout.tsx` ya declara `lang="es"`, pero si no tienen ese commit, desactivar la traducción.
6. **Tapa o lo tapa otro botón.** El botón Ayuda está pegado a la esquina inferior derecha (`FAB_RIGHT`, `FAB_BOTTOM` al inicio de `ChatBot.tsx`). Si choca con otro panel, esas constantes se cambian ahí.
7. **Error en consola o en la N roja de Next.** Copiar el texto del error y el archivo que indica.

Al reportar un problema, decir: rama, resultado de `git log --oneline -1`, URL y captura de pantalla.

## Límites

- No es una IA generativa: no razona ni relaciona cosas que no estén escritas. Si una pregunta no coincide con ninguna entrada, responde con el mensaje de "no tengo / no consta".
- No afirma descubrimientos ni resultados científicos que no estén en el material verificado.
- Si hace falta que relacione preguntas más libremente, está **pendiente** una mejora gratuita con embeddings en el navegador (Transformers.js) como reordenador de resultados. No está implementada.
