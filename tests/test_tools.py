"""Tests for bsc-mint-guard. No live network. urllib is mocked."""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools
from tools import (
    RPC_ENDPOINTS,
    encode_address_call,
    mint_check,
    mint_quote,
    pad_address,
    wallet_mint_status,
)

CONTRACT = "0xC24BE89bd723547546ABC86e6B9fdD176C21D5e2"
WALLET = "0x1111111111111111111111111111111111111111"
OWNER = "0x2222222222222222222222222222222222222222"


def uint_word(value):
    return "0x" + value.to_bytes(32, "big").hex()


def abi_string(text):
    raw = text.encode("utf-8")
    pad = (32 - len(raw) % 32) % 32
    return (
        "0x"
        + (32).to_bytes(32, "big").hex()
        + len(raw).to_bytes(32, "big").hex()
        + raw.hex()
        + "00" * pad
    )


def address_word(address):
    return "0x" + "0" * 24 + address[2:].lower()


def make_rpc(price_wei=0, mint_open=True, is_contract=True, balance=0,
             price_known=True, open_known=True):
    """Build a fake _rpc_call. Selector map drives eth_call results."""
    mapping = {
        "0x06fdde03": abi_string("Test"),
        "0x95d89b41": abi_string("TST"),
        "0x18160ddd": uint_word(100),
        "0x8da5cb5b": address_word(OWNER),
        "0x453c2310": uint_word(1),
        "0x70a08231": uint_word(balance),
    }
    if price_known:
        mapping["0x6817c76c"] = uint_word(price_wei)
    if open_known:
        mapping["0x24bbd049"] = uint_word(1 if mint_open else 0)

    def fake(endpoint, method, params):
        if method == "eth_getCode":
            return "0x60806040" if is_contract else "0x"
        if method == "eth_getBalance":
            return "0x0"
        if method == "eth_call":
            data = params[0]["data"]
            return mapping.get(data[:10])
        return None

    return fake


class TestValidation(unittest.TestCase):
    def test_short_address_rejected(self):
        out = json.loads(mint_check({"contract_address": "0x1234"}))
        self.assertFalse(out["ok"])
        self.assertIn("error", out)

    def test_non_hex_address_rejected(self):
        bad = "0x" + "zz" * 20
        out = json.loads(mint_check({"contract_address": bad}))
        self.assertFalse(out["ok"])

    def test_missing_address_rejected(self):
        out = json.loads(mint_check({}))
        self.assertFalse(out["ok"])

    def test_handlers_return_json_string_on_error(self):
        raw = mint_check({"contract_address": "nope"})
        self.assertIsInstance(raw, str)
        self.assertIn("error", json.loads(raw))

    def test_pad_address_length(self):
        padded = pad_address(WALLET)
        self.assertEqual(len(padded), 64)
        self.assertTrue(padded.endswith(WALLET[2:].lower()))

    def test_encode_address_call_length(self):
        data = encode_address_call("0x70a08231", WALLET)
        self.assertEqual(len(data), 74)
        self.assertTrue(data.startswith("0x70a08231"))
        self.assertTrue(data.endswith(WALLET[2:].lower()))


class TestMintCheck(unittest.TestCase):
    def test_free_open_contract_is_safe_to_preview(self):
        with mock.patch.object(tools, "_rpc_call", side_effect=make_rpc()):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "SAFE_TO_PREVIEW")
        self.assertTrue(out["is_free"])
        self.assertEqual(out["mint_price_wei"], 0)
        self.assertEqual(out["mint_price_bnb"], 0)
        self.assertTrue(out["mint_open"])
        self.assertEqual(out["name"], "Test")
        self.assertEqual(out["symbol"], "TST")
        self.assertEqual(out["total_supply"], 100)
        self.assertEqual(out["max_per_wallet"], 1)
        self.assertEqual(out["owner"].lower(), OWNER.lower())
        self.assertGreaterEqual(out["checks_run"], 7)

    def test_not_a_contract(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(is_contract=False)):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertEqual(out["verdict"], "DO_NOT_MINT")
        self.assertIn("not_a_contract", out["risk_flags"])
        self.assertFalse(out["is_contract"])

    def test_paid_price_is_do_not_mint(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(price_wei=10**15)):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertEqual(out["verdict"], "DO_NOT_MINT")
        self.assertIn("not_free", out["risk_flags"])
        self.assertFalse(out["is_free"])
        self.assertAlmostEqual(out["mint_price_bnb"], 0.001)

    def test_closed_mint_is_do_not_mint(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(mint_open=False)):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertEqual(out["verdict"], "DO_NOT_MINT")
        self.assertIn("mint_closed", out["risk_flags"])

    def test_unknown_price_needs_manual_check(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(price_known=False)):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertEqual(out["verdict"], "NEEDS_MANUAL_CHECK")
        self.assertIn("price_unknown", out["risk_flags"])
        self.assertIsNone(out["mint_price_wei"])

    def test_rpc_fallback_uses_next_endpoint(self):
        base = make_rpc()
        seen = []

        def flaky(endpoint, method, params):
            seen.append(endpoint)
            if endpoint == RPC_ENDPOINTS[0]:
                return None
            return base(endpoint, method, params)

        with mock.patch.object(tools, "_rpc_call", side_effect=flaky):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "SAFE_TO_PREVIEW")
        self.assertIn(RPC_ENDPOINTS[1], seen)

    def test_all_endpoints_down_returns_manual_check(self):
        with mock.patch.object(tools, "_rpc_call", return_value=None):
            out = json.loads(mint_check({"contract_address": CONTRACT}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "NEEDS_MANUAL_CHECK")
        self.assertIn("price_unknown", out["risk_flags"])


class TestMintQuote(unittest.TestCase):
    def test_quote_multiplies_price(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(price_wei=10**15)):
            out = json.loads(mint_quote(
                {"contract_address": CONTRACT, "quantity": 3}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["total_price_wei"], 3 * 10**15)
        self.assertAlmostEqual(out["total_price_bnb"], 0.003)
        self.assertIn("estimate", out["gas_note"])

    def test_quote_defaults_to_one(self):
        with mock.patch.object(tools, "_rpc_call", side_effect=make_rpc()):
            out = json.loads(mint_quote({"contract_address": CONTRACT}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["quantity"], 1)
        self.assertEqual(out["total_price_wei"], 0)

    def test_quote_quantity_cap(self):
        out = json.loads(mint_quote(
            {"contract_address": CONTRACT, "quantity": 21}))
        self.assertFalse(out["ok"])

    def test_quote_quantity_zero_rejected(self):
        out = json.loads(mint_quote(
            {"contract_address": CONTRACT, "quantity": 0}))
        self.assertFalse(out["ok"])

    def test_quote_unknown_price_errors(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(price_known=False)):
            out = json.loads(mint_quote({"contract_address": CONTRACT}))
        self.assertFalse(out["ok"])
        self.assertIn("unknown", out["error"])


class TestWalletStatus(unittest.TestCase):
    def test_invalid_wallet_rejected(self):
        out = json.loads(wallet_mint_status(
            {"contract_address": CONTRACT, "wallet_address": "bad"}))
        self.assertFalse(out["ok"])

    def test_already_minted_when_balance_positive(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(balance=1)):
            out = json.loads(wallet_mint_status(
                {"contract_address": CONTRACT, "wallet_address": WALLET}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["balance"], 1)
        self.assertTrue(out["already_minted"])

    def test_fresh_wallet_not_minted(self):
        with mock.patch.object(tools, "_rpc_call",
                               side_effect=make_rpc(balance=0)):
            out = json.loads(wallet_mint_status(
                {"contract_address": CONTRACT, "wallet_address": WALLET}))
        self.assertTrue(out["ok"])
        self.assertEqual(out["balance"], 0)
        self.assertFalse(out["already_minted"])


class TestRegister(unittest.TestCase):
    def test_register_wires_tools_hook_and_skill(self):
        import importlib.util
        plugin_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        spec = importlib.util.spec_from_file_location(
            "hermes_mint_guard", os.path.join(plugin_dir, "__init__.py"),
            submodule_search_locations=[plugin_dir])
        module = importlib.util.module_from_spec(spec)
        sys.modules["hermes_mint_guard"] = module
        spec.loader.exec_module(module)

        class FakeCtx:
            def __init__(self):
                self.tools = {}
                self.hooks = []
                self.skills = []

            def register_tool(self, name, toolset, schema, handler):
                self.tools[name] = (toolset, schema, handler)

            def register_hook(self, name, handler):
                self.hooks.append(name)

            def register_skill(self, name, path):
                self.skills.append(name)

        ctx = FakeCtx()
        module.register(ctx)
        self.assertEqual(
            sorted(ctx.tools),
            ["mint_check", "mint_quote", "wallet_mint_status"])
        for name in ctx.tools:
            toolset, schema, handler = ctx.tools[name]
            self.assertEqual(toolset, "bsc-mint-guard")
            self.assertEqual(schema["name"], name)
            self.assertTrue(callable(handler))
        self.assertEqual(ctx.hooks, ["post_tool_call"])
        self.assertIn("bsc-mint-guard", ctx.skills)

        before = module.get_call_count()
        module._on_post_tool_call("mint_check", {}, "{}", "task-1")
        self.assertEqual(module.get_call_count(), before + 1)


if __name__ == "__main__":
    unittest.main()
