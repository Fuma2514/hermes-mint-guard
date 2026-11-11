"""Tool schemas for bsc-mint-guard. These are what the LLM reads."""

MINT_CHECK = {
    "name": "mint_check",
    "description": (
        "Safety-check a BSC ERC-721 contract before a free mint. "
        "Reads name, symbol, total supply, mint price, mint open state, "
        "max per wallet, and owner from public BSC RPC endpoints. "
        "Use this before any free mint. It never mints, signs, or spends. "
        "A SAFE_TO_PREVIEW verdict means a preview is warranted, not that "
        "a mint is safe to execute."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "contract_address": {
                "type": "string",
                "description": "BSC contract address, 0x followed by 40 hex chars.",
            },
        },
        "required": ["contract_address"],
    },
}

MINT_QUOTE = {
    "name": "mint_quote",
    "description": (
        "Quote the total mint price for a quantity of NFTs from a BSC "
        "ERC-721 contract. Returns unit price and total price in wei and "
        "BNB. Gas is an estimate only, never a promise. Use mint_check "
        "first when you need the full safety verdict."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "contract_address": {
                "type": "string",
                "description": "BSC contract address, 0x followed by 40 hex chars.",
            },
            "quantity": {
                "type": "integer",
                "description": "How many to mint. Default 1, maximum 20.",
                "default": 1,
            },
        },
        "required": ["contract_address"],
    },
}

WALLET_MINT_STATUS = {
    "name": "wallet_mint_status",
    "description": (
        "Check whether a wallet already holds or minted from a BSC "
        "ERC-721 contract. Reads balanceOf and, when available, the "
        "minted count for the wallet. Read-only. Use it to avoid a "
        "second mint when the contract allows one per wallet."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "contract_address": {
                "type": "string",
                "description": "BSC contract address, 0x followed by 40 hex chars.",
            },
            "wallet_address": {
                "type": "string",
                "description": "Wallet address to check, 0x followed by 40 hex chars.",
            },
        },
        "required": ["contract_address", "wallet_address"],
    },
}
