from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.macro_fred import macro_data_text


@mcp.tool()
def fetch_macro_data(curr_date: str = "") -> dict:
    """Fetch key macroeconomic series from FRED (requires FRED_API_KEY).

    Series: US unemployment, nonfarm payrolls, CPI, fed funds rate, 2Y/10Y treasury yields,
    federal debt, dollar index, eurozone unemployment, Brent crude oil.

    Args:
        curr_date: As-of date label YYYY-MM-DD. Defaults to today if not provided.
    """
    from datetime import date

    if not curr_date:
        curr_date = date.today().isoformat()

    text = macro_data_text(curr_date)
    return ToolResult(
        summary=f"FRED macro data as-of {curr_date}",
        artifacts=[Artifact(path_hint="macro_data.txt", media_type="text/plain", content=text)],
    ).model_dump()
