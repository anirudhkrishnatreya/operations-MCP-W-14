import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Fetch Server")


@mcp.tool()
def fetch_url(url: str) -> str:
    """
    Fetch the contents of a public URL.

    Args:
        url: The full URL to fetch (e.g., https://example.com).

    Returns:
        The text content of the URL, or an error message if fetching fails.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8")[
                :5000
            ]  # Return up to 5000 chars to avoid blowing up context window
    except urllib.error.URLError as e:
        return f"Error fetching URL: {e.reason}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


if __name__ == "__main__":
    mcp.run()
