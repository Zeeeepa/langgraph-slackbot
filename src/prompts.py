from langchain_core.prompts import ChatPromptTemplate

# 質問ルーティング用プロンプト
ROUTE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたはユーザーの質問をベクターストアまたはウェブ検索にルーティングする専門家です。
ベクターストアにはエージェント、プロンプトエンジニアリング、アドバーサリアルアタックに関連する文書が含まれています。
これらのトピックに関する質問にはベクターストアを使用し、それ以外の場合はウェブ検索を使用してください。"""),
    ("human", "{question}")
])

# ドキュメント評価用プロンプト
GRADE_DOCUMENTS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたは、ユーザーの質問に対して取得されたドキュメントの関連性を評価する採点者です。
ドキュメントにユーザーの質問に関連するキーワードや意味が含まれている場合、それを関連性があると評価してください。
目的は明らかに誤った取得を排除することです。厳密なテストである必要はありません。
ドキュメントが質問に関連しているかどうかを示すために、バイナリスコア「yes」または「no」を与えてください。"""),
    ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")
])

# 回答生成用プロンプト
GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたはSlackbotのアシスタントです。以下の会話履歴を参考に、ユーザーの質問に答えてください。
    
会話履歴:
{context}

回答の際は以下の点に注意してください:
- 会話の流れを考慮して自然な回答をすること
- 既に会話で触れられた内容は繰り返さないこと
- 新しい情報を追加する場合は、会話の流れに沿って説明すること"""),
    ("human", "Question: {question}")
])

# 質問リライト用プロンプト
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたは、入力された質問をベクトルストア検索に最適化されたより良いバージョンに変換する質問リライターです。
質問を見て、質問者の意図/意味について推論してより良いベクトル検索の為の質問を作成してください。"""),
    ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")
])

# 幻覚評価用プロンプト
HALLUCINATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたは、LLMの生成が取得された事実のセットに基づいているか/サポートされているかを評価する採点者です。
バイナリスコア「yes」または「no」を与えてください。「yes」は、回答が事実のセットに基づいている/サポートされていることを意味します。"""),
    ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}")
])

# 回答評価用プロンプト
ANSWER_GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたは、回答が質問に対処しているか/解決しているかを評価する採点者です。
バイナリスコア「yes」または「no」を与えてください。「yes」は、回答が質問を解決していることを意味します。"""),
    ("human", "User question: \n\n {question} \n\n LLM generation: {generation}")
])