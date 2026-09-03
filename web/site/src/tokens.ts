/**
 * Where PDBT lives, one entry per network (3-sep-2026).
 *
 * The token was the funding mechanism from the start, and it is going to three networks so that
 * someone who wants to back the project can do it from the chain they already use. The site used
 * to say "a token, on Base" in three hardcoded places — a button, a card footer and a paragraph —
 * plus one sentence per language. This is the list instead: adding a network is one entry, and
 * nothing on the page has to be hunted down.
 *
 * `address: null` means announced but not deployed yet. The page shows those as pending and
 * never links to an explorer, because a link to a contract that does not exist is worse than no
 * link at all — it is exactly the shape a scam copy would take.
 */

export interface TokenDeployment {
  /** The chain, as a person would say it. */
  network: string;
  /** The launchpad it went out on — worth naming, it is where people will look for it. */
  platform: string;
  ticker: string;
  /** null until it is actually deployed. */
  address: string | null;
  /** Block explorer for the contract, when there is one. */
  explorer?: string;
  /** Where to get it. Omitted while the token is pending. */
  buy?: string;
}

export const TOKENS: TokenDeployment[] = [
  {
    network: 'Base',
    platform: 'Virtuals',
    ticker: 'PDBT',
    address: '0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1',
    explorer: 'https://basescan.org/token/0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1',
    buy: 'https://app.uniswap.org/explore/tokens/base/0x196a67ba334dbed501e19baec47d217bb2fc15e1',
  },
  {
    // Launched 3-sep-2026. Verified against the chain before publishing, not against the UI: the
    // account is owned by the SPL Token program, is a mint of 1e9 at 6 decimals, and BOTH
    // authorities are renounced — `mintAuthority` and `freezeAuthority` are null, so no more can
    // ever be printed and no holder's balance can be frozen. Jupiter reports name "PediBot",
    // symbol PDBT, launchpad jup-studio.
    network: 'Solana',
    platform: 'Jupiter Studio',
    ticker: 'PDBT',
    address: 'EUiC7nSriqfASMbEe5ZwkD6P4j4bKH5eLoMTajr4jups',
    explorer: 'https://solscan.io/token/EUiC7nSriqfASMbEe5ZwkD6P4j4bKH5eLoMTajr4jups',
    buy: 'https://jup.ag/tokens/EUiC7nSriqfASMbEe5ZwkD6P4j4bKH5eLoMTajr4jups',
  },
  {
    // Launched 3-sep-2026, tx 0xd362e52f…b27c58d. The address was read off the creation receipt
    // and checked against the token itself (name "PediBot", symbol PDBT, 6 decimals, 1e9 supply)
    // before being published — not taken from the launchpad's UI, which took an hour to index it.
    // The link goes to the LiquidLaunch page rather than a block explorer: it is the one URL that
    // was verified to load, and it is where a reader can actually see and buy the token.
    network: 'HyperEVM',
    platform: 'LiquidLaunch',
    ticker: 'PDBT',
    address: '0x4a2caac88e85cc858a6265e773fc8db5aa40b5e5',
    explorer: 'https://liquidlaunch.app/token/0x4a2caac88e85cc858a6265e773fc8db5aa40b5e5',
    buy: 'https://liquidlaunch.app/token/0x4a2caac88e85cc858a6265e773fc8db5aa40b5e5',
  },
];

/** The ones that actually exist on-chain. */
export const liveTokens = (): TokenDeployment[] => TOKENS.filter((t) => t.address !== null);

/** Announced, not deployed. */
export const pendingTokens = (): TokenDeployment[] => TOKENS.filter((t) => t.address === null);

/** Shortened for display: 0x196A…15E1. */
export function shortAddress(address: string): string {
  return address.length > 14 ? `${address.slice(0, 6)}…${address.slice(-4)}` : address;
}
