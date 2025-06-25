import os
import pandas as pd
import openai
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, HnswParameters, VectorSearchProfile
)
import requests
import json
import time
from typing import List, Dict, Any

# ローカルで動かす時用
from dotenv import load_dotenv

load_dotenv()

# 環境変数からAzureのAPIキーを取得
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_GPT_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_GPT_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

# OpenAI API クライアント設定
openai.api_key = AZURE_OPENAI_API_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2023-07-01-preview"

# パターン別のSearchClientを取得する関数
def get_search_client_for_pattern(pattern):
    """パターンに応じたSearchClientを返す"""
    # 確認済みの実際のインデックス名を使用
    index_names = {
        "A": "science_tokyo_pattern_a",
        "B": "science_tokyo_pattern_b", 
        "C": "science_tokyo_pattern_c"
    }
    
    index_name = index_names.get(pattern.upper())
    if not index_name:
        raise ValueError(f"Invalid pattern: {pattern}")
    
    return SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
    )

# 埋め込みを取得する関数
def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
    )
    return response.data[0].embedding

def get_openai_response(messages):
    """
    Azure OpenAI Serviceにチャットメッセージを送信し、応答を取得する関数。

    Parameters:
    messages (list): チャットメッセージのリスト。各メッセージは辞書で、'role'と'content'を含む。

    Returns:
    str: アシスタントからの応答メッセージ。
    """
    # 環境変数からAPIキーとエンドポイントを取得
    api_key = os.getenv("AZURE_OPENAI_GPT_API_KEY")
    api_base = os.getenv("AZURE_OPENAI_GPT_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT_NAME")  # デプロイメント名を環境変数から取得

    # エンドポイントURLの構築
    api_version = "2024-08-01-preview"  # 使用するAPIバージョンを指定
    endpoint = f"{api_base}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

    # ヘッダーの設定
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    # リクエストデータの作成
    data = {
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 300
    }

    # POSTリクエストの送信
    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    # レスポンスの処理
    if response.status_code == 200:
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    else:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

def deduplicate_researchers(raw_results, top_k=10):
    """
    研究者IDで重複を除去し、各研究者の最高スコアの記録のみを保持
    
    Parameters:
    raw_results: Azure Searchからの生の結果
    top_k: 返すユニーク研究者の数
    
    Returns:
    list: 重複除去された研究者リスト
    """
    researcher_dict = {}
    
    # 各結果を処理し、研究者IDごとに最高スコアの記録を保持
    for result in raw_results:
        researcher_id = result["researcher_id"]
        current_score = result.get('@search.score', 0)
        
        # この研究者が初めて出現するか、より高いスコアを持つ場合
        if (researcher_id not in researcher_dict or 
            current_score > researcher_dict[researcher_id].get('@search.score', 0)):
            researcher_dict[researcher_id] = result
    
    # スコア順にソートし、上位top_k件を返す
    unique_researchers = list(researcher_dict.values())
    unique_researchers.sort(key=lambda x: x.get('@search.score', 0), reverse=True)
    
    return unique_researchers[:top_k]

def merge_researcher_information(results_for_researcher):
    """
    同一研究者の複数レコードから情報をマージ（オプション機能）
    
    Parameters:
    results_for_researcher: 同一研究者の複数レコードのリスト
    
    Returns:
    dict: マージされた研究者情報
    """
    if not results_for_researcher:
        return None
    
    # 最高スコアのレコードをベースとする
    base_record = max(results_for_researcher, key=lambda x: x.get('@search.score', 0))
    
    # キーワードや研究プロジェクトなどをマージ（必要に応じて）
    merged_keywords = set()
    merged_projects = set()
    
    for record in results_for_researcher:
        # キーワードのマージ
        if record.get("keywords_pi"):
            keywords = record["keywords_pi"].split(";") if ";" in record["keywords_pi"] else [record["keywords_pi"]]
            merged_keywords.update([k.strip() for k in keywords if k.strip()])
        
        # 研究プロジェクトのマージ（Pattern Bの場合）
        if record.get("research_project_title"):
            merged_projects.add(record["research_project_title"])
    
    # ベースレコードを更新
    if merged_keywords:
        base_record["keywords_pi"] = "; ".join(list(merged_keywords)[:10])  # 最大10個のキーワード
    
    return base_record

# パターンA: 研究者キーワードのみ検索（重複除去付き）
def search_researchers_pattern_a(category, title, description, university="東京科学大学", top_k=10):
    """
    Pattern A: 研究者キーワードのみを使用した検索（KAKENデータのみ）
    重複する研究者を除去し、ユニークな研究者のみを返す
    """
    try:
        start_time = time.time()
        query_text = f"{category} {title} {description}"
        embedding = get_embedding(query_text)
        
        # Pattern A専用のSearchClientを取得
        search_client = get_search_client_for_pattern("A")
        
        # より多くの結果を取得してから重複除去（top_k * 3 で十分なユニーク結果を確保）
        search_k = min(top_k * 3, 50)  # 最大50件まで
        
        results = search_client.search(
            search_text=None,
            vector_queries=[
                VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=search_k,
                    fields="science_tokyo_pattern_a"  # Pattern A vector field
                )
            ],
            select=["id", "researcher_id", "researcher_affiliation_current", "researcher_position_current", "keywords_pi"],
            filter=f"search.ismatch('{university}', 'researcher_affiliation_current')"
        )

        # 生の結果を重複除去
        raw_results = list(results)
        unique_results = deduplicate_researchers(raw_results, top_k)
        
        search_results = []
        for result in unique_results:
            explanation = generate_explanation_pattern_a(query_text, result)
            search_results.append({
                "researcher_id": result["researcher_id"],
                "name": f"研究者ID: {result['researcher_id']}",
                "name_alphabet": "",
                "university": university,
                "affiliation": result["researcher_affiliation_current"],
                "position": result["researcher_position_current"],
                "research_field": "",
                "keywords": result["keywords_pi"],
                "explanation": explanation,
                "score": result.get('@search.score', 0),
                "pattern": "A"
            })
        
        search_time = time.time() - start_time
        return {
            "results": search_results,
            "search_time": search_time,
            "pattern": "A",
            "pattern_description": "研究者キーワードのみ（KAKEN）- 重複除去済み"
        }
    
    except Exception as e:
        print("search_researchers_pattern_a内で例外発生:", e)
        raise

# パターンB: 研究者キーワード + 研究課題（重複除去付き）
def search_researchers_pattern_b(category, title, description, university="東京科学大学", top_k=10):
    """
    Pattern B: 研究者キーワード + 研究課題を使用した検索（KAKENデータ拡張）
    重複する研究者を除去し、ユニークな研究者のみを返す
    """
    try:
        start_time = time.time()
        query_text = f"{category} {title} {description}"
        embedding = get_embedding(query_text)
        
        # Pattern B専用のSearchClientを取得
        search_client = get_search_client_for_pattern("B")
        
        # より多くの結果を取得してから重複除去
        search_k = min(top_k * 3, 50)
        
        results = search_client.search(
            search_text=None,
            vector_queries=[
                VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=search_k,
                    fields="science_tokyo_pattern_b"  # Pattern B vector field
                )
            ],
            select=["id", "researcher_id", "researcher_affiliation_current", "researcher_position_current", "keywords_pi", "research_project_title", "research_project_details", "research_achievement"],
            filter=f"search.ismatch('{university}', 'researcher_affiliation_current')"
        )

        # 生の結果を重複除去
        raw_results = list(results)
        unique_results = deduplicate_researchers(raw_results, top_k)
        
        search_results = []
        for result in unique_results:
            explanation = generate_explanation_pattern_b(query_text, result)
            search_results.append({
                "researcher_id": result["researcher_id"],
                "name": f"研究者ID: {result['researcher_id']}",
                "name_alphabet": "",
                "university": university,
                "affiliation": result["researcher_affiliation_current"],
                "position": result["researcher_position_current"],
                "research_field": "",
                "keywords": result["keywords_pi"],
                "research_projects": f"{result.get('research_project_title', '')} | {result.get('research_project_details', '')} | {result.get('research_achievement', '')}",
                "explanation": explanation,
                "score": result.get('@search.score', 0),
                "pattern": "B"
            })
        
        search_time = time.time() - start_time
        return {
            "results": search_results,
            "search_time": search_time,
            "pattern": "B", 
            "pattern_description": "研究者キーワード + 研究課題（KAKEN拡張）- 重複除去済み"
        }
    
    except Exception as e:
        print("search_researchers_pattern_b内で例外発生:", e)
        raise

# パターンC: 研究者キーワード + 論文（タイトル・概要）（重複除去付き）
def search_researchers_pattern_c(category, title, description, university="東京科学大学", top_k=10):
    """
    Pattern C: 研究者キーワード + 論文（タイトル・概要）を使用した検索（KAKEN + researchmap）
    重複する研究者を除去し、ユニークな研究者のみを返す
    """
    try:
        start_time = time.time()
        query_text = f"{category} {title} {description}"
        embedding = get_embedding(query_text)
        
        # Pattern C専用のSearchClientを取得
        search_client = get_search_client_for_pattern("C")
        
        # より多くの結果を取得してから重複除去
        search_k = min(top_k * 3, 50)
        
        results = search_client.search(
            search_text=None,
            vector_queries=[
                VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=search_k,
                    fields="science_tokyo_pattern_c"  # Pattern C vector field
                )
            ],
            select=["id", "researcher_id", "researcher_affiliation_current", "researcher_position_current", "keywords_pi", "publication_title", "description_publication"],
            filter=f"search.ismatch('{university}', 'researcher_affiliation_current')"
        )

        # 生の結果を重複除去
        raw_results = list(results)
        unique_results = deduplicate_researchers(raw_results, top_k)
        
        search_results = []
        for result in unique_results:
            explanation = generate_explanation_pattern_c(query_text, result)
            search_results.append({
                "researcher_id": result["researcher_id"],
                "name": f"研究者ID: {result['researcher_id']}",
                "name_alphabet": "",
                "university": university,
                "affiliation": result["researcher_affiliation_current"],
                "position": result["researcher_position_current"],
                "research_field": "",
                "keywords": result["keywords_pi"],
                "publications": f"{result.get('publication_title', '')} | {result.get('description_publication', '')}",
                "explanation": explanation,
                "score": result.get('@search.score', 0),
                "pattern": "C"
            })
        
        search_time = time.time() - start_time
        return {
            "results": search_results,
            "search_time": search_time,
            "pattern": "C",
            "pattern_description": "研究者キーワード + 論文（KAKEN + researchmap）- 重複除去済み"
        }
    
    except Exception as e:
        print("search_researchers_pattern_c内で例外発生:", e)
        raise

# 全パターン比較検索
def compare_all_patterns(category, title, description, university="東京科学大学", top_k=10):
    """
    3つのパターンすべてを実行して結果を比較
    各パターンで重複除去を実行
    """
    try:
        start_time = time.time()
        
        # 全パターンを並行実行
        pattern_a_results = search_researchers_pattern_a(category, title, description, university, top_k)
        pattern_b_results = search_researchers_pattern_b(category, title, description, university, top_k)
        pattern_c_results = search_researchers_pattern_c(category, title, description, university, top_k)
        
        total_time = time.time() - start_time
        
        return {
            "pattern_a": pattern_a_results,
            "pattern_b": pattern_b_results,
            "pattern_c": pattern_c_results,
            "total_comparison_time": total_time,
            "query_info": {
                "category": category,
                "title": title,
                "description": description,
                "university": university,
                "top_k": top_k
            }
        }
    
    except Exception as e:
        print("compare_all_patterns内で例外発生:", e)
        raise

# パターン別の説明生成関数
def generate_explanation_pattern_a(query_text, researcher):
    """Pattern A用の説明生成（基本情報のみ）"""
    prompt = f"""
    依頼内容: {query_text}
    研究者ID: {researcher["researcher_id"]}
    所属: {researcher["researcher_affiliation_current"]}
    職位: {researcher["researcher_position_current"]}
    キーワード: {researcher["keywords_pi"]}

    【Pattern A検索】研究者の基本情報とキーワードのみを基に、なぜこの研究者が依頼内容に適しているのかを簡潔に説明してください。
    """
    messages = [
        {"role": "system", "content": "あなたは研究者マッチングの説明を行うアシスタントです。Pattern A（基本情報のみ）での検索結果を説明します。"},
        {"role": "user", "content": prompt}
    ]
    return get_openai_response(messages)

def generate_explanation_pattern_b(query_text, researcher):
    """Pattern B用の説明生成（研究課題情報を含む）"""
    prompt = f"""
    依頼内容: {query_text}
    研究者ID: {researcher["researcher_id"]}
    所属: {researcher["researcher_affiliation_current"]}
    職位: {researcher["researcher_position_current"]}
    キーワード: {researcher["keywords_pi"]}
    研究課題タイトル: {researcher.get("research_project_title", "")}
    研究課題詳細: {researcher.get("research_project_details", "")}
    研究成果: {researcher.get("research_achievement", "")}

    【Pattern B検索】研究者の基本情報、キーワード、および研究課題を基に、なぜこの研究者が依頼内容に適しているのかを説明してください。
    """
    messages = [
        {"role": "system", "content": "あなたは研究者マッチングの説明を行うアシスタントです。Pattern B（研究課題を含む）での検索結果を説明します。"},
        {"role": "user", "content": prompt}
    ]
    return get_openai_response(messages)

def generate_explanation_pattern_c(query_text, researcher):
    """Pattern C用の説明生成（論文情報を含む）"""
    prompt = f"""
    依頼内容: {query_text}
    研究者ID: {researcher["researcher_id"]}
    所属: {researcher["researcher_affiliation_current"]}
    職位: {researcher["researcher_position_current"]}
    キーワード: {researcher["keywords_pi"]}
    論文タイトル: {researcher.get("publication_title", "")}
    論文概要: {researcher.get("description_publication", "")}

    【Pattern C検索】研究者の基本情報、キーワード、および論文情報を基に、なぜこの研究者が依頼内容に適しているのかを詳細に説明してください。
    """
    messages = [
        {"role": "system", "content": "あなたは研究者マッチングの説明を行うアシスタントです。Pattern C（論文情報を含む）での検索結果を説明します。"},
        {"role": "user", "content": prompt}
    ]
    return get_openai_response(messages)

# 既存の関数（後方互換性のため）
def search_researchers(category, title, description, university="東京科学大学", top_k=10):
    """
    既存のsearch_researchers関数（Pattern Aと同じ動作）
    重複除去付き
    """
    result = search_researchers_pattern_a(category, title, description, university, top_k)
    return result["results"]  # 既存の形式で返す

def generate_explanation(query_text, researcher):
    """
    既存のgenerate_explanation関数
    """
    return generate_explanation_pattern_a(query_text, researcher)