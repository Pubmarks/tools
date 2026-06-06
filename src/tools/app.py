from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from tools.config import cfg

# DNS-rebinding protection stays on, but because we bind 0.0.0.0 (not the
# localhost default) we must declare the host allowlist ourselves — otherwise
# FastMCP's localhost-only auto-default rejects cross-container callers with 421.
mcp = FastMCP(
    "tools",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=cfg.allowed_hosts,
        allowed_origins=[f"http://{h}" for h in cfg.allowed_hosts],
    ),
)
