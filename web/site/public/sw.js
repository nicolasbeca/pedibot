/**
 * PediBot sin cobertura (19-sep-2026, fase F1 del plan de APP.md).
 *
 * El motivo de que esto exista, y de que sea lo primero que se construye: **sin red, una web es
 * una pantalla en blanco**. El proyecto apunta a India, el mundo árabe y África, donde la
 * cobertura se acaba a mitad de mes, y lo que hace falta a las tres de la mañana —el número al
 * que llamar, los signos que significan ir ya, la próxima vacuna— no cambia de un día para otro.
 * Lo único que necesita red de verdad es el chat, porque la respuesta la escribe un modelo.
 *
 * Las dos reglas de las que sale todo lo demás:
 *
 *   1. **Las páginas van a la red PRIMERO.** Siempre. Un calendario de vacunas de hace ocho meses
 *      servido desde el teléfono es peor que no tener nada, y este proyecto corrige datos todas
 *      las semanas. La copia guardada sólo aparece cuando la red falla.
 *   2. **La API no se guarda jamás.** Una respuesta del chat es para una pregunta, un niño y un
 *      momento; volver a enseñarla por estar en la caché sería contestar a otra cosa.
 *
 * Interruptor de emergencia: esta dirección revalida en cada carga (Caddy le pone `no-cache` a
 * todo lo que no lleve hash), así que si un día hay que apagarlo basta con desplegar este fichero
 * con `self.registration.unregister()` dentro y las cachés borradas. No hace falta tocar nada más.
 */

//: Se sube la versión para invalidar todo lo guardado. Al activarse, las demás se borran.
const VERSION = 'pedibot-v2';

//: Lo que se guarda al instalar, sin esperar a que nadie lo visite. No es la web entera: es lo
//: que un padre sin cobertura necesita abrir **aunque nunca haya entrado ahí**.
//:
//: 19-sep-2026 (F1b del plan de APP.md). La primera versión guardaba sólo las páginas visitadas,
//: y eso deja fuera justo el caso que importa: alguien instala el sitio un martes con wifi y el
//: viernes, sin saldo y a las tres de la mañana, busca el número de su país por primera vez.
const CIMIENTOS = [
  '/offline',
  '/emergency',
  '/vaccines',
  '/growth',
  // Y los datos, que son de lo que está hecho todo lo de arriba: 88 países con su número, los
  // 61 calendarios, las 69 tablas de crecimiento, las dosis y los signos de alarma. Pesan unos
  // 700 kB juntos y son lo único del sitio que sigue valiendo sin red.
  '/offline-data/emergency.json',
  '/offline-data/vaccines.json',
  '/offline-data/growth_charts.json',
  '/offline-data/checklist.json',
  '/offline-data/drugs.json',
  '/offline-data/dose_table.json',
];

//: Lo que lleva un hash en el nombre o no cambia nunca: se sirve de la caché sin preguntar.
const INMUTABLE = /^\/(?:_astro|fonts)\//;

const esNavegacion = (req) =>
  req.mode === 'navigate' || (req.method === 'GET' && (req.headers.get('accept') || '').includes('text/html'));

self.addEventListener('install', (e) => {
  e.waitUntil(
    (async () => {
      const cache = await caches.open(VERSION);
      // uno a uno y sin romperse: `addAll` falla entero si una sola dirección falla, y perder
      // el service worker por eso dejaría al lector igual que antes
      await Promise.allSettled(CIMIENTOS.map((u) => cache.add(new Request(u, { cache: 'reload' }))));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    (async () => {
      const viejas = (await caches.keys()).filter((k) => k !== VERSION);
      await Promise.all(viejas.map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // La API, fuera: ni el chat, ni la foto, ni las dosis, ni el panel. Y el enlace compartido
  // tampoco, que es una respuesta concreta a una pregunta concreta.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/a/') || url.pathname.startsWith('/admin')) {
    return;
  }

  if (esNavegacion(req)) {
    e.respondWith(
      (async () => {
        try {
          const fresca = await fetch(req);
          if (fresca && fresca.status === 200 && fresca.type === 'basic') {
            const cache = await caches.open(VERSION);
            cache.put(req, fresca.clone());
          }
          return fresca;
        } catch (err) {
          // sin red: primero esta misma página si ya se vio, luego la de «sin conexión»
          const guardada = await caches.match(req);
          if (guardada) return guardada;
          const aviso = await caches.match('/offline');
          if (aviso) return aviso;
          throw err;
        }
      })()
    );
    return;
  }

  // Lo demás —estilos, tipografías, iconos, los JSON de datos— de la caché y al mismo tiempo
  // pidiéndolo a la red para la próxima vez. Lo que lleva hash en el nombre no cambia nunca;
  // lo que no lo lleva, con un día de retraso no hace daño a nadie.
  e.respondWith(
    (async () => {
      const cache = await caches.open(VERSION);
      const guardada = await cache.match(req);
      // Lo que lleva el hash en el nombre no cambia NUNCA: si está guardado, se acabó. Pedirlo
      // igualmente «por si acaso» sería gastarle datos al lector para recibir byte a byte lo
      // mismo que ya tiene, y en 2G eso se nota.
      if (guardada && INMUTABLE.test(url.pathname)) return guardada;
      const red = fetch(req)
        .then((r) => {
          if (r && r.status === 200 && r.type === 'basic') cache.put(req, r.clone());
          return r;
        })
        .catch(() => null);
      if (guardada) {
        e.waitUntil(red);
        return guardada;
      }
      const fresca = await red;
      if (fresca) return fresca;
      return new Response('', { status: 504, statusText: 'sin conexión' });
    })()
  );
});

// La página puede pedir que la versión nueva entre ya, sin esperar a que se cierren las pestañas.
self.addEventListener('message', (e) => {
  if (e.data === 'ya') self.skipWaiting();
});
