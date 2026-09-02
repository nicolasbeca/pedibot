/**
 * Donation address, in one place.
 *
 * Empty string = the block does not render anywhere. That is deliberate: a donation section with
 * a placeholder address is worse than no donation section, because somebody eventually sends
 * money to nowhere.
 *
 * Rules this address must satisfy, from the reasoning in STATE.md:
 *  - a NEW account, created only for this, never used for anything else. A chain address is
 *    pseudonymous, not anonymous: everything it receives is public forever, and the moment it
 *    shares a transaction with another wallet of the operator, the two are linked for good.
 *  - not the PediBot ACP agent wallet and not the PDBT deployer: both are already tied to a
 *    Virtuals account and to an identity.
 */
export const DONATION_ADDRESS = '';

/** Base (chain id 8453): the network PDBT already lives on, and cents in fees instead of euros. */
export const DONATION_CHAIN_ID = 8453;

/** Opens MetaMask (and most mobile wallets) straight on the transfer screen. EIP-681. */
export const donationLink = (address: string, chainId = DONATION_CHAIN_ID) =>
  `ethereum:${address}@${chainId}`;
