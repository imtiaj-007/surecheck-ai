from fastapi import Request


async def get_real_ip(request: Request) -> str:
    """
    Get the real IP address of the client, handling proxies (Nginx/Cloudflare/Railway).

    This checks standard headers like X-Forwarded-For which are set by load balancers.
    If not found, it falls back to the direct client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if isinstance(ip, str) and ip:
            return ip

    client_host = getattr(request.client, "host", None)
    if isinstance(client_host, str) and client_host:
        return client_host

    return "127.0.0.1"
