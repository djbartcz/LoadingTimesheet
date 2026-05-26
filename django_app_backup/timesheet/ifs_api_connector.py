"""
IFS API connector utilities.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class IFSAPIConnector:
    """
    IFS API Connector with OAuth2 client credentials authentication.
    """

    def __init__(self) -> None:
        # Prefer namespaced IFS_* variables, fallback to legacy keys.
        self.client_id = os.environ.get(
            "IFS_CLIENT_ID", os.environ.get("CLIENT_ID", "")
        ).strip()
        self.client_secret = os.environ.get(
            "IFS_CLIENT_SECRET", os.environ.get("CLIENT_SECRET", "")
        ).strip()
        self.token_url = os.environ.get(
            "IFS_TOKEN_URL", os.environ.get("TOKEN_URL", "")
        ).strip()
        self.scope = os.environ.get(
            "IFS_SCOPE", os.environ.get("SCOPE", "")
        ).strip()
        self.base_url = os.environ.get(
            "IFS_BASE_URL", os.environ.get("BASE_URL", "")
        ).strip().rstrip("/")
        self.access_token: Optional[str] = None

        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up file logging for IFS API requests."""
        log_dir = Path(settings.BASE_DIR) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "ifs_api_requests.log"
        file_handler_exists = any(
            isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", "") == str(log_file)
            for handler in logger.handlers
        )
        if not file_handler_exists:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s - %(message)s"
                )
            )
            logger.addHandler(file_handler)

        logger.setLevel(logging.INFO)

    def get_oauth2_token(self) -> str:
        """
        Fetch OAuth2 token from IFS token endpoint.
        """
        missing = [
            key
            for key, value in {
                "IFS_CLIENT_ID": self.client_id,
                "IFS_CLIENT_SECRET": self.client_secret,
                "IFS_TOKEN_URL": self.token_url,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required IFS OAuth settings: "
                + ", ".join(missing)
            )

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            data["scope"] = self.scope

        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.info("Successfully obtained OAuth2 token")
            return self.access_token
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to obtain OAuth2 token: %s", exc)
            raise Exception(f"Failed to obtain token: {exc}") from exc

    def get_headers(self) -> Dict[str, str]:
        """Build authenticated request headers."""
        if not self.access_token:
            self.get_oauth2_token()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an authenticated request to the IFS API.
        """
        if endpoint.startswith("http"):
            url = endpoint
        else:
            if not self.base_url:
                raise ValueError(
                    "IFS_BASE_URL (or BASE_URL fallback) must be configured."
                )
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

        headers = self.get_headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            if params:
                query_parts = []
                for key, value in params.items():
                    if key == "$filter":
                        # Keep OData filter unescaped where APIs
                        # expect raw expression.
                        query_parts.append(f"$filter={value}")
                    else:
                        query_parts.append(f"{key}={value}")
                full_url = f"{url}?{'&'.join(query_parts)}"
                logger.info("Full URL with params: %s", full_url)

                response = requests.request(
                    method=method,
                    url=full_url,
                    json=data,
                    headers=headers,
                    timeout=60,
                )
            else:
                logger.info("URL without params: %s", url)
                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                    params=params,
                    timeout=60,
                )

            logger.info(
                "IFS API Request: %s %s - Status: %s",
                method,
                url,
                response.status_code,
            )

            if not response.ok:
                logger.error(
                    "IFS API Error: %s - %s",
                    response.status_code,
                    response.text,
                )
            return response
        except requests.exceptions.RequestException as exc:
            logger.error("IFS API Request failed: %s", exc)
            raise

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        return self.make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        return self.make_request("POST", endpoint, data=data)

    def put(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        return self.make_request("PUT", endpoint, data=data)

    def patch(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        return self.make_request("PATCH", endpoint, data=data)

    def delete(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        return self.make_request("DELETE", endpoint, data=data)


class IFSAPIRequests:
    """
    Legacy APIRequests class for backward compatibility.
    """

    def __init__(self, base_url: str, headers: Dict[str, str]) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = headers

    def post(self, endpoint: str, data: Dict[str, Any]) -> requests.Response:
        return self._make_request(method="POST", endpoint=endpoint, data=data)

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        return self._make_request(
            method="GET", endpoint=endpoint, params=params
        )

    def delete(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        return self._make_request(
            method="DELETE",
            endpoint=endpoint,
            data=data,
            extra_headers=headers,
        )

    def patch(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        return self._make_request(
            method="PATCH", endpoint=endpoint, data=data, extra_headers=headers
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self.headers.copy()
        if extra_headers:
            request_headers.update(extra_headers)

        response: Optional[requests.Response] = None
        try:
            assert isinstance(data, (dict, type(None))), (
                "Data should be a dictionary or None."
            )
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=request_headers,
                params=params,
                timeout=60,
            )
            response.raise_for_status()
            return response
        except AssertionError as error:
            logger.error("Assertion Error: %s", error)
            raise
        except requests.exceptions.HTTPError:
            if response is not None:
                logger.error("Request failed %s", response.status_code)
                return response
            raise
        except requests.exceptions.RequestException as err:
            logger.error("General Error: %s", err)
            if response is not None:
                logger.error("Response content: %s", response.content)
            raise
