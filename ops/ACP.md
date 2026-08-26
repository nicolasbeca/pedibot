# PediBot en Virtuals ACP (idea 10) — cómo lo hacemos

**Qué es**: el Agent Commerce Protocol de Virtuals es un mercado on-chain donde un agente *cliente* contrata a un agente *proveedor*; el pago queda en escrow y se libera tras la evaluación. PediBot entra como **proveedor** de un servicio: "respuesta pediátrica con fuentes verificadas" (la misma que da gratis a los padres), pagada en $VIRTUAL o $PDBT por otros agentes. Los padres no pagan nunca.

**Lo que ya está en el código** (25-26 ago):
- `POST /api/agent/ask` — mismo motor (triaje, fuentes, verificador, memoria no), JSON con `answer`, `sources`, `level`, `banner`, `disclaimer`. Autenticado con cabecera `X-Api-Key` (claves separadas por comas en `AGENT_API_KEYS` del `.env`). Registrado en la base con sesión `agent_…` para contarlo en el informe.
- Mismo triaje y rechazo fuera de ámbito: si el agente cliente pregunta algo que no es pediatría, recibe "no tengo fuente" y no se cobra nada útil.

**Lo que hace falta del operador** (Virtuals cambia el flujo con frecuencia; verificar en app.virtuals.io → ACP):
1. En el perfil del agente PediBot (ya verificado con la web), activar **ACP → Register as seller/provider**. Pide: nombre del servicio, descripción, precio por trabajo, wallet del agente (Virtuals crea una wallet no custodial) y un **endpoint** o el uso de su SDK.
2. Servicio propuesto: `pediatric_sourced_answer` — entrada `{question, lang, country}`; salida = el JSON de `/api/agent/ask`. Precio inicial sugerido: el mínimo que permita ACP (el coste real es ≈ 0,0005 $).
3. Si ACP exige integrar su SDK (`acp-python` / `virtuals-acp`) en lugar de llamar a un endpoint HTTP, el adaptador es pequeño: un proceso que escucha trabajos ACP y llama a `/api/agent/ask` con la clave. Lo escribo cuando tengamos acceso al panel de proveedor y sepamos la versión exacta del SDK.
4. Generar una clave: `python -c "import secrets;print(secrets.token_urlsafe(24))"` → `AGENT_API_KEYS=<clave>` en `/opt/pedibot/.env` → `systemctl restart pedibot-api`.

**Prueba**:
```
curl -s -X POST https://pedibot.xyz/api/agent/ask -H "content-type: application/json" -H "x-api-key: <clave>" \
  -d '{"question":"my 3 year old has a barking cough","lang":"en","country":"GB"}'
```

**Riesgos y límites**: uso médico por agentes sin contexto → misma política (no diagnóstico, banner de urgencias, disclaimer en cada respuesta); revisar los términos de ACP sobre servicios de salud antes de publicar el servicio; cuota de 60 trabajos/hora por clave (rate limit del API) — subir si hace falta.
