# Validation

Checked: 2026-11-11 08:02 WIB (01:02 UTC). Read-only checks only. No mint, no sign, no spend.

## Unit tests

Command: `python3 -m py_compile __init__.py schemas.py tools.py tests/test_tools.py` then `python3 -m unittest discover -s tests -v`

Result: compile OK. 22 tests ran, 22 passed, 0 failed.

Coverage: address validation, calldata padding, price parsing, verdict logic for free, paid, closed, unknown price, and not a contract, handler returns JSON string on error, RPC fallback order, all endpoints down, quantity cap and zero, quote math, wallet minted and fresh, register wiring for 3 tools, hook, and skill.

## Live read-only check

Contract: 0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2 (JPEG.ai, BSC).

`mint_check` output:

```json
{"contract": "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2", "is_contract": true, "name": "JPEG.ai", "symbol": "JAI", "total_supply": 5000, "mint_price_wei": null, "mint_price_bnb": null, "price_source": null, "mint_open": true, "mint_open_source": "mintOpen", "max_per_wallet": null, "max_per_wallet_source": null, "owner": "0x2ef3b19cd3166bb86f57676b256f2bcee6a93431", "contract_balance_wei": 0, "checks_run": 7, "ok": true, "is_free": false, "risk_flags": ["price_unknown"], "verdict": "NEEDS_MANUAL_CHECK", "note": "SAFE_TO_PREVIEW means a preview is warranted, not that a mint is safe to execute. Always preview first and check the preview."}
```

`wallet_mint_status` for wallet 0x1111111111111111111111111111111111111111:

```json
{"ok": true, "contract": "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2", "wallet": "0x1111111111111111111111111111111111111111", "balance": 0, "minted_count": null, "has_minted": null, "already_minted": false}
```

`mint_quote` for the same contract returned `{"ok": false, "error": "mint price unknown, cannot quote"}`. This is correct behavior when the price function is not found.

Invalid address input returned `{"ok": false, "error": "contract_address must be a 0x address of 42 chars"}`.

## Live probe, second round (2026-11-11 08:06 WIB)

- Hopkin Genesis 0x2728c134D79D34A977d6D35D8A3014AbB5C97ed4: name HOPKIN GENESIS, symbol HOPKIN, supply 4444, price 1000000000000000 wei (0.001 BNB), mint open false, verdict DO_NOT_MINT, flags mint_closed, not_free. Price probe works when the contract exposes a standard price view.
- Star Agent 0xAB2649ecc5Bf7c1e8E40758387C8CB278c04FB77: name Star Agent, symbol STAR, supply 232, price unknown, mint open false, verdict DO_NOT_MINT, flags mint_closed, price_unknown.
- JPEG.ai rechecked: same as above, NEEDS_MANUAL_CHECK.

## Hermes CLI

`hermes` is not installed on this machine. `hermes plugins doctor . --ci` and `hermes plugins validate . --install-deps` were not run. The CLI was not installed blindly. Run both commands before submitting to the catalog.

## Gaps

- Price probe list covers common view functions only (mintPrice, price, cost, mintCost, publicPrice, salePrice, getPrice). JPEG.ai uses a different price function, so its price came back unknown and the verdict was NEEDS_MANUAL_CHECK. This is honest, not a pass.
- `wallet_mint_status` for the zero address returned balance null. balanceOf reverts for the zero address in many ERC721 contracts. A normal address returned balance 0 as expected.
- No GitHub repo, PR, X post, or Typeform submission was created. Build only.
