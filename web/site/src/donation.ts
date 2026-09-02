/**
 * Donation address, in one place.
 *
 * Empty string = the block does not render anywhere. That is deliberate: a donation section with
 * a placeholder address is worse than no donation section, because somebody eventually sends
 * money to nowhere.
 *
 * The address in use (operator's decision, 1-sep-2026) is a wallet that was ALREADY public
 * through Virtuals, chosen precisely because publishing it exposes nothing new. The trade-off
 * was accepted knowingly: a chain address is pseudonymous, not anonymous, so anyone reading
 * this page can also read that wallet's balance and its whole history — 1,214 transactions at
 * the time of writing. What it does avoid is a bank account and a real name, which was the
 * point. It is an EOA delegated under EIP-7702 (a smart account), which receives normally.
 *
 * What must never go here: the PDBT contract (anything sent there is burnt) and the PediBot
 * ACP agent wallet (Privy custody, tied to the Virtuals account). Both are locked by a test.
 */
export const DONATION_ADDRESS = '0x1EC1445342713b1dF48E6768456800B1260aeaBb';

/**
 * The networks we list. It is the same EVM address on every one of them, so this list is a
 * courtesy — telling a donor which chains are worth using — and not a limitation of the wallet.
 * Every one was checked on 1-sep-2026 with eth_getCode: a plain externally-owned account on all
 * six, which is what makes receiving safe.
 *
 * Base goes first because it is the cheapest and the network PDBT already lives on; the QR and
 * the wallet button point there.
 */
export const DONATION_CHAINS = [
  { id: 8453, name: 'Base', coin: 'ETH', recommended: true },
  { id: 1, name: 'Ethereum', coin: 'ETH', recommended: false },
  { id: 42161, name: 'Arbitrum', coin: 'ETH', recommended: false },
  { id: 10, name: 'Optimism', coin: 'ETH', recommended: false },
  { id: 137, name: 'Polygon', coin: 'POL', recommended: false },
  { id: 56, name: 'BNB Chain', coin: 'BNB', recommended: false },
] as const;

export const DONATION_CHAIN_ID = 8453;

/** Opens MetaMask (and most mobile wallets) straight on the transfer screen. EIP-681. */
export const donationLink = (address: string, chainId = DONATION_CHAIN_ID) =>
  `ethereum:${address}@${chainId}`;
