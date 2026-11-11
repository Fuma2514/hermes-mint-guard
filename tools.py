"""Tool handlers for bsc-mint-guard.

Read-only safety checks for BSC ERC-721 free mints. Stdlib only.
No keys, no signing, no spending, no private data.
Every handler returns a JSON string and never raises.
"""

import json
import urllib.error
import urllib.request

RPC_ENDPOINTS = [
    "https://bsc.meowrpc.com",
    "https://bsc-mainnet.public.blastapi.io",
    "https://rpc-bsc.48.club",
    "https://bsc-dataseed.bnbchain.org",
]

RPC_TIMEOUT = 10
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

SEL_NAME = "0x06fdde03"
SEL_SYMBOL = "0x95d89b41"
SEL_TOTAL_SUPPLY = "0x18160ddd"
SEL_BALANCE_OF = "0x70a08231"
SEL_OWNER = "0x8da5cb5b"

# Price view functions, tried in order. Selectors are keccak first 4 bytes.
PRICE_FNS = [
    ("mintPrice", "0x6817c76c"),
    ("price", "0xa035b1fe"),
    ("cost", "0x13faede6"),
    ("mintCost", "0xbdb4b848"),
    ("publicPrice", "0xa945bf80"),
    ("salePrice", "0xf51f96dd"),
    ("getPrice", "0x98d5fdca"),
]

# Mint open view functions, tried in order.
OPEN_FNS = [
    ("mintOpen", "0x24bbd049", False),
    ("saleActive", "0x68428a1b", False),
    ("publicSaleActive", "0xbc8893b4", False),
    ("isMintOpen", "0x19908016", False),
    ("mintingEnabled", "0x9fd6db12", False),
    ("paused", "0x5c975abb", True),
]

MAX_FNS = [
    ("maxPerWallet", "0x453c2310"),
    ("maxMintPerWallet", "0xb228d925"),
    ("maxMintAmount", "0x239c70ae"),
]

MINTED_FNS = [
    ("numberMinted", "0xdc33e681", "uint"),
    ("minted", "0x1e7269c5", "uint"),
    ("hasMinted", "0x38e21cce", "bool"),
]


def is_address(value):
    """Return True for a 0x address of 42 chars with hex digits."""
    if not isinstance(value, str):
        return False
    if len(value) != 42 or not value.startswith("0x"):
        return False
    try:
        int(value[2:], 16)
    except ValueError:
        return False
    return True


def pad_address(address):
    """Encode an address as a 32 byte ABI word. Asserts exact length."""
    hexpart = address[2:].lower()
    data = "0" * (64 - len(hexpart)) + hexpart
    assert len(data) == 64
    return data


def encode_address_call(selector, address):
    """Build calldata for fn(address). Asserts exact length."""
    data = selector + pad_address(address)
    assert len(data) == 10 + 64
    return data


def _decode_uint(raw):
    if not raw or raw in ("0x", "0X"):
        return None
    try:
        return int(raw, 16)
    except ValueError:
        return None


def _decode_bool(raw):
    value = _decode_uint(raw)
    if value is None:
        return None
    return value != 0


def _decode_address(raw):
    if not raw or len(raw) < 42:
        return None
    return "0x" + raw[-40:]


def _decode_string(raw):
    if not raw or raw in ("0x", "0X"):
        return None
    body = raw[2:] if raw.startswith("0x") else raw
    try:
        raw_bytes = bytes.fromhex(body)
    except ValueError:
        return None
    if len(raw_bytes) >= 64:
        try:
            length = int.from_bytes(raw_bytes[32:64], "big")
            if 0 < length <= len(raw_bytes) - 64:
                text = raw_bytes[64:64 + length].decode("utf-8", "replace")
                return text.strip("\x00").strip() or None
        except Exception:
            pass
    try:
        text = raw_bytes.decode("utf-8", "replace")
    except Exception:
        return None
    return text.strip("\x00").strip() or None


def _rpc_call(endpoint, method, params):
    """One JSON-RPC POST. Returns the result field, or None on failure."""
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=RPC_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(body, dict) or "error" in body:
        return None
    return body.get("result")


def _view_first(contract, data):
    """Try eth_call on each RPC endpoint in order. Return first good result."""
    params = [{"to": contract, "data": data}, "latest"]
    for endpoint in RPC_ENDPOINTS:
        result = _rpc_call(endpoint, "eth_call", params)
        if result is not None and result not in ("0x", "0X"):
            return result
    return None


def _read_contract(contract):
    """Run the on-chain reads. Returns a dict with the raw findings."""
    found = {
        "contract": contract,
        "is_contract": None,
        "name": None,
        "symbol": None,
        "total_supply": None,
        "mint_price_wei": None,
        "mint_price_bnb": None,
        "price_source": None,
        "mint_open": None,
        "mint_open_source": None,
        "max_per_wallet": None,
        "max_per_wallet_source": None,
        "owner": None,
        "contract_balance_wei": None,
        "checks_run": 0,
    }

    code = None
    for endpoint in RPC_ENDPOINTS:
        code = _rpc_call(endpoint, "eth_getCode", [contract, "latest"])
        if code is not None:
            break
    if code is not None:
        found["checks_run"] += 1
        found["is_contract"] = bool(code and code not in ("0x", "0X"))

    balance = None
    for endpoint in RPC_ENDPOINTS:
        balance = _rpc_call(endpoint, "eth_getBalance", [contract, "latest"])
        if balance is not None:
            break
    if balance is not None:
        found["checks_run"] += 1
        found["contract_balance_wei"] = _decode_uint(balance)

    name_raw = _view_first(contract, SEL_NAME)
    if name_raw is not None:
        found["checks_run"] += 1
        found["name"] = _decode_string(name_raw)

    symbol_raw = _view_first(contract, SEL_SYMBOL)
    if symbol_raw is not None:
        found["checks_run"] += 1
        found["symbol"] = _decode_string(symbol_raw)

    supply_raw = _view_first(contract, SEL_TOTAL_SUPPLY)
    if supply_raw is not None:
        found["checks_run"] += 1
        found["total_supply"] = _decode_uint(supply_raw)

    for label, selector in PRICE_FNS:
        raw = _view_first(contract, selector)
        if raw is not None:
            value = _decode_uint(raw)
            if value is not None:
                found["checks_run"] += 1
                found["mint_price_wei"] = value
                found["mint_price_bnb"] = value / 10**18
                found["price_source"] = label
                break

    for label, selector, inverted in OPEN_FNS:
        raw = _view_first(contract, selector)
        if raw is not None:
            value = _decode_bool(raw)
            if value is not None:
                found["checks_run"] += 1
                found["mint_open"] = (not value) if inverted else value
                found["mint_open_source"] = label
                break

    for label, selector in MAX_FNS:
        raw = _view_first(contract, selector)
        if raw is not None:
            value = _decode_uint(raw)
            if value is not None:
                found["checks_run"] += 1
                found["max_per_wallet"] = value
                found["max_per_wallet_source"] = label
                break

    owner_raw = _view_first(contract, SEL_OWNER)
    if owner_raw is not None:
        found["checks_run"] += 1
        found["owner"] = _decode_address(owner_raw)

    return found


def _verdict(found):
    """Decide the verdict and risk flags from the raw findings."""
    flags = []
    if found["is_contract"] is False:
        flags.append("not_a_contract")
    if found["is_contract"] is None:
        flags.append("contract_check_failed")
    if found["mint_open"] is False:
        flags.append("mint_closed")
    if found["mint_open"] is None:
        flags.append("mint_open_unknown")
    if found["mint_price_wei"] is None:
        flags.append("price_unknown")
    elif found["mint_price_wei"] != 0:
        flags.append("not_free")
    if found["owner"] is None:
        flags.append("owner_unknown")
    elif found["owner"].lower() == ZERO_ADDRESS:
        flags.append("owner_is_zero_address")

    if "not_a_contract" in flags:
        verdict = "DO_NOT_MINT"
    elif "mint_closed" in flags:
        verdict = "DO_NOT_MINT"
    elif "not_free" in flags:
        verdict = "DO_NOT_MINT"
    elif "price_unknown" in flags or "mint_open_unknown" in flags:
        verdict = "NEEDS_MANUAL_CHECK"
    else:
        verdict = "SAFE_TO_PREVIEW"
    return verdict, flags


def _error(message):
    return json.dumps({"ok": False, "error": message})


def mint_check(args: dict, **kwargs) -> str:
    """Safety-check a BSC ERC-721 contract before a free mint preview."""
    try:
        contract = (args or {}).get("contract_address", "")
        if not isinstance(contract, str):
            return _error("contract_address must be a string")
        contract = contract.strip()
        if not is_address(contract):
            return _error("contract_address must be a 0x address of 42 chars")
        found = _read_contract(contract)
        verdict, flags = _verdict(found)
        result = dict(found)
        result["ok"] = True
        result["is_free"] = found["mint_price_wei"] == 0
        result["risk_flags"] = flags
        result["verdict"] = verdict
        result["note"] = (
            "SAFE_TO_PREVIEW means a preview is warranted, not that a mint "
            "is safe to execute. Always preview first and check the preview."
        )
        return json.dumps(result)
    except Exception as exc:
        return _error("mint_check failed: %s" % exc)


def mint_quote(args: dict, **kwargs) -> str:
    """Quote the mint price for a quantity. Gas is an estimate only."""
    try:
        params = args or {}
        contract = params.get("contract_address", "")
        if not isinstance(contract, str):
            return _error("contract_address must be a string")
        contract = contract.strip()
        if not is_address(contract):
            return _error("contract_address must be a 0x address of 42 chars")
        quantity = params.get("quantity", 1)
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            try:
                quantity = int(quantity)
            except Exception:
                return _error("quantity must be an integer")
        if quantity < 1:
            return _error("quantity must be at least 1")
        if quantity > 20:
            return _error("quantity must be at most 20")
        found = _read_contract(contract)
        if found["mint_price_wei"] is None:
            return json.dumps(
                {
                    "ok": False,
                    "contract": contract,
                    "quantity": quantity,
                    "error": "mint price unknown, cannot quote",
                    "price_source": None,
                }
            )
        total_wei = found["mint_price_wei"] * quantity
        return json.dumps(
            {
                "ok": True,
                "contract": contract,
                "quantity": quantity,
                "unit_price_wei": found["mint_price_wei"],
                "unit_price_bnb": found["mint_price_bnb"],
                "total_price_wei": total_wei,
                "total_price_bnb": total_wei / 10**18,
                "price_source": found["price_source"],
                "is_free": found["mint_price_wei"] == 0,
                "gas_note": (
                    "Gas cost is an estimate only, not a promise. "
                    "Check the actual gas in the preview before minting."
                ),
            }
        )
    except Exception as exc:
        return _error("mint_quote failed: %s" % exc)


def wallet_mint_status(args: dict, **kwargs) -> str:
    """Check a wallet balance and minted state for a contract."""
    try:
        params = args or {}
        contract = params.get("contract_address", "")
        wallet = params.get("wallet_address", "")
        if not isinstance(contract, str) or not isinstance(wallet, str):
            return _error("contract_address and wallet_address must be strings")
        contract = contract.strip()
        wallet = wallet.strip()
        if not is_address(contract):
            return _error("contract_address must be a 0x address of 42 chars")
        if not is_address(wallet):
            return _error("wallet_address must be a 0x address of 42 chars")
        balance = None
        raw = _view_first(contract, encode_address_call(SEL_BALANCE_OF, wallet))
        if raw is not None:
            balance = _decode_uint(raw)
        minted_count = None
        has_minted = None
        for label, selector, kind in MINTED_FNS:
            raw = _view_first(contract, encode_address_call(selector, wallet))
            if raw is None:
                continue
            if kind == "uint":
                value = _decode_uint(raw)
                if value is not None:
                    minted_count = value
                    break
            else:
                value = _decode_bool(raw)
                if value is not None:
                    has_minted = value
                    break
        already = False
        if balance is not None and balance > 0:
            already = True
        if minted_count is not None and minted_count > 0:
            already = True
        if has_minted is True:
            already = True
        return json.dumps(
            {
                "ok": True,
                "contract": contract,
                "wallet": wallet,
                "balance": balance,
                "minted_count": minted_count,
                "has_minted": has_minted,
                "already_minted": already,
            }
        )
    except Exception as exc:
        return _error("wallet_mint_status failed: %s" % exc)
