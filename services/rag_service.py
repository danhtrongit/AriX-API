# -*- coding: utf-8 -*-
import requests
import re
from qdrant_client import QdrantClient, models
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RAGService:
    """
    RAG (Retrieval Augmented Generation) Service for financial data queries
    """
    
    def __init__(self, config):
        self.openai_api_key = config.OPENAI_API_KEY
        self.openai_base = config.OPENAI_BASE
        self.embedding_model = config.EMBEDDING_MODEL
        self.chat_model = config.CHAT_MODEL
        self.qdrant_host = config.QDRANT_HOST
        self.qdrant_port = config.QDRANT_PORT
        self.qdrant_collection = config.QDRANT_COLLECTION
        
        # Initialize Qdrant client
        try:
            # Hỗ trợ cả local (host+port) và remote (URL)
            if self.qdrant_host.startswith(('http://', 'https://')):
                # Parse URL to extract host/port/scheme
                from urllib.parse import urlparse
                parsed = urlparse(self.qdrant_host)
                host = parsed.hostname or parsed.netloc
                port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                use_https = (parsed.scheme == 'https')
                
                self.qdrant = QdrantClient(
                    host=host,
                    port=port,
                    https=use_https,
                    api_key=config.QDRANT_API_KEY,
                    timeout=60,
                    prefer_grpc=False
                )
                logger.info(f"Connected to Qdrant: {host}:{port} (https={use_https})")
            else:
                self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
                logger.info(f"Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
    
    def get_embedding(self, text: str):
        """Get text embedding from OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {"model": self.embedding_model, "input": text}
            resp = requests.post(f"{self.openai_base}/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def ask_openai(self, prompt: str):
        """Ask OpenAI chat completion"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": "Bạn là chuyên gia tài chính Việt Nam."},
                    {"role": "user", "content": prompt}
                ]
            }
            resp = requests.post(f"{self.openai_base}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error asking OpenAI: {e}")
            raise
    
    def extract_period(self, text):
        """Extract period (year, quarter) from text"""
        match = re.search(r'\(Q(\d+)/(\d+)\)', text)
        if match:
            return (int(match.group(2)), int(match.group(1)))  # (year, quarter)
        return (0, 0)
    
    def query_financials(self, question: str, ticker: str = "VIC"):
        """
        Query financial data using RAG
        
        Args:
            question: User's question
            ticker: Stock ticker symbol
            
        Returns:
            dict: Response with answer and metadata
        """
        try:
            # Kiểm tra ý định câu hỏi
            is_latest_request = any(keyword in question.lower() for keyword in 
                ['mới nhất', 'gần đây', 'hiện tại', 'năm nay', 'latest', 'recent', 'current'])
            
            is_annual_request = any(keyword in question.lower() for keyword in 
                ['năm', 'year', 'annual', 'hàng năm', 'yearly'])
            
            is_quarterly_request = any(keyword in question.lower() for keyword in 
                ['quý', 'quarter', 'quarterly'])
            
            # Log query intent
            intent_type = []
            if is_latest_request:
                intent_type.append("latest")
            if is_annual_request:
                intent_type.append("annual")
            if is_quarterly_request:
                intent_type.append("quarterly")
            
            logger.info(f"📋 RAG Query Intent: {', '.join(intent_type) if intent_type else 'general'}")
            
            # Generate embedding for question
            q_vector = self.get_embedding(question)
            
            # Retrieve relevant documents
            if is_latest_request:
                logger.info(f"🔍 RAG Strategy: Time-based retrieval (latest data)")
                # Get all statistics-financial points
                all_points = self.qdrant.scroll(
                    collection_name=self.qdrant_collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(key="ticker", match=models.MatchValue(value=ticker)),
                            models.FieldCondition(key="section", match=models.MatchValue(value="statistics-financial"))
                        ]
                    ),
                    limit=50,
                    with_payload=True,
                    with_vectors=False
                )[0]
                
                sorted_points = sorted(all_points, key=lambda p: self.extract_period(p.payload["text"]), reverse=True)
                
                # Filter based on question type
                if is_annual_request:
                    q5_points = [p for p in sorted_points if 'Q5/' in p.payload['text']]
                    recent_points = q5_points[:5]  # 5 years
                    logger.info(f"📅 RAG Data Type: Annual (Q5) - {len(recent_points)} years")
                    context = "\n\n".join([f"[Năm {self.extract_period(p.payload['text'])[0]}]\n{p.payload['text']}" 
                                          for p in recent_points])
                elif is_quarterly_request:
                    quarterly_points = [p for p in sorted_points if 'Q5/' not in p.payload['text']]
                    recent_points = quarterly_points[:8]  # 8 quarters
                    logger.info(f"📅 RAG Data Type: Quarterly (Q1-Q4) - {len(recent_points)} quarters")
                    context = "\n\n".join([f"[{self.extract_period(p.payload['text'])}]\n{p.payload['text']}" 
                                          for p in recent_points])
                else:
                    # Mixed: Q5 + quarterly
                    q5_points = [p for p in sorted_points if 'Q5/' in p.payload['text']][:3]
                    quarterly_points = [p for p in sorted_points if 'Q5/' not in p.payload['text']][:6]
                    recent_points = q5_points + quarterly_points
                    logger.info(f"📅 RAG Data Type: Mixed - {len(q5_points)} years + {len(quarterly_points)} quarters")
                    context = "\n\n".join([f"[{self.extract_period(p.payload['text'])}]\n{p.payload['text']}" 
                                          for p in recent_points])
            else:
                logger.info(f"🔍 RAG Strategy: Semantic search")
                # Semantic search
                hits = self.qdrant.search(
                    collection_name=self.qdrant_collection,
                    query_vector=q_vector,
                    limit=15,
                    query_filter=models.Filter(
                        must=[models.FieldCondition(key="ticker", match=models.MatchValue(value=ticker))]
                    )
                )
                
                sorted_hits = sorted(hits, key=lambda h: self.extract_period(h.payload["text"]), reverse=True)
                logger.info(f"📊 Found {len(sorted_hits)} relevant documents via semantic search")
                context = "\n\n".join([f"[Điểm {i+1}]\n{h.payload['text']}" for i, h in enumerate(sorted_hits)])
                recent_points = sorted_hits
            
            # Generate prompt
            data_type_note = ""
            if is_annual_request:
                data_type_note = "\nLƯU Ý: Dữ liệu Q5 là tổng hợp THEO NĂM (annual summary), sử dụng khi trả lời về năm."
            elif is_quarterly_request:
                data_type_note = "\nLƯU Ý: Dữ liệu Q1-Q4 là theo QUÝ (quarterly), sử dụng khi trả lời về quý."
            
            prompt = f"""Bạn là chuyên gia phân tích tài chính. Dưới đây là dữ liệu tài chính THỰC TẾ của công ty {ticker}:

{context}

Câu hỏi: {question}{data_type_note}

YÊU CẦU QUAN TRỌNG:
- CHỈ sử dụng dữ liệu được cung cấp ở trên, KHÔNG tự bịa số liệu
- Nếu dữ liệu không đủ để trả lời, hãy nói rõ "Không có đủ dữ liệu"
- Khi trả lời về NĂM, dùng dữ liệu Q5 (tổng hợp cả năm)
- Khi trả lời về QUÝ, dùng dữ liệu Q1-Q4
- Trích dẫn chính xác kỳ báo cáo (Năm 2024, Q1/2024...)
- Ưu tiên dữ liệu mới nhất khi trả lời

Trả lời:"""
            
            # Get answer from OpenAI
            logger.info(f"🤖 Generating answer with OpenAI ({self.chat_model})...")
            answer = self.ask_openai(prompt)
            
            context_count = len(recent_points) if 'recent_points' in locals() else 0
            logger.info(f"✅ RAG answer generated - Used {context_count} context points")
            
            return {
                "success": True,
                "ticker": ticker,
                "question": question,
                "answer": answer,
                "context_used": context_count
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Không thể truy vấn dữ liệu tài chính. Vui lòng thử lại sau."
            }

