from typing import Annotated
from datetime import datetime
import akshare as ak
import pandas as pd


def get_AK_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):
    """Fetch OHLCV data from AKShare (A-share market)."""
    from datetime import datetime

    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    try:
        code = symbol[:6] if len(symbol) > 6 else symbol
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )

        if df.empty:
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

        df = df.rename(columns={
            "日期": "Date",
            "开盘": "Open",
            "最高": "High",
            "最低": "Low",
            "收盘": "Close",
            "成交量": "Volume",
        })
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

        numeric_columns = ["Open", "High", "Low", "Close"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].round(2)

        csv_string = df.to_csv(index=False)

        header = f"# Stock data for {symbol} from {start_date} to {end_date}\n"
        header += f"# Total records: {len(df)}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + csv_string

    except Exception as e:
        return f"Error retrieving AKShare data for {symbol}: {str(e)}"


def get_AK_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date (not used for AKShare)"] = None,
):
    """Get company fundamentals from AKShare (A-share market)."""
    from datetime import datetime

    try:
        code = ticker[:6] if len(ticker) > 6 else ticker
        info = ak.stock_individual_info_em(symbol=code)

        if info is None or info.empty:
            return f"No fundamentals data found for symbol '{ticker}'"

        info_dict = dict(zip(info["item"], info["value"]))

        fields = [
            ("Name", info_dict.get("股票简称")),
            ("Sector", info_dict.get("行业")),
            ("Industry", info_dict.get("行业")),
            ("Market Cap", info_dict.get("总市值")),
            ("PE Ratio (TTM)", info_dict.get("市盈率-动态")),
            ("Price to Book", info_dict.get("市净率")),
            ("EPS (TTM)", info_dict.get("每股收益")),
            ("Beta", info_dict.get("Beta")),
            ("52 Week High", info_dict.get("52周最高")),
            ("52 Week Low", info_dict.get("52周最低")),
        ]

        lines = []
        for label, value in fields:
            if value is not None:
                lines.append(f"{label}: {value}")

        header = f"# Company Fundamentals for {ticker}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving fundamentals for {ticker}: {str(e)}"


def _get_financial_statement(ticker: str, report_type: str, curr_date: str, freq: str):
    """Generic financial statement fetcher for A-share."""
    from datetime import datetime

    try:
        code = ticker[:6] if len(ticker) > 6 else ticker
        df = ak.stock_financial_report_sina(stock=code, symbol=report_type)

        if df.empty:
            return f"No {report_type} data found for symbol '{ticker}'"

        # Filter by date if curr_date provided
        if curr_date:
            cutoff = pd.Timestamp(curr_date)
            mask = pd.to_datetime(df.columns, format="%Y-%m-%d", errors="coerce") <= cutoff
            df = df.loc[:, mask]

        csv_string = df.to_csv()

        header = f"# {report_type} for {ticker} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + csv_string

    except Exception as e:
        return f"Error retrieving {report_type} for {ticker}: {str(e)}"


def get_AK_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Get balance sheet data from AKShare."""
    return _get_financial_statement(ticker, "资产负债表", curr_date, freq)


def get_AK_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Get cash flow data from AKShare."""
    return _get_financial_statement(ticker, "现金流量表", curr_date, freq)


def get_AK_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Get income statement data from AKShare."""
    return _get_financial_statement(ticker, "利润表", curr_date, freq)


def get_AK_news(
    ticker: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):
    """Retrieve news for a specific A-share stock from East Money."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    try:
        code = ticker[:6] if len(ticker) > 6 else ticker
        news_df = ak.stock_news_em(symbol=code)

        if news_df.empty:
            return f"No news found for {ticker}"

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + relativedelta(days=1)

        filtered_count = 0
        news_str = ""

        for _, row in news_df.iterrows():
            title = row.get("新闻标题", "")
            source = row.get("新闻媒体", "Unknown")
            link = row.get("新闻链接", "")
            pub_date_str = row.get("发布时间", "")

            if pub_date_str:
                try:
                    pub_date = datetime.strptime(pub_date_str[:19], "%Y-%m-%d %H:%M:%S")
                    if not (start_dt <= pub_date <= end_dt):
                        continue
                except ValueError:
                    pass

            news_str += f"### {title} (source: {source})\n"
            if link:
                news_str += f"Link: {link}\n"
            news_str += "\n"
            filtered_count += 1

        if filtered_count == 0:
            return f"No news found for {ticker} between {start_date} and {end_date}"

        return f"## {ticker} News, from {start_date} to {end_date}:\n\n{news_str}"

    except Exception as e:
        return f"Error fetching news for {ticker}: {str(e)}"


def get_AK_global_news(
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"],
    look_back_days: Annotated[int, "how many days to look back"] = 7,
    limit: Annotated[int, "max number of news articles to return"] = 10,
):
    """Retrieve macro/financial news relevant to A-share market analysis."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    try:
        news_df = ak.news_cctv(date=curr_date.replace("-", ""))

        if news_df is None or news_df.empty:
            return f"No global news found for {curr_date}"

        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - relativedelta(days=look_back_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        news_str = ""
        count = 0

        for _, row in news_df.iterrows():
            if count >= limit:
                break

            title = row.get("title", "")
            content = row.get("content", "")
            link = row.get("url", "")

            news_str += f"### {title}\n"
            if content:
                news_str += f"{content[:300]}...\n"
            if link:
                news_str += f"Link: {link}\n"
            news_str += "\n"
            count += 1

        if count == 0:
            return f"No global news found for {curr_date}"

        return f"## Global Market News, from {start_date} to {curr_date}:\n\n{news_str}"

    except Exception as e:
        return f"Error fetching global news: {str(e)}"


def get_AK_insider_transactions(
    ticker: Annotated[str, "ticker symbol of the company"],
):
    """Insider transactions are not available for A-share market in this format."""
    return "A 股内部人交易数据暂不可用"
