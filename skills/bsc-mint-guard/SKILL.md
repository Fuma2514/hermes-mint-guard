---
name: bsc-mint-guard
description: Safe-mint checklist for BSC ERC-721 free mints. Use before any free mint.
---

# BSC Mint Guard

Use this skill before any BSC ERC-721 free mint. It is read-only. It never mints, signs, or spends.

## Checklist

1. Verify the contract. Run `mint_check` with the contract address.
2. Price must be 0. If `mint_price_wei` is not 0, stop. Do not mint.
3. Mint must be open. If `mint_open` is false, stop.
4. Read the verdict. Only `SAFE_TO_PREVIEW` warrants a preview.
5. `DO_NOT_MINT` means stop. `NEEDS_MANUAL_CHECK` means check the project site and docs by hand.
6. Check the wallet first. Run `wallet_mint_status` to see if the wallet already minted.
7. Quote before you mint. Run `mint_quote` for the quantity you want.
8. Preview clean. The preview must show value 0, gas only, and no allowance or authority change.
9. Receipt verify. Confirm the receipt and the token id before you report a mint.
10. Single-tx swaps only. Never transfer tokens to a pair and swap later. Use one router swap tx.

## Tools

- `mint_check`: full safety check for a contract address.
- `mint_quote`: total price for a quantity, max 20. Gas is an estimate only.
- `wallet_mint_status`: balance and minted state for a wallet and contract.

## Limits

- A `SAFE_TO_PREVIEW` verdict is not a promise that a mint is safe to execute.
- Price and open state come from public RPC reads. A contract can change after the check.
- This plugin holds no keys and moves no funds.
