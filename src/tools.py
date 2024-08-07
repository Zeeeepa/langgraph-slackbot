import requests
import html2text
from readability.readability import Document
from itertools import islice
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field


class SearchDDGInput(BaseModel):
    query: str = Field(description="検索したいキーワードを入力してください")


@tool(args_schema=SearchDDGInput)
def search_ddg(query, max_result_num=5):
    """
    ## Toolの説明
    本ToolはDuckDuckGoを利用し、Web検索を実行するためのツールです。

    ## Toolの動作方法
    1. userが検索したいキーワードに従ってWeb検索します
    2. assistantは以下の戻り値の形式で検索結果をuserに回答します

    ## 戻り値の形式

    Returns
    -------
    List[Dict[str, str]]:
    - title
    - snippet
    - url
    """

    # [1] Web検索を実施
    res = DDGS().text(query, region="jp-jp", safesearch="off", backend="lite")

    # [2] 結果のリストを分解して戻す
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "url": r.get("href", ""),
        }
        for r in islice(res, max_result_num)
    ]


class FetchPageInput(BaseModel):
    url: str = Field()


@tool(args_schema=FetchPageInput)
def fetch_page(url, page_num=0, timeout_sec=10):
    """
    ## Toolの説明
    本Toolは指定されたURLのWebページから本文の文章を取得するツールです。
    詳細な情報を取得するのに役立ちます

    ## Toolの動作方法
    1. userがWebページのURLを入力します
    2. assistantはHTTPレスポンスステータスコードと本文の文章内容をusrに回答します

    ## 戻り値の設定
    Returns
    -------
    Dict[str, Any]:
    - status: str
    - page_content
      - title: str
      - content: str
      - has_next: bool
    """

    try:
        response = requests.get(url, timeout=timeout_sec)
        response.encoding = "utf-8"
    except requests.exceptions.Timeout:
        return {
            "page_content": {
                "error_message": "Could not download page due to Timeout Error. Please try to fetch other pages."
            },
        }

    doc = Document(response.text)
    title = doc.title()
    html_content = doc.summary()
    content = html2text.html2text(html_content)

    chunk_size = 1000 * 3  # 【chunk_sizeを大きくしておきます】
    content = content[:chunk_size]

    return {
        "page_content": {
            "title": title,
            "content": content,  # chunks[page_num], を文書分割をやめて、contentにします
            "has_next": False,  # page_num < len(chunks) - 1
        },
    }


all_tools = [search_ddg, fetch_page]