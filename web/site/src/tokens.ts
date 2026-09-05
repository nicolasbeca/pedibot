/**
 * Where PDBT lives (3-sep-2026; trimmed to Base on 5-sep by the operator).
 *
 * It went out on three chains and the site advertised all three. It now names only Base:
 * the Solana and HyperEVM deployments still exist on their chains, but three addresses on a
 * page is three chances for a reader to send money to the wrong one, and the token is not
 * what this site is for.
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
];

/** The ones that actually exist on-chain. */
export const liveTokens = (): TokenDeployment[] => TOKENS.filter((t) => t.address !== null);

/** Announced, not deployed. */
export const pendingTokens = (): TokenDeployment[] => TOKENS.filter((t) => t.address === null);

/** Shortened for display: 0x196A…15E1. */
export function shortAddress(address: string): string {
  return address.length > 14 ? `${address.slice(0, 6)}…${address.slice(-4)}` : address;
}
