// Genera twa-manifest.json desde el manifiesto vivo de pedibot.xyz (appgoogle.md §4).
// Se rehace con: node make-manifest.mjs   — y luego `bubblewrap update` + `bubblewrap build`.
import { createRequire } from 'module';
import { readFileSync, writeFileSync } from 'fs';
import { execSync } from 'child_process';

const require = createRequire(import.meta.url);
const raiz = execSync('npm root -g').toString().trim();
const { TwaManifest } = require(raiz + '/@bubblewrap/cli/node_modules/@bubblewrap/core');

const web = 'https://pedibot.xyz/manifest.webmanifest';
const res = await fetch(web);
const m = TwaManifest.fromWebManifestJson(new URL(web), await res.json());

m.packageId = 'xyz.pedibot.app';
m.name = 'PediBot';
m.launcherName = 'PediBot';
// la marca del modo app: la web esconde lo que Play no admite (appgoogle.md §3)
m.startUrl = '/?source=android';
for (const s of m.shortcuts) s.url = s.url + '?source=android';
m.iconUrl = 'https://pedibot.xyz/logo.png';
m.maskableIconUrl = 'https://pedibot.xyz/logo-maskable.png';
m.enableNotifications = false;
m.enableLocationDelegation = false;
m.isChromeOSOnly = false;
m.appVersionCode = 1;
m.appVersionName = '1.0.0';
// la clave vive FUERA del repositorio (appgoogle.md §4.2)
m.signingKey = { path: 'D:/Nicolas/android-keys/pedibot-upload.keystore', alias: 'pedibot-upload' };
m.fallbackType = 'customtabs';
m.generatorApp = 'bubblewrap-cli';
await m.saveToFile('./twa-manifest.json');

// los colores se escriben sobre el JSON: la biblioteca los quiere como objetos Color
const j = JSON.parse(readFileSync('./twa-manifest.json', 'utf8'));
j.navigationColor = '#FFFDF9';
j.navigationDividerColor = '#EDE6D8';
writeFileSync('./twa-manifest.json', JSON.stringify(j, null, 2) + '\n');
console.log('twa-manifest.json escrito');
