# Virtuals / EconomyOS / ACP — todo lo aprendido en la práctica

> Escrito el **26-ago-2026** montando PediBot como agente proveedor. Todo lo de aquí está **verificado
> ejecutándolo**, no leído en la documentación (que a esa fecha estaba a medio migrar y devolvía 404 en
> varias rutas del whitepaper). Copia gemela en `D:/Nicolas/Regime_Virtuals/`.

## 1. El mapa: tres cosas distintas que se confunden

| Capa | Qué es | Dónde |
|---|---|---|
| **Capital Market** | Lanzamiento y trading de tokens de agente (bonding curve → Uniswap) | `Launch Token` |
| **EconomyOS** | Identidad y "banca" del agente: wallet, correo, tarjeta, firmantes, cómputo | `Create Agent` |
| **ACP** (Agentic Commerce) | Mercado donde agentes se contratan y se pagan entre sí | pestaña `Agentic Commerce` |

**Lo importante**: un token puede existir **sin agente** (aparece como *"Standalone token"*). Sin agente no hay wallet ni identidad, y por tanto **no se puede vender nada en ACP**. El token no es el agente.

## 2. Crear el agente (formulario `New Agent`)

- **Identity** (obligatorio): nombre (≤20 car.) y **descripción ≤100 caracteres** (el botón *Launch Agent* sigue gris hasta que hay 10+).
- **Console** (opcional): runtime gestionado (OpenClaw/Hermes) con hosting y cómputo. **Saltar si ya tienes tu propio servidor.** Pide enlazar un correo.
- **Agent Email**: se provisiona solo, `<nombre>@agents.world`. Gratis, no hay nada que rellenar.
- **Agent Card** (opcional): tarjeta virtual de un solo uso para que el agente pague compras. Dejar apagada salvo que se necesite.
- **Wallet**: `New · Mint a fresh wallet` crea una wallet embebida de **Privy** (una EVM y una Solana). También se puede elegir una existente.
- **Token**: `Skip` / `Create new` / **`Link existing`** ← esta es la que permite **conservar el token ya lanzado y sus holders**. Se elige el token y listo; después la ficha del agente muestra *AGENT TOKEN $XXX*.

**Créditos gratuitos de inferencia**: se piden enlazando **GitHub o X** en la pestaña *Compute*; los aprueba a mano su equipo de DevRel y **una cuenta respalda un solo agente**. Si tu usuario de Virtuals ya tiene una X enlazada, Privy responde *"You cannot authorize more than one account for this user"* — hay que desenlazar la anterior o usar GitHub. **Solo sirven para el runtime gestionado**: si el agente corre en tu servidor con tu propio LLM, no hacen falta.

## 3. Firmantes: la wallet nace inerte

> *"Until a signer is added, the agent wallet is inert — no transactions can be sent, no messages signed, no jobs initiated."*

Dos caminos:
- **UI** → *Signers* → `+ Add Key` (genera la clave en el navegador).
- **CLI** → `acp agent add-signer` (genera la clave **en la máquina donde corre la CLI** y la persiste tras aprobar en el navegador). **Este es el bueno para un servidor**: la clave privada nunca sale del servidor ni pasa por el chat/correo.

### Secuencia exacta que funciona en un servidor sin escritorio

```bash
npm i -g @virtuals-protocol/acp-cli          # la CLI es Node, no Python
acp configure start --json                    # → {"url": …, "requestId": …}
#   ↳ el humano abre esa URL y firma con su cuenta de Virtuals
acp configure complete --request-id <id> --json   # → {"status":"authenticated", walletAddress}

acp agent list --json                         # ver agentes y quedarte con el id
acp agent use --agent-id <agentId>
acp agent add-signer --agent-id <agentId> --policy restricted --no-wait --json
#   ↳ devuelve {signerUrl, requestId, publicKey}; el humano abre signerUrl y aprueba
acp agent signer-status --agent-id <agentId> --request-id <rid> --public-key "<publicKey>" --json
#   ↳ {"status":"pending"} hasta que aprueba; luego {"status":"completed"}
```

**Trampas encontradas**:
- La `signerUrl` **debe llevar el parámetro `publicKey` completo y URL-encoded** (`+`→`%2B`, `/`→`%2F`, `=`→`%3D`). Si se recorta, la página carga en blanco y parece que "no sale nada".
- Caduca en 5 minutos, pero `signer-status` sigue diciendo `pending` hasta que caduca de verdad: se puede reintentar sin regenerar.
- Hay que abrirla **en el navegador con la sesión de Virtuals iniciada**.
- `signer-status` exige `--agent-id`, `--request-id` **y** `--public-key`; sin los tres da `NO_ACTIVE_AGENT` o error de opción.

### Políticas del firmante

`restricted` (autoriza transacciones ACP) · `deny-all` (aprobación manual de todo) · `unrestricted` (sin aprobación) · o una personalizada con `acp policy`.

⚠️ **Con `restricted` siguen apareciendo aprobaciones manuales** para llamadas RPC que no son ACP puro:

```
[PrivyAlchemy] Manual approval required.
  Approve at: https://app.virtuals.io/wallet/approve-transaction?id=…
  Reason: RPC request denied due to policy violation
```

El comando termina igualmente (cae a REST), pero para un proveedor autónomo hay que vigilarlo: si un trabajo se queda esperando aprobación, tocará una política personalizada o `unrestricted`. **Decisión pendiente**; empezar siempre por `restricted`.

## 4. CLI vs SDK de Python

- `pip install virtuals-acp` (SDK) espera el flujo **v1**: `WHITELISTED_WALLET_PRIVATE_KEY` (clave EVM en crudo) + `AGENT_WALLET_ADDRESS` + `ENTITY_ID`.
- El flujo nuevo de EconomyOS usa **wallets de Privy + firmante P256 en el llavero de la CLI**, así que **no tienes** una clave EVM en crudo → **el SDK no encaja** y hay que ir por la CLI.
- Además hay conflicto de dependencias: `virtuals-acp` exige `eth-account<0.14`, así que si tu proyecto pide `>=0.14` no resuelve (fijar `eth-account>=0.13.7`).

## 5. Ofertas (Offerings)

Tres tipos, cada uno con su tabla en la UI y su comando:
- **Jobs Offered** — trabajo puntual pagado (`acp offering …`). Campos: *Job Name, Price, SLA, Requirement, Deliverable*.
- **Resources Offered** — una URL con parámetros.
- **Subscriptions Offered** — cuota periódica.

```bash
acp offering create \
  --name "…" --description "…" \        # descripción: MÁXIMO 500 caracteres (HTTP 400 si te pasas)
  --price-type fixed --price-value 0.05 \   # USDC
  --sla-minutes 5 \
  --requirements '<JSON Schema de la entrada>' \
  --deliverable  '<JSON Schema de la salida>' \
  --no-required-funds --no-hidden --json
```

`--required-funds` es para trabajos donde el cliente además te adelanta capital (tokens para operar, gas…), distinto de tu tarifa. La UI tiene `Export All` / `Import All`, útil para versionar las ofertas en el repo.

## 6. Ciclo de vida de un trabajo (lado proveedor)

```bash
acp job list --json                       # trabajos activos (REST puro) ← usar ESTE
acp job history --job-id <id> --json      # contexto completo, mensajes y requirement
acp job watch --job-id <id>               # bloquea hasta que te toca actuar
acp events listen --output eventos.jsonl  # o streaming a fichero…
acp events drain --file eventos.jsonl --limit 20   # …y consumirlo por lotes
acp provider set-budget --job-id <id> --amount 0.05    # proponer precio (USDC)
acp provider submit --job-id <id> --deliverable '<texto o JSON>'
```

⚠️ **`acp job list --all` se cuelga con `restricted`.** El flag `--all` (y `--legacy`) añade los trabajos
del contrato viejo, que se leen **on-chain**; esa llamada RPC la deniega la política y la CLI se queda
esperando una aprobación manual hasta agotar el tiempo. Medido el 26-ago: `acp job list` a secas devuelve
`{"jobs":[]}` en **3 s**; con `--all`, **3 minutos** y ni un dato. Para un proveedor que sondea, usar
siempre `acp job list` a secas (v2, REST puro).

Cadena por defecto **Base (8453)**; los pagos van en **USDC** y quedan en escrow hasta la evaluación.

**Cómo lo montamos en PediBot**: un servicio systemd (`ops/acp_worker.py`) que **sondea** `acp job list` cada 30 s en vez de mantener un socket, y para cada trabajo propone presupuesto y luego entrega. La respuesta la genera el motor de siempre a través de `/api/agent/ask` (mismo triaje, mismas fuentes, mismo verificador). Los nombres de campo de los payloads ACP **no son estables**, así que el trabajador busca las claves de forma recursiva y registra el JSON crudo la primera vez que ve un trabajo.

## 7. Datos de ejemplo (PediBot, por si sirven de plantilla)

- Agent id `01a03e84-9819-7479-a366-9be9c00e7354` · wallet EVM `0x30d331ee2dc619ad4c353969b18586e5c0ce3ebb` · Solana `4Jrg7yNaR8x6PehYTtyP912GRuhbgmAD9XfETsq3iuze`
- `role: HYBRID` (puede comprar y vender) · `builderCode: bc_yi3vvkhy` · correo `pedibot@agents.world`
- Token vinculado: PDBT (Base, `virtualAgentId 39535`) — ojo, el campo `chains[].active` seguía en `false` justo después de vincular.
- Oferta creada: `01a03e94-20a1-7a00-aed6-79cc26e8b8f9`, 0,05 USDC, SLA 5 min.

## 8. Resumen de trampas (para no repetirlas)

1. Token ≠ agente: sin agente no hay ACP.
2. Al crear el agente, **`Link existing`** o pierdes el token y los holders.
3. Descripción del agente ≤100 car.; de la oferta ≤500 car.
4. La URL de aprobación del firmante necesita el `publicKey` **entero y codificado**.
5. `restricted` no elimina todas las aprobaciones manuales… y **cuelga** `acp job list --all` / `--legacy` (lectura on-chain): usar `acp job list` a secas.
6. El SDK de Python es del flujo viejo; con EconomyOS se va por CLI.
7. `virtuals-acp` choca con `eth-account>=0.14`.
8. Los créditos gratis de inferencia solo sirven si usas su runtime.
9. Una cuenta de X/GitHub respalda **un solo agente**.
10. La documentación oficial estaba a medias (404 en varias rutas): la fuente fiable fue `acp <comando> --help`.

---

## Actualizado el 1-sep-2026 en la copia de Regime

Montando el segundo agente (Regime) salieron cosas que **no están arriba** y que aplican
igual aquí. La copia con todo es `D:/Nicolas/Regime_Virtuals/VIRTUALS_APRENDIDO.md` §8-§10.
Resumen de lo nuevo:

- **La CLI exige Node ≥ 20** y falla con `ERR_REQUIRE_ESM`, que no dice nada de la versión.
- **`HOME` decide dónde vive el llavero del firmante**: hay que correr la CLI como el
  usuario del servicio, y el unit lleva `Environment=HOME=…`. Creado como root, el servicio
  no puede firmar.
- **Cada propiedad del esquema necesita su `description`**, también las del entregable, o la
  UI marca la oferta con «Missing descriptions».
- **`cluster` y `category` del agente no se tocan por CLI** y no hay token que reutilizar (la
  CLI se autentica firmando). Ofertas y recursos sí se editan.
- **Los `Resources Offered` son URLs públicas sin autenticación**: sirven para lo que ya
  publicas gratis, y son superficie de búsqueda a coste cero.
- **`acpx.virtuals.io/api/agents` es el registro VIEJO** (nada posterior al 22-jul-2026): no
  sirve para medir el mercado actual.
- Cifras del mercado, convención de nombres (`snake_case`) y precios reales: §10 de la otra
  copia.
