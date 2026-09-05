/**
 * Donation addresses, one entry per wallet.
 *
 * Empty address = that wallet does not render. That is deliberate: a donation block with a
 * placeholder address is worse than no donation block, because somebody eventually sends money
 * to nowhere.
 *
 * It started (operator's decision, 1-sep-2026) as a single EVM wallet that was ALREADY public
 * through Virtuals, chosen precisely because publishing it exposed nothing new. The trade-off was
 * accepted knowingly: a chain address is pseudonymous, not anonymous, so anyone reading this page
 * can also read that wallet's balance and its whole history — 1,214 transactions at the time of
 * writing. What it avoids is a bank account and a real name, which was the point. It is an EOA
 * delegated under EIP-7702 (a smart account), which receives normally.
 *
 * On 3-sep-2026 the token went to three networks and two more wallets arrived with it. Solana is
 * the reason this file stopped being one address: an EVM address cannot receive on Solana at all,
 * so anything sent there was lost, and a warning in the small print is not the same as having
 * somewhere correct to send it. Every address here was checked before publishing — EIP-55
 * checksum for the EVM ones, and on-chain that each is a plain wallet and not a contract.
 *
 * What must never go here: a PDBT contract (anything sent there is burnt) and the PediBot ACP
 * agent wallet (Privy custody, tied to the Virtuals account). Both are locked by a test.
 */

export interface DonationChain {
  id: number;
  name: string;
  coin: string;
  recommended: boolean;
}

export interface DonationWallet {
  key: string;
  /** Only EVM now. The Solana card was retired on 5-sep; the type stopped naming a branch
   *  that no longer exists, because dead code that claims a capability is what rots. */
  kind: 'evm';
  address: string;
  /** The networks this address can receive on. */
  chains: DonationChain[];
  /** Which chain the QR and the wallet button aim at. */
  defaultChainId?: number;
}

export const DONATION_WALLETS: DonationWallet[] = [
  {
    // The original wallet: the same address on every EVM chain listed, so that list is a
    // courtesy — telling a donor which chains are worth using — not a limit of the wallet.
    // All six checked with eth_getCode on 1-sep-2026: a plain externally-owned account, which
    // is what makes receiving safe. Base first because it is the cheapest and the network PDBT
    // already lives on.
    key: 'evm',
    kind: 'evm',
    address: '0x1EC1445342713b1dF48E6768456800B1260aeaBb',
    defaultChainId: 8453,
    chains: [
      { id: 8453, name: 'Base', coin: 'ETH', recommended: true },
      { id: 1, name: 'Ethereum', coin: 'ETH', recommended: false },
      { id: 42161, name: 'Arbitrum', coin: 'ETH', recommended: false },
      { id: 10, name: 'Optimism', coin: 'ETH', recommended: false },
      { id: 137, name: 'Polygon', coin: 'POL', recommended: false },
      { id: 56, name: 'BNB Chain', coin: 'BNB', recommended: false },
      // Added 5-sep when the separate HyperEVM wallet was retired: the same key signs here
      // too, and asking a donor to choose between two of our own addresses only creates a
      // way to get it wrong.
      { id: 999, name: 'HyperEVM', coin: 'HYPE', recommended: false },
    ],
  },
];

/** The wallets that have an address filled in. */
export const donationWallets = (): DonationWallet[] =>
  DONATION_WALLETS.filter((w) => w.address.length > 0);

/** Opens MetaMask (and most mobile wallets) straight on the transfer screen. EIP-681. */
export const donationLink = (address: string, chainId: number) => `ethereum:${address}@${chainId}`;

/** Where a wallet's QR lives. Written by scripts/make_donation_qr.py. */
export const donationQr = (key: string) => `/donation-qr-${key}.svg`;

/** What the QR encodes: a wallet-openable URI. */
export function donationUri(w: DonationWallet): string {
  return donationLink(w.address, w.defaultChainId ?? w.chains[0].id);
}

/** Ways to give that do not need a wallet.
 *
 *  Most people who would send five euros are not going to install one, and telling them to is
 *  telling them not to bother. `url: null` means not set up yet and the card is not rendered:
 *  the same rule the token list follows for an address that does not exist. A button that goes
 *  nowhere is worse than no button.
 */
export interface DonationLink {
  key: string;
  label: string;
  url: string | null;
}

export const DONATION_LINKS: DonationLink[] = [
  { key: 'coffee', label: 'Buy Me a Coffee', url: null },
  { key: 'paypal', label: 'PayPal', url: 'https://paypal.me/nicobeca' },
];

/** The ones actually set up. */
export const liveLinks = (): DonationLink[] => DONATION_LINKS.filter((l) => l.url !== null);
