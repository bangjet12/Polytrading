#!/usr/bin/env python3
"""
Comprehensive backend API test suite for Polymarket BTC Scalper.
Tests all PHASE 2 backend user stories.
"""
import asyncio
import json
import sys
import time
from typing import Optional

import requests
import websockets

# Public endpoint from frontend/.env
BASE_URL = "https://btc-arbitrage-bot-1.preview.emergentagent.com/api"
WS_URL = "wss://btc-arbitrage-bot-1.preview.emergentagent.com/api/ws/state"

# Demo credentials from backend/.env
DEMO_EMAIL = "trader@scalper.local"
DEMO_PASSWORD = "scalper2026"
TV_SECRET = "tv-scalper-secret-change-me"


class BackendTester:
    def __init__(self):
        self.token: Optional[str] = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def test(self, name: str, condition: bool, error_msg: str = ""):
        """Record test result."""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            print(f"✅ PASS: {name}")
            return True
        else:
            self.tests_failed += 1
            msg = f"❌ FAIL: {name}"
            if error_msg:
                msg += f" — {error_msg}"
            print(msg)
            self.failures.append({"test": name, "error": error_msg})
            return False

    def test_auth_login_valid(self):
        """Test POST /api/auth/login with valid demo credentials."""
        print("\n🔍 Testing: POST /api/auth/login (valid credentials)")
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=10,
            )
            self.test("Login returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Login response has token", "token" in data, f"Response: {data}")
                self.test("Login response has email", "email" in data, f"Response: {data}")
                if "token" in data:
                    self.token = data["token"]
                    print(f"   Token acquired: {self.token[:20]}...")
                    return True
            return False
        except Exception as e:
            self.test("Login request succeeded", False, str(e))
            return False

    def test_auth_login_invalid(self):
        """Test POST /api/auth/login with invalid credentials."""
        print("\n🔍 Testing: POST /api/auth/login (invalid credentials)")
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": "wrong@example.com", "password": "wrongpass"},
                timeout=10,
            )
            self.test("Invalid login returns 401", resp.status_code == 401, f"Got {resp.status_code}")
            return resp.status_code == 401
        except Exception as e:
            self.test("Invalid login request succeeded", False, str(e))
            return False

    def test_state_authenticated(self):
        """Test GET /api/state (authenticated)."""
        print("\n🔍 Testing: GET /api/state (authenticated)")
        if not self.token:
            self.test("State endpoint requires token", False, "No token available")
            return False
        try:
            resp = requests.get(
                f"{BASE_URL}/state",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            )
            self.test("GET /api/state returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                # Verify structure
                self.test("State has spot_price", "spot_price" in data, f"Keys: {list(data.keys())}")
                self.test("State spot_price > 0", data.get("spot_price", 0) > 0, f"spot_price={data.get('spot_price')}")
                self.test("State has markets array", "markets" in data and isinstance(data["markets"], list), f"markets type: {type(data.get('markets'))}")
                self.test("State markets non-empty", len(data.get("markets", [])) > 0, f"markets count: {len(data.get('markets', []))}")
                self.test("State has ws_status", "ws_status" in data, f"Keys: {list(data.keys())}")
                ws_status = data.get("ws_status", {})
                self.test("ws_status.coinbase = 'connected'", ws_status.get("coinbase") == "connected", f"coinbase: {ws_status.get('coinbase')}")
                self.test("ws_status.okx in ['connected','polling']", ws_status.get("okx") in ["connected", "polling"], f"okx: {ws_status.get('okx')}")
                self.test("ws_status.polymarket in ['connected','polling']", ws_status.get("polymarket") in ["connected", "polling"], f"polymarket: {ws_status.get('polymarket')}")
                
                # Graph structure
                self.test("State has graph", "graph" in data, f"Keys: {list(data.keys())}")
                graph = data.get("graph", {})
                nodes = graph.get("nodes", [])
                links = graph.get("links", [])
                self.test("Graph has exactly 100 nodes", len(nodes) == 100, f"nodes count: {len(nodes)}")
                self.test("Graph has exactly 180 links", len(links) == 180, f"links count: {len(links)}")
                
                # Verify node structure
                if nodes:
                    node = nodes[0]
                    self.test("Node has id", "id" in node, f"Node keys: {list(node.keys())}")
                    self.test("Node has group", "group" in node, f"Node keys: {list(node.keys())}")
                    self.test("Node has color", "color" in node, f"Node keys: {list(node.keys())}")
                    self.test("Node has val", "val" in node, f"Node keys: {list(node.keys())}")
                    self.test("Node has label", "label" in node, f"Node keys: {list(node.keys())}")
                    self.test("Node has score", "score" in node, f"Node keys: {list(node.keys())}")
                
                # Verify link structure
                if links:
                    link = links[0]
                    self.test("Link has source", "source" in link, f"Link keys: {list(link.keys())}")
                    self.test("Link has target", "target" in link, f"Link keys: {list(link.keys())}")
                    self.test("Link has weight", "weight" in link, f"Link keys: {list(link.keys())}")
                
                # Signals, edge, settings
                self.test("State has signals", "signals" in data, f"Keys: {list(data.keys())}")
                self.test("State has edge", "edge" in data, f"Keys: {list(data.keys())}")
                self.test("State has settings", "settings" in data, f"Keys: {list(data.keys())}")
                
                return True
            return False
        except Exception as e:
            self.test("GET /api/state request succeeded", False, str(e))
            return False

    def test_state_public(self):
        """Test GET /api/state/public (unauthenticated)."""
        print("\n🔍 Testing: GET /api/state/public (unauthenticated)")
        try:
            resp = requests.get(f"{BASE_URL}/state/public", timeout=10)
            self.test("GET /api/state/public returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Public state has spot_price", "spot_price" in data, f"Keys: {list(data.keys())}")
                self.test("Public state has markets", "markets" in data, f"Keys: {list(data.keys())}")
                self.test("Public state has graph", "graph" in data, f"Keys: {list(data.keys())}")
                return True
            return False
        except Exception as e:
            self.test("GET /api/state/public request succeeded", False, str(e))
            return False

    def test_settings_update(self):
        """Test PUT /api/settings to update edge_threshold."""
        print("\n🔍 Testing: PUT /api/settings (update edge_threshold)")
        if not self.token:
            self.test("Settings update requires token", False, "No token available")
            return False
        try:
            # Update edge_threshold to 0.005
            resp = requests.put(
                f"{BASE_URL}/settings",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"edge_threshold": 0.005},
                timeout=10,
            )
            self.test("PUT /api/settings returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Settings edge_threshold updated", data.get("edge_threshold") == 0.005, f"edge_threshold={data.get('edge_threshold')}")
                
                # Verify with GET
                resp_get = requests.get(
                    f"{BASE_URL}/settings",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                if resp_get.status_code == 200:
                    data_get = resp_get.json()
                    self.test("GET /api/settings reflects update", data_get.get("edge_threshold") == 0.005, f"edge_threshold={data_get.get('edge_threshold')}")
                return True
            return False
        except Exception as e:
            self.test("PUT /api/settings request succeeded", False, str(e))
            return False

    def test_mode_live_blocked(self):
        """Test POST /api/mode with live mode (should fail - no POLY_PRIVATE_KEY)."""
        print("\n🔍 Testing: POST /api/mode (live mode - should fail)")
        if not self.token:
            self.test("Mode switch requires token", False, "No token available")
            return False
        try:
            resp = requests.post(
                f"{BASE_URL}/mode",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"mode": "live", "confirm": True},
                timeout=10,
            )
            self.test("POST /api/mode live returns 400", resp.status_code == 400, f"Got {resp.status_code}")
            if resp.status_code == 400:
                data = resp.json()
                detail = data.get("detail", "")
                self.test("Error mentions POLY_PRIVATE_KEY", "POLY_PRIVATE_KEY" in detail, f"detail: {detail}")
                return True
            return False
        except Exception as e:
            self.test("POST /api/mode live request succeeded", False, str(e))
            return False

    def test_mode_paper_success(self):
        """Test POST /api/mode with paper mode (should succeed)."""
        print("\n🔍 Testing: POST /api/mode (paper mode - should succeed)")
        if not self.token:
            self.test("Mode switch requires token", False, "No token available")
            return False
        try:
            resp = requests.post(
                f"{BASE_URL}/mode",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"mode": "paper"},
                timeout=10,
            )
            self.test("POST /api/mode paper returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Mode set to paper", data.get("mode") == "paper", f"mode={data.get('mode')}")
                return True
            return False
        except Exception as e:
            self.test("POST /api/mode paper request succeeded", False, str(e))
            return False

    def test_kill_switch(self):
        """Test POST /api/kill_switch."""
        print("\n🔍 Testing: POST /api/kill_switch")
        if not self.token:
            self.test("Kill switch requires token", False, "No token available")
            return False
        try:
            # Engage kill switch
            resp = requests.post(
                f"{BASE_URL}/kill_switch",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"engaged": True},
                timeout=10,
            )
            self.test("POST /api/kill_switch (engage) returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Kill switch engaged", data.get("kill_switch") is True, f"kill_switch={data.get('kill_switch')}")
                
                # Verify in state
                resp_state = requests.get(
                    f"{BASE_URL}/state",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                if resp_state.status_code == 200:
                    state = resp_state.json()
                    self.test("State reflects kill_switch=true", state.get("kill_switch") is True, f"kill_switch={state.get('kill_switch')}")
                
                # Disengage
                resp_off = requests.post(
                    f"{BASE_URL}/kill_switch",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"engaged": False},
                    timeout=10,
                )
                if resp_off.status_code == 200:
                    data_off = resp_off.json()
                    self.test("Kill switch disengaged", data_off.get("kill_switch") is False, f"kill_switch={data_off.get('kill_switch')}")
                return True
            return False
        except Exception as e:
            self.test("POST /api/kill_switch request succeeded", False, str(e))
            return False

    def test_select_market(self):
        """Test POST /api/select_market."""
        print("\n🔍 Testing: POST /api/select_market")
        if not self.token:
            self.test("Select market requires token", False, "No token available")
            return False
        try:
            # Get markets first
            resp_state = requests.get(
                f"{BASE_URL}/state",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            )
            if resp_state.status_code != 200:
                self.test("Get markets for selection", False, "Could not fetch state")
                return False
            
            markets = resp_state.json().get("markets", [])
            if not markets:
                self.test("Markets available for selection", False, "No markets found")
                return False
            
            market_id = markets[0].get("market_id")
            resp = requests.post(
                f"{BASE_URL}/select_market",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"market_id": market_id},
                timeout=10,
            )
            self.test("POST /api/select_market returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Selected market returned", "selected" in data, f"Response: {data}")
                
                # Verify in state
                time.sleep(1)  # Wait for book refresh
                resp_state2 = requests.get(
                    f"{BASE_URL}/state",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                if resp_state2.status_code == 200:
                    state = resp_state2.json()
                    selected = state.get("selected_market", {})
                    self.test("State selected_market updated", selected.get("market_id") == market_id, f"selected_market.market_id={selected.get('market_id')}")
                    self.test("State selected_book populated", "selected_book" in state and state["selected_book"], f"selected_book keys: {list(state.get('selected_book', {}).keys())}")
                return True
            return False
        except Exception as e:
            self.test("POST /api/select_market request succeeded", False, str(e))
            return False

    def test_wallet_config(self):
        """Test POST /api/wallet/config and GET /api/wallet/status."""
        print("\n🔍 Testing: POST /api/wallet/config + GET /api/wallet/status")
        if not self.token:
            self.test("Wallet config requires token", False, "No token available")
            return False
        try:
            # Save dummy values (DO NOT use real keys)
            resp = requests.post(
                f"{BASE_URL}/wallet/config",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "private_key": "dummy_key_for_testing",
                    "funder_address": "0xDummyAddress",
                },
                timeout=10,
            )
            self.test("POST /api/wallet/config returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("Wallet config response has 'configured'", "configured" in data, f"Response: {data}")
                configured = data.get("configured", {})
                self.test("private_key configured", configured.get("private_key") is True, f"configured: {configured}")
                self.test("funder_address configured", configured.get("funder_address") is True, f"configured: {configured}")
                
                # Verify with GET
                resp_status = requests.get(
                    f"{BASE_URL}/wallet/status",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                if resp_status.status_code == 200:
                    status = resp_status.json()
                    self.test("GET /api/wallet/status private_key=true", status.get("private_key") is True, f"status: {status}")
                    self.test("GET /api/wallet/status funder_address=true", status.get("funder_address") is True, f"status: {status}")
                return True
            return False
        except Exception as e:
            self.test("POST /api/wallet/config request succeeded", False, str(e))
            return False

    def test_tradingview_webhook(self):
        """Test POST /api/webhooks/tradingview with correct and wrong secret."""
        print("\n🔍 Testing: POST /api/webhooks/tradingview")
        try:
            # Test with correct secret
            resp_ok = requests.post(
                f"{BASE_URL}/webhooks/tradingview",
                json={
                    "secret": TV_SECRET,
                    "symbol": "BTCUSDT",
                    "action": "BUY",
                    "price": 95000.0,
                    "rsi": 65.0,
                    "note": "Test webhook",
                },
                timeout=10,
            )
            self.test("POST /api/webhooks/tradingview (correct secret) returns 200", resp_ok.status_code == 200, f"Got {resp_ok.status_code}")
            if resp_ok.status_code == 200:
                data = resp_ok.json()
                self.test("Webhook response ok=true", data.get("ok") is True, f"Response: {data}")
            
            # Test with wrong secret
            resp_bad = requests.post(
                f"{BASE_URL}/webhooks/tradingview",
                json={
                    "secret": "wrong-secret",
                    "symbol": "BTCUSDT",
                    "action": "SELL",
                },
                timeout=10,
            )
            self.test("POST /api/webhooks/tradingview (wrong secret) returns 401", resp_bad.status_code == 401, f"Got {resp_bad.status_code}")
            
            return True
        except Exception as e:
            self.test("POST /api/webhooks/tradingview request succeeded", False, str(e))
            return False

    def test_tv_events(self):
        """Test GET /api/tv_events."""
        print("\n🔍 Testing: GET /api/tv_events")
        if not self.token:
            self.test("TV events requires token", False, "No token available")
            return False
        try:
            resp = requests.get(
                f"{BASE_URL}/tv_events",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            )
            self.test("GET /api/tv_events returns 200", resp.status_code == 200, f"Got {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.test("TV events response has 'events'", "events" in data, f"Response keys: {list(data.keys())}")
                events = data.get("events", [])
                self.test("TV events list is array", isinstance(events, list), f"events type: {type(events)}")
                if events:
                    print(f"   Found {len(events)} TV events")
                return True
            return False
        except Exception as e:
            self.test("GET /api/tv_events request succeeded", False, str(e))
            return False

    async def test_websocket(self):
        """Test WebSocket /api/ws/state."""
        print("\n🔍 Testing: WebSocket /api/ws/state")
        try:
            async with websockets.connect(WS_URL, ping_interval=20, close_timeout=5) as ws:
                # Read at least 1 frame
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(raw)
                self.test("WebSocket delivers JSON snapshot", isinstance(data, dict), f"data type: {type(data)}")
                self.test("WebSocket snapshot has spot_price", "spot_price" in data, f"Keys: {list(data.keys())}")
                self.test("WebSocket snapshot has markets", "markets" in data, f"Keys: {list(data.keys())}")
                print(f"   WebSocket frame received: {len(raw)} bytes")
                return True
        except Exception as e:
            self.test("WebSocket connection succeeded", False, str(e))
            return False

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for f in self.failures:
                print(f"  - {f['test']}: {f['error']}")
        
        print("=" * 60)
        return self.tests_failed == 0


async def main():
    tester = BackendTester()
    
    print("=" * 60)
    print("🚀 POLYMARKET BTC SCALPER - BACKEND API TEST SUITE")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print("=" * 60)
    
    # Run all tests
    tester.test_auth_login_valid()
    tester.test_auth_login_invalid()
    tester.test_state_authenticated()
    tester.test_state_public()
    tester.test_settings_update()
    tester.test_mode_live_blocked()
    tester.test_mode_paper_success()
    tester.test_kill_switch()
    tester.test_select_market()
    tester.test_wallet_config()
    tester.test_tradingview_webhook()
    tester.test_tv_events()
    await tester.test_websocket()
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
