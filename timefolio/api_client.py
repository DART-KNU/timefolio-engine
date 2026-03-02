"""
TimefolioAPIClient
------------------
Low-level HTTP client for the Timefolio contest API.

Responsibilities:
- Authenticate and attach the Bearer token to all subsequent requests.
- Expose generic ``get`` / ``post`` helpers consumed by higher-level components.
"""

import logging
import requests

logger = logging.getLogger(__name__)


class TimefolioAPIClient:
    """HTTP client that manages a single authenticated session with the Timefolio server.

    All requests share one :class:`requests.Session`, so the Bearer token and
    any server-set cookies are automatically reused across calls.

    :param email: Account e-mail registered on contest.timefolio.net
    :param password: Account password
    """

    BASE_URL = "https://contest.timefolio.net/api"

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                ),
                "Origin": "https://contest.timefolio.net",
                "Referer": "https://contest.timefolio.net/",
            }
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """Authenticate with the server and store the Bearer token.

        After a successful login every subsequent :meth:`get` / :meth:`post`
        call automatically includes the ``Authorization`` header.

        :returns: ``True`` on success, ``False`` on failure.
        """
        logger.info("Attempting to log in as %s ...", self.email)
        url = f"{self.BASE_URL}/Auth/Login"
        payload = {"email": self.email, "password": self.password}

        res = self.session.post(url, json=payload)
        if res.status_code == 200:
            data = res.json()
            token = data.get("token") or data.get("accessToken")
            if token:
                self.session.headers["Authorization"] = f"Bearer {token}"
                logger.info("Login successful.")
                return True

        logger.error("Login failed (HTTP %s): %s", res.status_code, res.text)
        return False

    # ------------------------------------------------------------------
    # Raw request helpers
    # ------------------------------------------------------------------

    def post(self, endpoint: str, payload: dict = None) -> requests.Response:
        """Send a POST request to ``BASE_URL/<endpoint>``.

        :param endpoint: Path segment after ``/api/``, e.g. ``"Portfolio/AddOrder"``.
        :param payload: JSON-serialisable request body.
        :returns: :class:`requests.Response`
        """
        return self.session.post(f"{self.BASE_URL}/{endpoint}", json=payload)

    def get(self, endpoint: str, params: dict = None) -> requests.Response:
        """Send a GET request to ``BASE_URL/<endpoint>``.

        :param endpoint: Path segment after ``/api/``, e.g. ``"Portfolio/Summary"``.
        :param params: URL query-string parameters.
        :returns: :class:`requests.Response`
        """
        return self.session.get(f"{self.BASE_URL}/{endpoint}", params=params)
