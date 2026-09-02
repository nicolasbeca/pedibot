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

/** Base (chain id 8453): the network PDBT already lives on, and cents in fees instead of euros. */
export const DONATION_CHAIN_ID = 8453;

/** Opens MetaMask (and most mobile wallets) straight on the transfer screen. EIP-681. */
export const donationLink = (address: string, chainId = DONATION_CHAIN_ID) =>
  `ethereum:${address}@${chainId}`;
