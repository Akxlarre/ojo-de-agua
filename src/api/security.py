"""
Seguridad, Control de Acceso y Rate Limiting para la Plataforma de Inteligencia Hídrica.
Implementa:
1. SecurityHeadersMiddleware (Protección contra sniffing, clickjacking y XSS)
2. TokenBucketRateLimiter (Protección contra DoS y ráfagas no controladas)
3. APIKeyValidator (Autenticación configurable para despliegue público)
"""

import os
import time
from collections import defaultdict
from typing import Callable, Dict, Optional, Tuple
from fastapi import Header, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Inyecta cabeceras HTTP de seguridad según recomendaciones OWASP.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/mapa"):
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
            if "Content-Security-Policy" in response.headers:
                del response.headers["Content-Security-Policy"]
        else:
            response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class TokenBucketRateLimiter:
    """
    Limitador de tasa de peticiones en memoria basado en el algoritmo Token Bucket.
    Permite ráfagas controladas y reposición continua de tokens.
    """

    def __init__(self, capacity: int = 120, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        # ip -> (tokens, last_update_time)
        self.buckets: Dict[str, Tuple[float, float]] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        now = time.time()
        tokens, last_update = self.buckets.get(client_ip, (float(self.capacity), now))

        # Calcular tokens acumulados desde la última petición
        elapsed = now - last_update
        tokens = min(float(self.capacity), tokens + (elapsed * self.refill_rate))

        if tokens >= 1.0:
            self.buckets[client_ip] = (tokens - 1.0, now)
            return True, 0
        else:
            self.buckets[client_ip] = (tokens, now)
            wait_time = int((1.0 - tokens) / self.refill_rate) + 1
            return False, wait_time

    def reset(self) -> None:
        """Limpia los buckets de memoria (útil para tests)."""
        self.buckets.clear()


# Instancia global del rate limiter (120 req de capacidad, 2 req/s reposición)
rate_limiter = TokenBucketRateLimiter(capacity=120, refill_rate_per_sec=2.0)


async def check_rate_limit(request: Request) -> None:
    """
    Dependencia de FastAPI para proteger endpoints intensivos.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    allowed, wait_seconds = rate_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de peticiones excedido. Reintente en {wait_seconds} segundos.",
            headers={"Retry-After": str(wait_seconds)}
        )


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Valida la clave de API si la variable de entorno WATER_INTEL_API_KEY está configurada.
    En entorno de desarrollo o local (sin la variable seteada), el acceso es irrestricto.
    """
    configured_key = os.getenv("WATER_INTEL_API_KEY", "").strip()
    if not configured_key:
        return "dev-mode-unauthenticated"

    token = x_api_key
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if not token or token != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida o API Key inválida.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return token
