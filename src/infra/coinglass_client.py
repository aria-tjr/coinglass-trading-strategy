"""
Enhanced CoinGlass API Client for derivatives market data.

Provides async access to Open Interest, Funding Rates, Long/Short ratios,
and real-time liquidation data via REST API with robust error handling.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import websockets
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from core.logger import get_logger, trading_logger

logger = get_logger("coinglass")


class CoinGlassError(Exception):
    """Custom exception for CoinGlass API errors."""
    pass


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            now = datetime.now()
            
            # Remove old requests outside time window
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < timedelta(seconds=self.time_window)
            ]
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.requests.append(now)


class CoinGlassClient:
    """
    Enhanced CoinGlass API client with comprehensive error handling.
    """
    
    def __init__(self):
        """Initialize the CoinGlass client."""
        self.base_url = settings.coinglass_base_url
        self.api_key = settings.coinglass_api_key
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Enhanced configuration
        self.rate_limiter = RateLimiter(max_requests=50, time_window=60)
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 30  # seconds
        self.connected = False
        self.last_error_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Connection pool settings
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        
        # WebSocket connection for liquidations
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self.ws_running = False
        
        logger.info("Enhanced CoinGlass client initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> bool:
        """Establish connection to CoinGlass API."""
        try:
            if self.http_client:
                await self.http_client.aclose()
            
            headers = {
                "accept": "application/json",
                "coinglassSecret": self.api_key,
                "User-Agent": "CoinGlass-Trader/1.0"
            }
            
            self.http_client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True
            )
            
            # Test connection
            await self._test_connection()
            
            self.connected = True
            self.consecutive_errors = 0
            logger.info("Successfully connected to CoinGlass API")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to CoinGlass API: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from CoinGlass API."""
        if self.http_client:
            try:
                await self.http_client.aclose()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
        
        self.connected = False
        self.http_client = None
        logger.info("Disconnected from CoinGlass")
        
        if self.ws_connection and not self.ws_connection.closed:
            await self.ws_connection.close()
            self.ws_running = False
            logger.info("WebSocket disconnected")
    
    async def _test_connection(self) -> None:
        """Test API connection with a simple request."""
        try:
            response = await self.http_client.get(f"{self.base_url}/v2/indicator/funding_rates_ohlc", 
                                               params={"symbol": "BTC", "limit": 1})
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") != "0":
                raise CoinGlassError(f"API test failed: {data.get('msg', 'Unknown error')}")
            
            logger.info("CoinGlass API connection test successful")
            
        except Exception as e:
            raise CoinGlassError(f"Connection test failed: {e}") from e
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if not self.connected:
                return await self.connect()
            
            # Simple health check request
            await self._test_connection()
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key for request."""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        age = datetime.now().timestamp() - cache_entry["timestamp"]
        return age < self.cache_ttl
    
    def _should_retry_after_error(self) -> bool:
        """Check if we should retry after consecutive errors."""
        if self.consecutive_errors >= self.max_consecutive_errors:
            if self.last_error_time:
                time_since_error = datetime.now() - self.last_error_time
                # Wait 5 minutes before retrying after too many errors
                return time_since_error > timedelta(minutes=5)
            return False
        return True
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make HTTP request to CoinGlass API with enhanced error handling.
        """
        if not self._should_retry_after_error():
            raise CoinGlassError("Too many consecutive errors, temporarily disabled")
        
        if not self.http_client:
            await self.connect()
        
        params = params or {}
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache first
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.debug(f"Using cached data for {endpoint}")
            return self.cache[cache_key]["data"]
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Enhanced response validation
            if not isinstance(data, dict):
                raise CoinGlassError(f"Invalid response format from {endpoint}")
            
            # Handle different response formats
            if "code" in data:
                if data.get("code") != "0":
                    error_msg = data.get("msg", "Unknown API error")
                    if "upgrade plan" in error_msg.lower():
                        logger.warning(f"API plan limitation: {error_msg}")
                        # Don't count plan limitations as errors
                        return {"data": [], "limited": True}
                    else:
                        raise CoinGlassError(f"API error: {error_msg}")
                
                result = data.get("data", {})
            else:
                # Some endpoints return data directly
                result = data
            
            # Cache the result
            self.cache[cache_key] = {
                "data": result,
                "timestamp": datetime.now().timestamp()
            }
            
            # Reset error tracking on success
            self.consecutive_errors = 0
            self.last_error_time = None
            
            trading_logger.log_data_update(
                "coinglass", 
                endpoint,
                status="success",
                cached=False
            )
            
            return result
            
        except httpx.HTTPStatusError as e:
            self._handle_error(e, endpoint)
            error_msg = f"HTTP {e.response.status_code} error for {endpoint}"
            
            # Handle specific status codes
            if e.response.status_code == 429:
                logger.warning("Rate limit exceeded, implementing backoff")
                await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
            elif e.response.status_code == 403:
                logger.error("API access forbidden - check API key")
            elif e.response.status_code >= 500:
                logger.warning("Server error, will retry")
            
            raise CoinGlassError(error_msg) from e
            
        except httpx.RequestError as e:
            self._handle_error(e, endpoint)
            error_msg = f"Request error for {endpoint}: {str(e)}"
            raise CoinGlassError(error_msg) from e
        
        except json.JSONDecodeError as e:
            self._handle_error(e, endpoint)
            raise CoinGlassError(f"Invalid JSON response from {endpoint}") from e
        
        except Exception as e:
            self._handle_error(e, endpoint)
            raise CoinGlassError(f"Unexpected error for {endpoint}: {str(e)}") from e
    
    def _handle_error(self, error: Exception, endpoint: str):
        """Handle and track errors."""
        self.consecutive_errors += 1
        self.last_error_time = datetime.now()
        
        logger.error(f"Error in CoinGlass request ({self.consecutive_errors}/{self.max_consecutive_errors}): {error}")
        trading_logger.log_error("coinglass_request", error, endpoint=endpoint)
        
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.critical("Too many consecutive CoinGlass API errors - temporarily disabling")
    
    async def get_open_interest_ohlc(
        self, 
        symbol: str, 
        interval: str = "1h", 
        limit: int = 100
    ) -> List[Dict]:
        """
        Get Open Interest OHLC data with fallback handling.
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 500)
        }
        
        try:
            data = await self._make_request("v2/indicator/open_interest_ohlc", params)
            
            if isinstance(data, dict) and data.get("limited"):
                logger.warning(f"Open Interest data limited for {symbol} due to API plan")
                return []
            
            if not isinstance(data, list):
                logger.warning(f"Unexpected OI data format for {symbol}")
                return []
            
            logger.debug(f"Fetched {len(data)} OI data points for {symbol}")
            return data
            
        except CoinGlassError as e:
            logger.error(f"Failed to fetch OI data for {symbol}: {e}")
            return []
    
    async def get_funding_rate_ohlc(
        self, 
        symbol: str, 
        interval: str = "8h", 
        limit: int = 100
    ) -> List[Dict]:
        """
        Get Funding Rate OHLC data with enhanced error handling.
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 500)
        }
        
        try:
            data = await self._make_request("v2/indicator/funding_rates_ohlc", params)
            
            if isinstance(data, dict) and data.get("limited"):
                logger.warning(f"Funding rate data limited for {symbol} due to API plan")
                return []
            
            if not isinstance(data, list):
                logger.warning(f"Unexpected funding data format for {symbol}")
                return []
            
            logger.debug(f"Fetched {len(data)} funding rate points for {symbol}")
            return data
            
        except CoinGlassError as e:
            logger.error(f"Failed to fetch funding data for {symbol}: {e}")
            return []
    
    async def get_long_short_ratio(
        self, 
        symbol: str, 
        interval: str = "1h", 
        limit: int = 100
    ) -> List[Dict]:
        """
        Get Long/Short ratio data with fallback.
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 500)
        }
        
        try:
            data = await self._make_request("v2/indicator/long_short_ratio", params)
            
            if isinstance(data, dict) and data.get("limited"):
                logger.warning(f"L/S ratio data limited for {symbol} due to API plan")
                return []
            
            if not isinstance(data, list):
                logger.warning(f"Unexpected LS ratio data format for {symbol}")
                return []
            
            logger.debug(f"Fetched {len(data)} LS ratio points for {symbol}")
            return data
            
        except CoinGlassError as e:
            logger.error(f"Failed to fetch LS ratio data for {symbol}: {e}")
            return []
    
    async def get_market_sentiment(self, symbol: str) -> Dict[str, float]:
        """
        Get comprehensive market sentiment data with fallbacks.
        """
        try:
            # Try to fetch all sentiment indicators
            tasks = [
                self.get_funding_rate_ohlc(symbol, limit=1),
                self.get_long_short_ratio(symbol, limit=1),
                self.get_open_interest_ohlc(symbol, limit=1)
            ]
            
            funding_data, ls_data, oi_data = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            
            sentiment = {
                "funding_rate": 0.0,
                "long_short_ratio": 0.5,  # Neutral
                "oi_change": 0.0,
                "confidence": 0.0
            }
            
            confidence_factors = 0
            
            # Process funding rate
            if isinstance(funding_data, list) and funding_data:
                try:
                    sentiment["funding_rate"] = float(funding_data[0].get("c", 0))
                    confidence_factors += 1
                except (ValueError, TypeError, KeyError):
                    logger.warning("Invalid funding rate data format")
            
            # Process long/short ratio
            if isinstance(ls_data, list) and ls_data:
                try:
                    sentiment["long_short_ratio"] = float(ls_data[0].get("longShortRatio", 0.5))
                    confidence_factors += 1
                except (ValueError, TypeError, KeyError):
                    logger.warning("Invalid L/S ratio data format")
            
            # Process OI change
            if isinstance(oi_data, list) and len(oi_data) >= 2:
                try:
                    current_oi = float(oi_data[0].get("c", 0))
                    prev_oi = float(oi_data[1].get("c", 0))
                    if prev_oi > 0:
                        sentiment["oi_change"] = ((current_oi - prev_oi) / prev_oi) * 100
                        confidence_factors += 1
                except (ValueError, TypeError, KeyError, IndexError):
                    logger.warning("Invalid OI data format")
            
            # Calculate confidence based on available data
            sentiment["confidence"] = confidence_factors / 3.0
            
            if confidence_factors == 0:
                logger.warning(f"No sentiment data available for {symbol}")
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Failed to get market sentiment for {symbol}: {e}")
            return {
                "funding_rate": 0.0,
                "long_short_ratio": 0.5,
                "oi_change": 0.0,
                "confidence": 0.0
            }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status."""
        return {
            "connected": self.connected,
            "consecutive_errors": self.consecutive_errors,
            "max_errors": self.max_consecutive_errors,
            "last_error": self.last_error_time.isoformat() if self.last_error_time else None,
            "cache_entries": len(self.cache),
            "api_limited": self.consecutive_errors >= self.max_consecutive_errors
        }
    
    async def start_liquidation_stream(self, callback=None) -> None:
        """
        Start WebSocket stream for real-time liquidation data.
        
        Args:
            callback: Function to call with liquidation events
        """
        if self.ws_running:
            logger.warning("Liquidation stream already running")
            return
        
        ws_url = "wss://ws.coinglass.com/ws/public"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.ws_connection = websocket
                self.ws_running = True
                
                # Subscribe to liquidation orders
                subscribe_msg = {
                    "channel": "liquidationOrders",
                    "event": "subscribe"
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                logger.info("Subscribed to liquidation stream")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        if data.get("channel") == "liquidationOrders":
                            liquidation_data = data.get("data", {})
                            
                            trading_logger.log_data_update(
                                "liquidation",
                                liquidation_data.get("symbol", ""),
                                side=liquidation_data.get("side"),
                                size=liquidation_data.get("size"),
                                price=liquidation_data.get("price")
                            )
                            
                            if callback:
                                await callback(liquidation_data)
                                
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing liquidation data: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.ws_running = False
        finally:
            self.ws_running = False
            logger.info("Liquidation stream stopped")
    
    async def stop_liquidation_stream(self) -> None:
        """Stop the liquidation WebSocket stream."""
        if self.ws_connection and not self.ws_connection.closed:
            await self.ws_connection.close()
        self.ws_running = False
        logger.info("Liquidation stream stop requested")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        valid_entries = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "cache_hit_ratio": valid_entries / len(self.cache) if self.cache else 0
        }


# Global CoinGlass client instance
coinglass_client = CoinGlassClient() 