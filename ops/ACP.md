# PediBot en Virtuals ACP (idea 10) — cómo lo hacemos

**Qué es**: el Agent Commerce Protocol de Virtuals es un mercado on-chain donde un agente *cliente* contrata a un agente *proveedor*; el pago queda en escrow y se libera tras la evaluación. PediBot entra como **proveedor** de un servicio: "respuesta pediátrica con fuentes verificadas" (la misma que da gratis a los padres), pagada en $VIRTUAL o $PDBT por otros agentes. Los padres no pagan nunca.

**Lo que ya está en el código** (25-26 ago):
- `POST /api/agent/ask` — mismo motor (triaje, fuentes, verificador, memoria no), JSON con `answer`, `sources`, `level`, `banner`, `disclaimer`. Autenticado con cabecera `X-Api-Key` (claves separadas por comas en `AGENT_API_KEYS` del `.env`). Registrado en la base con sesión `agent_…` para contarlo en el informe.
- Mismo triaje y rechazo fuera de ámbito: si el agente cliente pregunta algo que no es pediatría, recibe "no tengo fuente" y no se cobra nada útil.

**Situación real (26-ago, capturas del operador)**: $PDBT figura como **«Standalone token»** y la tarjeta ofrece **«Link EconomyOS agent →»**, que responde *«No available agents found. Create a new agent to link to your token.»* Es decir: el token existe pero **no hay agente**; sin agente no hay identidad ni wallet en EconomyOS y por tanto no se puede vender en ACP.

**Camino para el operador**:
1. `Create Agent` (arriba a la derecha en virtuals.io) → crear el agente **PediBot**: nombre, descripción (la de «How it works»), avatar (LOGO_PEDIBOT_CARA), web `https://pedibot.xyz`, X `@pedibotai`.
2. **No lanzar un token nuevo.** Buscar la opción de vincular/migrar el token existente (`0x196A…15E1`). Si el flujo solo ofrece lanzar uno nuevo o pedir $VIRTUAL, **parar** y mandar captura.
3. Volver a la tarjeta del token → **Link EconomyOS agent** → elegir el agente PediBot.
4. Con el agente vinculado: **Agentic Commerce → Offerings → crear oferta**. Cuando pida cómo se entrega el servicio (endpoint HTTP o worker con su SDK/CLI), mandar captura: si es endpoint, `https://pedibot.xyz/api/agent/ask` + clave; si es SDK, escribo el worker (la doc está en os.virtuals.io/acp → cli/provider-workflow).
5. Servicio propuesto: `pediatric_sourced_answer` — entrada `{question, lang, country}`; salida = el JSON de `/api/agent/ask`. Precio inicial: el mínimo que permita ACP (el coste real es ≈ 0,0005 $).

**Notas**: si ACP exige su SDK/CLI en vez de un endpoint, el adaptador es un worker que escucha trabajos y llama a `/api/agent/ask`; lo escribo cuando se vea la pantalla. La clave se genera con `python -c "import secrets;print(secrets.token_urlsafe(24))"` → `AGENT_API_KEYS=<clave>` en `/opt/pedibot/.env` → `systemctl restart pedibot-api`.

**Prueba**:
```
curl -s -X POST https://pedibot.xyz/api/agent/ask -H "content-type: application/json" -H "x-api-key: <clave>" \
  -d '{"question":"my 3 year old has a barking cough","lang":"en","country":"GB"}'
```

**Riesgos y límites**: uso médico por agentes sin contexto → misma política (no diagnóstico, banner de urgencias, disclaimer en cada respuesta); revisar los términos de ACP sobre servicios de salud antes de publicar el servicio; cuota de 60 trabajos/hora por clave (rate limit del API) — subir si hace falta.
