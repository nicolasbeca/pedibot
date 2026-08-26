# Virtuals — formulario "New Agent" (26-ago-2026)

Objetivo: crear la identidad EconomyOS de PediBot y **vincular el token existente $PDBT** (no lanzar otro).
PediBot corre en nuestro propio VPS, así que **no** usamos el runtime gestionado (Console).

## Identity (obligatorio)

- **Agent Name**: `PediBot`
- **Description** (máx. 100 caracteres) — recomendada:

```
Paediatric answers for parents, only from published guidelines, with the source in every sentence.
```

Alternativas:
```
Free assistant for parents: answers only from paediatric guidelines, and says when to go to the ER.
```
```
Free paediatric guidance for parents, grounded in published guidelines. Never a diagnosis.
```

## Console (opcional) → **no activar**

Es un runtime gestionado (OpenClaw/Hermes) con hosting y cómputo. PediBot ya corre en Hetzner con su propio motor y sus fuentes. No enlazar email por ahora.

## Agent Email

Se asigna solo (`…@agents.world`). Nada que rellenar. Útil más adelante para que otros agentes escriban.

## Agent Card → **dejar apagado**

Tarjeta de un solo uso para que el agente pague compras online. No lo necesitamos.

## Wallet → **New · Mint a fresh wallet**

Cartera embebida nueva (Privy), separada de la tuya personal. Es la que cobrará los trabajos de ACP.

## Token → **Link existing** → PediBot $PDBT (`0x196A…15E1`)

Ya aparece seleccionado en la captura. **Nunca "Create new"**: duplicaría el token y partiría a los 3.900 holders.

## Después de "Launch Agent"

1. **Compute tab → conectar X (@pedibotai)** o GitHub: da créditos semanales gratuitos de inferencia. Gratis, sin compromiso.
2. **Agentic Commerce → Offerings → New offering**:
   - **Name**: `Pediatric answer with sources`
   - **Description** (larga):
     > A parent-facing paediatric question answered only from published guidelines (SEUP, AEP, NHS, CDC, WHO, MedlinePlus). Every clinical sentence names its source. A rule-based triage runs first and flags emergencies; medication doses come from fixed tables, never from the model. Returns JSON: level, banner, answer, sources, disclaimer. Not medical advice; never a diagnosis.
   - **Input**: `{"question": "...", "lang": "en|es", "country": "GB"}`
   - **Output**: `{"level", "banner", "answer", "sources", "verification", "disclaimer"}`
   - **Price**: el mínimo que permita ACP (coste real ≈ 0,0005 $ por respuesta).
   - **Delivery**: si pide endpoint → `https://pedibot.xyz/api/agent/ask` (cabecera `X-Api-Key`, la clave la genero yo). Si pide worker con su SDK/CLI → captura y lo escribo.
3. Avisar para poner `AGENT_API_KEYS=<clave>` en `/opt/pedibot/.env` y reiniciar la API.

## Lo que NO hay que hacer

- No lanzar un token nuevo ni migrar liquidez.
- No aprobar transacciones que pidan $VIRTUAL sin comprobarlo antes.
- No activar Console ni Agent Card "por probar": provisionan recursos que no usamos.
