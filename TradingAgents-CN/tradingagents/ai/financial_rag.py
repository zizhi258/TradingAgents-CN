"""
Financial RAG System for TradingAgents-CN

This module implements a Retrieval-Augmented Generation (RAG) system specifically
designed for financial analysis with domain-specific knowledge base, vector embeddings,
and semantic search capabilities.
"""

import asyncio
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import pickle
from collections import defaultdict
import re

# Vector database and embeddings
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("ChromaDB not available - RAG system will use fallback storage")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Sentence Transformers not available - using fallback embedding method")

# TradingAgents imports
from tradingagents.utils.logging_init import get_logger
from tradingagents.dataflows import get_finnhub_news, get_YFin_data_window

logger = get_logger("financial_rag")


@dataclass
class FinancialDocument:
    """Financial document structure for RAG system"""
    doc_id: str
    title: str
    content: str
    doc_type: str  # "news", "research", "earnings", "filing", "market_data"
    symbol: Optional[str] = None
    sector: Optional[str] = None
    market: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    relevance_score: float = 0.0


@dataclass
class RAGQuery:
    """RAG query structure"""
    query_text: str
    query_type: str = "general"  # "general", "technical", "fundamental", "news", "risk"
    symbols: Optional[List[str]] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    doc_types: Optional[List[str]] = None
    top_k: int = 5
    relevance_threshold: float = 0.7
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResponse:
    """RAG response structure"""
    query: RAGQuery
    retrieved_documents: List[FinancialDocument]
    generated_response: str
    confidence_score: float
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FinancialEmbedding:
    """Financial domain-specific embedding system"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        
        # Financial domain keywords and weights
        self.financial_keywords = {
            'technical': ['support', 'resistance', 'trend', 'moving average', 'rsi', 'macd', 
                         'volume', 'breakout', 'momentum', 'volatility'],
            'fundamental': ['earnings', 'revenue', 'profit', 'cash flow', 'debt', 'ratio',
                           'growth', 'valuation', 'dividend', 'balance sheet'],
            'risk': ['risk', 'volatility', 'downside', 'correlation', 'var', 'drawdown',
                    'stress test', 'scenario', 'hedge', 'exposure'],
            'market': ['bull', 'bear', 'sentiment', 'market', 'sector', 'industry',
                      'economic', 'federal reserve', 'inflation', 'gdp']
        }
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize embedding model"""
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model: {self.model_name}")
            else:
                logger.warning("Using fallback embedding method")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
    
    def embed_text(self, text: str, doc_type: str = "general") -> np.ndarray:
        """
        Create embeddings with financial domain enhancement
        
        Args:
            text: Text to embed
            doc_type: Type of document for domain weighting
            
        Returns:
            np.ndarray: Embedding vector
        """
        try:
            if self.model is not None:
                # Get base embedding
                base_embedding = self.model.encode([text])[0]
                
                # Apply financial domain weighting
                enhanced_embedding = self._apply_domain_weighting(
                    text, base_embedding, doc_type
                )
                
                return enhanced_embedding
            else:
                # Fallback: simple TF-IDF-like embedding
                return self._fallback_embedding(text)
                
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return self._fallback_embedding(text)
    
    def _apply_domain_weighting(self, text: str, base_embedding: np.ndarray, 
                               doc_type: str) -> np.ndarray:
        """Apply financial domain-specific weighting to embeddings"""
        # Calculate domain relevance scores
        text_lower = text.lower()
        domain_scores = {}
        
        for domain, keywords in self.financial_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            domain_scores[domain] = score / len(keywords)  # Normalize by keyword count
        
        # Apply weighting based on document type
        weight_multiplier = 1.0
        if doc_type == 'technical' and domain_scores.get('technical', 0) > 0.1:
            weight_multiplier = 1.2
        elif doc_type == 'fundamental' and domain_scores.get('fundamental', 0) > 0.1:
            weight_multiplier = 1.2
        elif doc_type == 'news' and domain_scores.get('market', 0) > 0.1:
            weight_multiplier = 1.1
        
        # Apply subtle enhancement to preserve semantic meaning
        enhanced_embedding = base_embedding * weight_multiplier
        
        # Normalize to maintain vector properties
        return enhanced_embedding / np.linalg.norm(enhanced_embedding)
    
    def _fallback_embedding(self, text: str) -> np.ndarray:
        """Fallback embedding method using simple hashing"""
        # Simple hash-based embedding as fallback
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to numeric vector
        embedding = np.array([
            int(text_hash[i:i+2], 16) / 255.0 
            for i in range(0, min(len(text_hash), 64), 2)
        ])
        
        # Pad or truncate to fixed size
        if len(embedding) < 32:
            embedding = np.pad(embedding, (0, 32 - len(embedding)))
        else:
            embedding = embedding[:32]
        
        return embedding
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings"""
        try:
            # Cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm_product = np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            
            if norm_product == 0:
                return 0.0
            
            similarity = dot_product / norm_product
            return float(np.clip(similarity, -1.0, 1.0))
            
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0


class FinancialKnowledgeBase:
    """Financial knowledge base with vector storage"""
    
    def __init__(self, storage_path: str = "financial_kb"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize vector database
        self.vector_db = None
        self.collection = None
        self._initialize_vector_db()
        
        # Initialize embedding system
        self.embedding_system = FinancialEmbedding()
        
        # In-memory indexes for fast retrieval
        self.symbol_index: Dict[str, List[str]] = defaultdict(list)
        self.date_index: Dict[str, List[str]] = defaultdict(list)
        self.type_index: Dict[str, List[str]] = defaultdict(list)
        
        # Document storage
        self.documents: Dict[str, FinancialDocument] = {}
        
        # Load existing knowledge base
        self._load_knowledge_base()
        
        logger.info("Financial Knowledge Base initialized")
    
    def _initialize_vector_db(self):
        """Initialize ChromaDB vector database"""
        try:
            if CHROMADB_AVAILABLE:
                # Initialize persistent ChromaDB client
                db_path = str(self.storage_path / "chromadb")
                self.vector_db = chromadb.PersistentClient(
                    path=db_path,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Create or get collection
                self.collection = self.vector_db.get_or_create_collection(
                    name="financial_knowledge",
                    metadata={"description": "Financial documents and data"}
                )
                
                logger.info("ChromaDB initialized successfully")
            else:
                logger.warning("ChromaDB not available - using fallback storage")
                
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            self.vector_db = None
            self.collection = None
    
    def add_document(self, document: FinancialDocument) -> bool:
        """
        Add document to knowledge base
        
        Args:
            document: Financial document to add
            
        Returns:
            bool: Success status
        """
        try:
            # Generate embedding if not provided
            if document.embedding is None:
                document.embedding = self.embedding_system.embed_text(
                    document.content, document.doc_type
                )
            
            # Store in vector database
            if self.collection is not None:
                self.collection.add(
                    embeddings=[document.embedding.tolist()],
                    documents=[document.content],
                    metadatas=[{
                        "doc_id": document.doc_id,
                        "title": document.title,
                        "doc_type": document.doc_type,
                        "symbol": document.symbol or "",
                        "sector": document.sector or "",
                        "market": document.market or "",
                        "timestamp": document.timestamp.isoformat()
                    }],
                    ids=[document.doc_id]
                )
            
            # Store document
            self.documents[document.doc_id] = document
            
            # Update indexes
            self._update_indexes(document)
            
            logger.debug(f"Added document to knowledge base: {document.doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def query_documents(self, query: RAGQuery) -> List[FinancialDocument]:
        """
        Query documents from knowledge base
        
        Args:
            query: RAG query object
            
        Returns:
            List[FinancialDocument]: Retrieved documents
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_system.embed_text(
                query.query_text, query.query_type
            )
            
            retrieved_docs = []
            
            if self.collection is not None:
                # Query vector database
                results = self.collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=min(query.top_k * 2, 20),  # Get more results for filtering
                    include=['documents', 'metadatas', 'distances']
                )
                
                # Convert results to documents
                for i in range(len(results['ids'][0])):
                    doc_id = results['ids'][0][i]
                    if doc_id in self.documents:
                        doc = self.documents[doc_id]
                        doc.relevance_score = 1.0 - results['distances'][0][i]  # Convert distance to similarity
                        retrieved_docs.append(doc)
            else:
                # Fallback: search in-memory documents
                retrieved_docs = self._fallback_search(query, query_embedding)
            
            # Apply filters
            filtered_docs = self._apply_filters(retrieved_docs, query)
            
            # Sort by relevance and return top k
            filtered_docs.sort(key=lambda x: x.relevance_score, reverse=True)
            return filtered_docs[:query.top_k]
            
        except Exception as e:
            logger.error(f"Document query failed: {e}")
            return []
    
    def _apply_filters(self, documents: List[FinancialDocument], 
                      query: RAGQuery) -> List[FinancialDocument]:
        """Apply query filters to documents"""
        filtered = documents
        
        # Relevance threshold
        filtered = [doc for doc in filtered if doc.relevance_score >= query.relevance_threshold]
        
        # Symbol filter
        if query.symbols:
            filtered = [doc for doc in filtered 
                       if doc.symbol is None or doc.symbol in query.symbols]
        
        # Document type filter
        if query.doc_types:
            filtered = [doc for doc in filtered if doc.doc_type in query.doc_types]
        
        # Date range filter
        if query.date_range:
            start_date, end_date = query.date_range
            filtered = [doc for doc in filtered 
                       if start_date <= doc.timestamp <= end_date]
        
        return filtered
    
    def _fallback_search(self, query: RAGQuery, 
                        query_embedding: np.ndarray) -> List[FinancialDocument]:
        """Fallback search method when vector DB is not available"""
        results = []
        
        for doc in self.documents.values():
            if doc.embedding is not None:
                similarity = self.embedding_system.compute_similarity(
                    query_embedding, doc.embedding
                )
                doc.relevance_score = similarity
                results.append(doc)
        
        return results
    
    def _update_indexes(self, document: FinancialDocument):
        """Update in-memory indexes"""
        doc_id = document.doc_id
        
        # Symbol index
        if document.symbol:
            self.symbol_index[document.symbol].append(doc_id)
        
        # Date index (by day)
        date_key = document.timestamp.date().isoformat()
        self.date_index[date_key].append(doc_id)
        
        # Type index
        self.type_index[document.doc_type].append(doc_id)
    
    def ingest_news_data(self, symbol: str, days_back: int = 30) -> int:
        """
        Ingest news data for a symbol
        
        Args:
            symbol: Stock symbol
            days_back: Number of days to look back
            
        Returns:
            int: Number of documents added
        """
        try:
            news_data = get_finnhub_news(symbol, days_back=days_back)
            added_count = 0
            
            for news_item in news_data:
                doc_id = f"news_{symbol}_{news_item.get('id', hash(news_item.get('summary', '')))}"
                
                # Skip if already exists
                if doc_id in self.documents:
                    continue
                
                document = FinancialDocument(
                    doc_id=doc_id,
                    title=news_item.get('headline', 'No Title'),
                    content=news_item.get('summary', ''),
                    doc_type="news",
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(news_item.get('datetime', 0)),
                    metadata={
                        'source': news_item.get('source', ''),
                        'url': news_item.get('url', ''),
                        'category': news_item.get('category', '')
                    }
                )
                
                if self.add_document(document):
                    added_count += 1
            
            logger.info(f"Ingested {added_count} news documents for {symbol}")
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to ingest news data for {symbol}: {e}")
            return 0
    
    def ingest_market_data(self, symbol: str, start_date: str, end_date: str) -> int:
        """
        Ingest market data for technical analysis
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            int: Number of documents added
        """
        try:
            market_data = get_YFin_data_window(symbol, start_date, end_date)
            
            if market_data is None or market_data.empty:
                return 0
            
            added_count = 0
            
            # Create summary documents for different time periods
            periods = ['1D', '1W', '1M']  # Daily, Weekly, Monthly summaries
            
            for period in periods:
                if period == '1D':
                    grouped_data = market_data.tail(1)  # Last day
                elif period == '1W':
                    grouped_data = market_data.tail(5)  # Last week
                else:  # 1M
                    grouped_data = market_data.tail(22)  # Last month
                
                if grouped_data.empty:
                    continue
                
                # Create technical summary
                summary = self._create_technical_summary(symbol, grouped_data, period)
                
                doc_id = f"market_{symbol}_{period}_{end_date}"
                
                document = FinancialDocument(
                    doc_id=doc_id,
                    title=f"{symbol} {period} Technical Summary",
                    content=summary,
                    doc_type="market_data",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    metadata={
                        'period': period,
                        'data_points': len(grouped_data),
                        'price_range': {
                            'high': float(grouped_data['High'].max()),
                            'low': float(grouped_data['Low'].min()),
                            'close': float(grouped_data['Close'].iloc[-1])
                        }
                    }
                )
                
                if self.add_document(document):
                    added_count += 1
            
            logger.info(f"Ingested {added_count} market data documents for {symbol}")
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to ingest market data for {symbol}: {e}")
            return 0
    
    def _create_technical_summary(self, symbol: str, data: pd.DataFrame, 
                                 period: str) -> str:
        """Create technical analysis summary from market data"""
        try:
            latest = data.iloc[-1]
            first = data.iloc[0]
            
            # Basic metrics
            change = latest['Close'] - first['Close']
            change_pct = (change / first['Close']) * 100
            
            # Volume analysis
            avg_volume = data['Volume'].mean()
            latest_volume = latest['Volume']
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
            
            # Price action
            high = data['High'].max()
            low = data['Low'].min()
            volatility = ((high - low) / latest['Close']) * 100
            
            summary = f"""
{symbol} {period} Technical Analysis:

Price Action:
- Current Price: ${latest['Close']:.2f}
- Change: ${change:.2f} ({change_pct:.2f}%)
- Range: ${low:.2f} - ${high:.2f}
- Volatility: {volatility:.2f}%

Volume Analysis:
- Latest Volume: {latest_volume:,.0f}
- Average Volume: {avg_volume:,.0f}
- Volume Ratio: {volume_ratio:.2f}x

Market Sentiment: {'Bullish' if change > 0 else 'Bearish' if change < 0 else 'Neutral'}
Period: {period}
Data Points: {len(data)}
"""
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Failed to create technical summary: {e}")
            return f"{symbol} technical data for {period}"
    
    def _load_knowledge_base(self):
        """Load existing knowledge base from disk"""
        try:
            kb_file = self.storage_path / "knowledge_base.pkl"
            if kb_file.exists():
                with open(kb_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', {})
                    self.symbol_index = data.get('symbol_index', defaultdict(list))
                    self.date_index = data.get('date_index', defaultdict(list))
                    self.type_index = data.get('type_index', defaultdict(list))
                
                logger.info(f"Loaded {len(self.documents)} documents from knowledge base")
        except Exception as e:
            logger.warning(f"Failed to load existing knowledge base: {e}")
    
    def save_knowledge_base(self):
        """Save knowledge base to disk"""
        try:
            kb_file = self.storage_path / "knowledge_base.pkl"
            data = {
                'documents': self.documents,
                'symbol_index': dict(self.symbol_index),
                'date_index': dict(self.date_index),
                'type_index': dict(self.type_index)
            }
            
            with open(kb_file, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info("Knowledge base saved successfully")
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return {
            'total_documents': len(self.documents),
            'documents_by_type': {
                doc_type: len(doc_ids) 
                for doc_type, doc_ids in self.type_index.items()
            },
            'symbols_covered': len(self.symbol_index),
            'date_range': {
                'earliest': min(self.date_index.keys()) if self.date_index else None,
                'latest': max(self.date_index.keys()) if self.date_index else None
            },
            'storage_path': str(self.storage_path),
            'vector_db_available': self.collection is not None
        }


class FinancialRAGSystem:
    """Complete Financial RAG System"""
    
    def __init__(self, 
                 knowledge_base_path: str = "financial_kb",
                 llm_orchestrator=None):
        self.knowledge_base = FinancialKnowledgeBase(knowledge_base_path)
        self.llm_orchestrator = llm_orchestrator
        
        # RAG prompt templates
        self.prompt_templates = {
            'general': """Based on the following financial documents, please answer the question:

Question: {query}

Relevant Information:
{context}

Please provide a comprehensive answer based on the information above. If the information is insufficient, please indicate what additional data would be helpful.""",

            'technical': """As a technical analyst, analyze the following market data and answer the question:

Question: {query}

Market Data and Technical Information:
{context}

Please provide technical analysis insights including price action, trends, support/resistance levels, and trading recommendations if applicable.""",

            'fundamental': """As a fundamental analyst, analyze the following financial information and answer the question:

Question: {query}

Financial Data and Research:
{context}

Please provide fundamental analysis including valuation insights, financial health assessment, and investment recommendations based on the available data.""",

            'news': """Based on the latest news and market developments, please answer the question:

Question: {query}

Recent News and Developments:
{context}

Please provide analysis of how these developments might impact the mentioned stocks or markets, including short-term and long-term implications.""",

            'risk': """As a risk analyst, evaluate the following information and answer the question:

Question: {query}

Risk-Related Information:
{context}

Please provide risk assessment including potential downside scenarios, volatility analysis, and risk mitigation recommendations."""
        }
        
        logger.info("Financial RAG System initialized")
    
    async def query(self, 
                   query_text: str,
                   query_type: str = "general",
                   symbols: Optional[List[str]] = None,
                   agent_role: str = "fundamental_expert",
                   **kwargs) -> RAGResponse:
        """
        Execute RAG query with document retrieval and generation
        
        Args:
            query_text: Query text
            query_type: Type of query
            symbols: Relevant symbols
            agent_role: Agent role for LLM generation
            **kwargs: Additional query parameters
            
        Returns:
            RAGResponse: Complete RAG response
        """
        try:
            # Create RAG query
            rag_query = RAGQuery(
                query_text=query_text,
                query_type=query_type,
                symbols=symbols,
                **kwargs
            )
            
            # Retrieve relevant documents
            retrieved_docs = self.knowledge_base.query_documents(rag_query)
            
            if not retrieved_docs:
                logger.warning(f"No relevant documents found for query: {query_text[:50]}...")
                return RAGResponse(
                    query=rag_query,
                    retrieved_documents=[],
                    generated_response="I don't have sufficient relevant information to answer this question accurately. Please provide more context or try a different query.",
                    confidence_score=0.0,
                    sources=[],
                    metadata={'no_documents_found': True}
                )
            
            # Prepare context from retrieved documents
            context = self._prepare_context(retrieved_docs)
            
            # Generate response using LLM
            if self.llm_orchestrator:
                generated_response = await self._generate_response(
                    rag_query, context, agent_role
                )
            else:
                generated_response = self._fallback_response(rag_query, context)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(retrieved_docs, generated_response)
            
            # Extract sources
            sources = [f"{doc.title} ({doc.doc_type})" for doc in retrieved_docs]
            
            return RAGResponse(
                query=rag_query,
                retrieved_documents=retrieved_docs,
                generated_response=generated_response,
                confidence_score=confidence_score,
                sources=sources,
                metadata={
                    'num_documents_retrieved': len(retrieved_docs),
                    'avg_relevance_score': np.mean([doc.relevance_score for doc in retrieved_docs]),
                    'context_length': len(context)
                }
            )
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return RAGResponse(
                query=RAGQuery(query_text=query_text, query_type=query_type),
                retrieved_documents=[],
                generated_response=f"I apologize, but I encountered an error while processing your query: {str(e)}",
                confidence_score=0.0,
                sources=[],
                metadata={'error': str(e)}
            )
    
    def _prepare_context(self, documents: List[FinancialDocument]) -> str:
        """Prepare context string from retrieved documents"""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            # Format document information
            doc_context = f"""
Document {i}: {doc.title}
Type: {doc.doc_type.replace('_', ' ').title()}
{f"Symbol: {doc.symbol}" if doc.symbol else ""}
Date: {doc.timestamp.strftime('%Y-%m-%d')}
Relevance: {doc.relevance_score:.2f}

Content:
{doc.content}
"""
            context_parts.append(doc_context.strip())
        
        return "\n\n" + "\n\n".join(context_parts)
    
    async def _generate_response(self, 
                               query: RAGQuery,
                               context: str,
                               agent_role: str) -> str:
        """Generate response using LLM orchestrator"""
        try:
            # Select appropriate prompt template
            template = self.prompt_templates.get(query.query_type, self.prompt_templates['general'])
            
            # Format prompt
            prompt = template.format(query=query.query_text, context=context)
            
            # Execute with LLM orchestrator
            result = await self.llm_orchestrator.execute_task(
                agent_role=agent_role,
                task_prompt=prompt,
                task_type=query.query_type,
                context={
                    'rag_enhanced': True,
                    'symbols': query.symbols,
                    'doc_count': len(query.context.get('retrieved_docs', [])),
                    'query_type': query.query_type
                }
            )
            
            if result.success:
                return result.result
            else:
                return f"I encountered an issue generating a response: {result.error_message}"
                
        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return f"I apologize, but I couldn't generate a proper response due to a technical issue: {str(e)}"
    
    def _fallback_response(self, query: RAGQuery, context: str) -> str:
        """Fallback response when LLM orchestrator is not available"""
        return f"""Based on the available financial documents, here's the relevant information for your query: "{query.query_text}"

{context}

Note: This is a document-based response. For more detailed analysis, please ensure the AI analysis system is properly configured."""
    
    def _calculate_confidence(self, documents: List[FinancialDocument], 
                            response: str) -> float:
        """Calculate confidence score for the response"""
        if not documents:
            return 0.0
        
        # Base confidence from document relevance
        avg_relevance = np.mean([doc.relevance_score for doc in documents])
        
        # Adjust based on response quality indicators
        response_lower = response.lower()
        
        # Positive indicators
        confidence_boost = 0.0
        if any(phrase in response_lower for phrase in ['based on', 'according to', 'data shows']):
            confidence_boost += 0.1
        
        if len(response) > 200:  # Detailed response
            confidence_boost += 0.05
        
        # Negative indicators
        confidence_penalty = 0.0
        if any(phrase in response_lower for phrase in ['insufficient', 'unclear', 'unable to']):
            confidence_penalty += 0.2
        
        # Calculate final confidence
        confidence = avg_relevance + confidence_boost - confidence_penalty
        return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    
    def ingest_symbol_data(self, symbol: str, 
                          include_news: bool = True,
                          include_market_data: bool = True,
                          days_back: int = 30) -> Dict[str, int]:
        """
        Ingest comprehensive data for a symbol
        
        Args:
            symbol: Stock symbol
            include_news: Whether to include news data
            include_market_data: Whether to include market data
            days_back: Number of days to look back
            
        Returns:
            Dict[str, int]: Ingestion statistics
        """
        stats = {'news': 0, 'market_data': 0}
        
        if include_news:
            stats['news'] = self.knowledge_base.ingest_news_data(symbol, days_back)
        
        if include_market_data:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            stats['market_data'] = self.knowledge_base.ingest_market_data(
                symbol, start_date, end_date
            )
        
        # Save knowledge base after ingestion
        self.knowledge_base.save_knowledge_base()
        
        logger.info(f"Ingested data for {symbol}: {stats}")
        return stats
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        kb_stats = self.knowledge_base.get_stats()
        
        return {
            'knowledge_base': kb_stats,
            'rag_system': {
                'prompt_templates': len(self.prompt_templates),
                'llm_orchestrator_available': self.llm_orchestrator is not None,
                'embedding_system_available': self.knowledge_base.embedding_system.model is not None,
                'vector_db_available': self.knowledge_base.collection is not None
            }
        }