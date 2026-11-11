# bsc-mint-guard

Safety-check a BSC ERC-721 free mint before you mint. Read-only on-chain reads. No keys, no signing, no spending.

## What it does

`mint_check` reads a contract on BSC and reports name, symbol, total supply, mint price, mint open state, max per wallet, and owner. It returns a verdict: `SAFE_TO_PREVIEW`, `DO_NOT_MINT`, or `NEEDS_MANUAL_CHECK`. A `SAFE_TO_PREVIEW` verdict means a preview is warranted. It is not a promise that a mint is safe to execute.

`mint_quote` quotes the total price for a quantity, max 20. Gas is an estimate only, never a promise.

`wallet_mint_status` checks whether a wallet already holds or minted from a contract.

## Install

Copy this folder to `~/.hermes/plugins/bsc-mint-guard`, then run:

```
hermes plugins enable bsc-mint-guard
```

No API key. No env vars. No dependencies beyond the Python standard library.

## Tools

| Tool | Args | Returns |
| --- | --- | --- |
| mint_check | contract_address | Verdict, price, open state, owner, risk flags |
| mint_quote | contract_address, quantity (default 1, max 20) | Unit and total price in wei and BNB |
| wallet_mint_status | contract_address, wallet_address | Balance, minted count, already_minted |

## Example calls

```
mint_check({"contract_address": "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2"})
mint_quote({"contract_address": "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2", "quantity": 1})
wallet_mint_status({"contract_address": "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2", "wallet_address": "0x0000000000000000000000000000000000000000"})
```

## Safety rules

- Verify the contract first.
- Price must be 0 for a free mint.
- Preview must be clean: value 0, gas only, no allowance or authority change.
- Verify the receipt and token id before reporting a mint.
- Swaps go through one router tx only. Never transfer then swap later.

## Disclosures

- The plugin calls public BSC RPC endpoints: bsc.meowrpc.com, bsc-mainnet.public.blastapi.io, rpc-bsc.48.club, and bsc-dataseed.bnbchain.org as fallback. Each call sends only the contract address and calldata for a read.
- It reads no files outside its own folder, stores no credentials, and moves no funds.
- It makes no network calls during registration. Network calls happen only when a tool runs.
- The `post_tool_call` hook logs a count only. It logs no arguments, results, or addresses.

## Tests

```
python3 -m py_compile __init__.py schemas.py tools.py
python3 -m unittest discover -s tests -v
```

## License

MIT.
