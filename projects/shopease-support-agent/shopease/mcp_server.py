"""ShopEase order tools as an MCP server (stdio). Day 8.

The host (your agent, Claude Desktop, an IDE) starts this process per customer session and passes the
authenticated customer id in the SHOPEASE_CUSTOMER_ID environment variable. The model can't change it.

    SHOPEASE_CUSTOMER_ID=C001 python -m shopease.mcp_server
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from . import config, tools

mcp = MCPServer("shopease-orders", instructions="Order and refund-eligibility tools for one ShopEase customer.")


def _session() -> tools.Session:
    cid = os.environ.get("SHOPEASE_CUSTOMER_ID")
    if not cid:
        raise RuntimeError("SHOPEASE_CUSTOMER_ID is not set by the host")
    return tools.Session(customer_id=cid, conversation_id="mcp")


@mcp.tool()
def get_customer_overview() -> str:
    """Get the logged-in customer's profile and their 5 most recent orders."""
    return tools.get_customer_overview(_session())


@mcp.tool()
def get_order(order_id: str) -> str:
    """Look up one of the customer's orders by id (e.g. 'O2001'). Returns item, amount, status and dates."""
    return tools.get_order(_session(), order_id)


@mcp.tool()
def search_orders(status: str | None = None, item: str | None = None) -> str:
    """Search the customer's orders by status (processing/shipped/delivered/returned) and/or item name."""
    return tools.search_orders(_session(), status=status, item=item)


@mcp.tool()
def check_refund_eligibility(order_id: str) -> str:
    """Check if an order can be refunded under ShopEase policy and whether a human must approve it."""
    return tools.check_refund_eligibility(_session(), order_id)


@mcp.resource("policy://{name}")
def policy(name: str) -> str:
    """A ShopEase policy document: returns, shipping, warranty or payments."""
    path = config.POLICY_DIR / f"{name}.md"
    return path.read_text() if path.exists() else f"No policy named {name}"


if __name__ == "__main__":
    mcp.run()  # stdio transport
