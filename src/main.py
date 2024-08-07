from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI

from tools import all_tools

CUSTOM_SYSTEM_PROMPT = """
## あなたの役割
あなたの役割はuserの入力する質問に対して、インターネットでWebページを調査をし、回答することです。

## あなたが従わなければいけないルール
1. 回答はできるだけ短く、要約して回答してください
2. 文章が長くなる場合は改行して見やすくしてください
3. 回答の最後に改行した後、参照したページのURLを記載してください

"""

# プロンプトを定義
prompt = ChatPromptTemplate.from_messages(
    [("system", CUSTOM_SYSTEM_PROMPT), ("user", "{messages}")]
)

def _modify_messages(messages: list[AnyMessage]):
    return prompt.invoke({"messages": messages}).to_messages()

llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

web_browsing_agent = create_react_agent(llm, all_tools, state_modifier=_modify_messages)
query_ddg = "2024年のオリンピックの開催地はどこですか？"

messages = web_browsing_agent.invoke({"messages": [("user", query_ddg)]})

print(messages)
