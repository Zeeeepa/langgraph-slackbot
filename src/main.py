import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START
from typing import List, Literal, TypedDict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from tools import get_slack_thread_history, send_slack_message


class RouteQuery(BaseModel):
    """ユーザーのクエリを最も関連性の高いデータソースにルーティングします。"""

    datasource: Literal["vectorstore"] = Field(
        ...,
        description="ユーザーの質問に応じて、ウェブ検索またはベクターストアにルーティングします。",
    )


class GradeDocuments(BaseModel):
    """取得された文書の関連性チェックのためのバイナリスコア。"""

    binary_score: str = Field(
        description="文書が質問に関連しているかどうか、「yes」または「no」"
    )


class GradeHallucinations(BaseModel):
    """生成された回答における幻覚の有無を示すバイナリスコア。"""

    binary_score: str = Field(
        description="回答が事実に基づいているかどうか、「yes」または「no」"
    )


class GradeAnswer(BaseModel):
    """回答が質問に対処しているかどうかを評価するバイナリスコア。"""

    binary_score: str = Field(
        description="回答が質問に対処しているかどうか、「yes」または「no」"
    )


class GraphState(BaseModel):
    """グラフの状態を表すデータモデル"""

    question: str = Field(..., description="ユーザーの質問")
    generation: str = Field("", description="LLMが生成した回答")
    documents: List[str] = Field(default_factory=list, description="関連文書のリスト")
    context: str = Field("", description="会話のコンテキスト（スレッド履歴）")


async def route_question(state):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm_router = llm.with_structured_output(RouteQuery)

    from prompts import ROUTE_PROMPT
    route_prompt = ROUTE_PROMPT

    question_router = route_prompt | structured_llm_router

    question = state["question"]
    source = question_router.invoke({"question": question})
    if source.datasource == "vectorstore":
        return "vectorstore"


async def retrieve(state):
    embd = OpenAIEmbeddings()

    urls = [
        "https://lilianweng.github.io/posts/2023-06-23-agent/",
        "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
        "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
    ]

    docs = [WebBaseLoader(url).load() for url in urls]
    docs_list = [item for sublist in docs for item in sublist]

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)

    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=embd,
    )
    retriever = vectorstore.as_retriever()

    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}


async def grade_documents(state):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm_grader = llm.with_structured_output(GradeDocuments)

    from prompts import GRADE_DOCUMENTS_PROMPT
    grade_prompt = GRADE_DOCUMENTS_PROMPT

    retrieval_grader = grade_prompt | structured_llm_grader
    question = state["question"]
    documents = state["documents"]
    filtered_docs = []

    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score.binary_score
        if grade == "yes":
            filtered_docs.append(d)

    return {"documents": filtered_docs, "question": question}


async def generate(state):
    from prompts import GENERATION_PROMPT
    prompt = GENERATION_PROMPT

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

    rag_chain = prompt | llm | StrOutputParser()
    question = state["question"]
    documents = state["documents"]
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}


async def transform_query(state):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    from prompts import REWRITE_PROMPT
    re_write_prompt = REWRITE_PROMPT

    question_rewriter = re_write_prompt | llm | StrOutputParser()
    question = state["question"]
    documents = state["documents"]
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}


async def decide_to_generate(state):
    filtered_documents = state["documents"]
    if not filtered_documents:
        return "transform_query"
    else:
        return "generate"


async def grade_generation_v_documents_and_question(state):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm_grader = llm.with_structured_output(GradeHallucinations)

    from prompts import HALLUCINATION_PROMPT, ANSWER_GRADE_PROMPT
    hallucination_prompt = HALLUCINATION_PROMPT
    answer_prompt = ANSWER_GRADE_PROMPT

    answer_grader = answer_prompt | structured_llm_grader
    hallucination_grader = hallucination_prompt | structured_llm_grader
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score
    if grade == "yes":
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        if grade == "yes":
            return "useful"
        else:
            return "not useful"
    else:
        return "not supported"


import logging
from functools import wraps

# ロガーの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise

    return wrapper


@log_errors
async def run_workflow(inputs):
    logger.info(f"Starting workflow with inputs: {inputs}")
    value = await workflow.ainvoke(inputs)
    logger.info("Workflow completed successfully")
    return value["generation"]


# ワークフローの初期化
workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("transform_query", transform_query)

workflow.add_conditional_edges(
    START,
    route_question,
    {
        "vectorstore": "retrieve",
    },
)
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
    },
)
workflow.add_edge("transform_query", "retrieve")
workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "transform_query",
    },
)

app = workflow.compile()
app = app.with_config(recursion_limit=10, run_name="Agent", tags=["Agent"])


# Slackアプリの初期化
slack_app = App(token=os.environ["SLACK_BOT_TOKEN"])


@slack_app.event("app_mention")
def handle_app_mention_events(body, say):
    try:
        event = body["event"]
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        # スレッド履歴を取得
        thread_history = get_slack_thread_history(channel_id, thread_ts)

        # 最新の質問を取得
        question = event["text"].replace(f"<@{os.environ['SLACK_BOT_ID']}>", "").strip()

        # RAGワークフローを実行
        inputs = {
            "question": question,
            "context": thread_history,
            "documents": [],
            "generation": "",
        }

        logger.info(f"Processing question: {question}")
        result = asyncio.run(run_workflow(inputs))

        # 結果をSlackに送信
        send_slack_message(
            channel_id=channel_id, text=result["generation"], thread_ts=thread_ts
        )
        logger.info("Response sent successfully")

    except Exception as e:
        logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
        send_slack_message(
            channel_id=channel_id,
            text="申し訳ありません、エラーが発生しました。もう一度試してください。",
            thread_ts=thread_ts,
        )


def start_slack_bot():
    handler = SocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
    handler.start()


if __name__ == "__main__":
    # Slackbotを起動
    start_slack_bot()
