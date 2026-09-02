import json, urllib.request, urllib.error

reg = json.load(open(r"C:\Users\15155\.workbuddy\connectors\default\mcp.json", encoding="utf-8"))
servers = list(reg.get("mcpServers", {}).keys())
mx = [s for s in servers if "mx" in s.lower()]
print("mx- servers in this env registry:", mx or "NONE")
print("westock present:", any("westock" in s for s in servers))
print("tdx present:", any("tdx" in s for s in servers))
print()


def probe(name, url, token=None, timeout=8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-11-25",
                                  "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        data = r.read(400).decode("utf-8", "replace").replace("\n", " ")
        print("[%s] HTTP %s ct=%s" % (name, r.status, r.headers.get("Content-Type")))
        print("   head:", data[:200])
    except urllib.error.HTTPError as e:
        print("[%s] HTTP %s: %s" % (name, e.code, e.read(300).decode("utf-8", "replace")[:200]))
    except Exception as e:
        print("[%s] ERR %s: %s" % (name, type(e).__name__, str(e)[:160]))


print("--- standalone reachability/auth probes (no platform session) ---")
probe("westock", "https://stockbuddy.qq.com/cgi/cgi-bin/openai/mcp/mcp")
probe("tdx", "https://txmcp.tdx.com.cn:3001/txmcp")
probe("jin10", "https://mcp.jin10.com/mcp", token="sk-R7V5Q69CqBwTmuX52qmdO0qnH_CgsCdT9cAV96LZ4I4")
