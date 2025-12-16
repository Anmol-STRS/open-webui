"""
Unit tests for RAG reranker
"""

import pytest
from open_webui.services.rag_reranker import LexicalReranker, RAGChunk, RAGTransparency


@pytest.fixture
def sample_chunks():
    """Create sample RAG chunks"""
    return [
        RAGChunk(
            doc_id='doc1',
            doc_title='Python Programming Guide',
            chunk_id='chunk1',
            content='Python is a high-level programming language. It supports multiple programming paradigms including object-oriented and functional programming.',
            vector_score=0.85
        ),
        RAGChunk(
            doc_id='doc2',
            doc_title='JavaScript Basics',
            chunk_id='chunk2',
            content='JavaScript is a scripting language primarily used for web development. It runs in browsers and on servers with Node.js.',
            vector_score=0.75
        ),
        RAGChunk(
            doc_id='doc3',
            doc_title='Python vs JavaScript',
            chunk_id='chunk3',
            content='Python and JavaScript are both popular programming languages. Python is often used for data science and machine learning.',
            vector_score=0.80
        )
    ]


def test_lexical_reranker_basic(sample_chunks):
    """Test basic reranking functionality"""
    reranker = LexicalReranker()
    query = "What is Python programming?"

    result = reranker.rerank(query, sample_chunks, top_k=3)

    assert len(result.ranked_chunks) == 3
    assert result.reranker_type == "lexical_bm25"
    assert result.rerank_latency_ms >= 0


def test_lexical_reranker_improves_ranking(sample_chunks):
    """Test that reranking changes order based on lexical relevance"""
    reranker = LexicalReranker(vector_weight=0.2, lexical_weight=0.8)
    query = "Python programming language features"

    result = reranker.rerank(query, sample_chunks, top_k=3)

    # First result should have "Python" and "programming" prominently
    top_chunk = result.ranked_chunks[0]
    assert 'python' in top_chunk.chunk.content.lower()

    # Check that rerank scores are different from vector scores
    has_different_scores = any(
        abs(r.rerank_score - r.vector_score) > 0.01
        for r in result.ranked_chunks
    )
    assert has_different_scores


def test_lexical_reranker_top_k_limit(sample_chunks):
    """Test top_k limiting"""
    reranker = LexicalReranker()
    query = "programming"

    result = reranker.rerank(query, sample_chunks, top_k=2)

    assert len(result.ranked_chunks) == 2


def test_lexical_reranker_empty_chunks():
    """Test handling of empty chunks"""
    reranker = LexicalReranker()
    query = "test"

    result = reranker.rerank(query, [], top_k=5)

    assert len(result.ranked_chunks) == 0
    assert result.rerank_latency_ms == 0


def test_tokenization():
    """Test tokenization"""
    reranker = LexicalReranker()
    text = "Hello, World! This is a test."

    tokens = reranker._tokenize(text)

    assert 'hello' in tokens
    assert 'world' in tokens
    assert 'test' in tokens
    assert ',' not in tokens  # Punctuation should be removed


def test_bm25_scoring(sample_chunks):
    """Test BM25 score calculation"""
    reranker = LexicalReranker()
    query_tokens = reranker._tokenize("Python programming")

    # Calculate IDF
    idf_scores = reranker._calculate_idf(query_tokens, sample_chunks)

    # Both terms should have IDF scores
    assert 'python' in idf_scores
    assert 'programming' in idf_scores

    # "Python" appears in 2 docs, "programming" in all 3
    # So "Python" should have higher IDF (more discriminative)
    assert idf_scores['python'] > idf_scores['programming']


def test_rag_transparency_retrieve_and_rerank(sample_chunks):
    """Test RAG transparency retrieve and rerank"""
    rag = RAGTransparency()
    query = "Python programming"

    selected, result = rag.retrieve_and_rerank(
        query=query,
        retrieved_chunks=sample_chunks,
        top_k=2
    )

    assert len(selected) == 2
    assert result.reranker_type == "lexical_bm25"


def test_rag_transparency_format_sources(sample_chunks):
    """Test formatting sources for UI"""
    reranker = LexicalReranker()
    query = "Python"
    result = reranker.rerank(query, sample_chunks, top_k=2)

    rag = RAGTransparency()
    sources = rag.format_sources_for_ui(result.ranked_chunks)

    assert len(sources) == 2
    assert sources[0]['rank'] == 1
    assert 'doc_id' in sources[0]
    assert 'preview' in sources[0]
    assert 'vector_score' in sources[0]
    assert 'rerank_score' in sources[0]
    assert 'final_score' in sources[0]


def test_rag_transparency_inject_system_strategy(sample_chunks):
    """Test injecting chunks as system message"""
    reranker = LexicalReranker()
    query = "Python"
    result = reranker.rerank(query, sample_chunks, top_k=1)

    rag = RAGTransparency()
    messages = [
        {'role': 'user', 'content': 'Tell me about Python'}
    ]

    modified = rag.inject_chunks_into_prompt(
        messages=messages,
        ranked_chunks=result.ranked_chunks,
        injection_strategy='system'
    )

    # Should have system message prepended
    assert len(modified) == 2
    assert modified[0]['role'] == 'system'
    assert 'knowledge base' in modified[0]['content'].lower()


def test_rag_transparency_inject_user_strategy(sample_chunks):
    """Test injecting chunks into user message"""
    reranker = LexicalReranker()
    query = "Python"
    result = reranker.rerank(query, sample_chunks, top_k=1)

    rag = RAGTransparency()
    messages = [
        {'role': 'user', 'content': 'Tell me about Python'}
    ]

    modified = rag.inject_chunks_into_prompt(
        messages=messages,
        ranked_chunks=result.ranked_chunks,
        injection_strategy='user'
    )

    # Should have same number of messages, but user content modified
    assert len(modified) == 1
    assert 'knowledge base' in modified[0]['content'].lower()
    assert 'Tell me about Python' in modified[0]['content']


def test_rag_transparency_empty_chunks():
    """Test handling empty chunks in transparency"""
    rag = RAGTransparency()
    messages = [{'role': 'user', 'content': 'test'}]

    modified = rag.inject_chunks_into_prompt(
        messages=messages,
        ranked_chunks=[],
        injection_strategy='system'
    )

    # Should return original messages unchanged
    assert modified == messages


def test_preview_generation(sample_chunks):
    """Test preview generation"""
    reranker = LexicalReranker()
    query = "test"

    # Create a chunk with very long content
    long_chunk = RAGChunk(
        doc_id='long',
        chunk_id='long1',
        content='a' * 1000,  # 1000 chars
        vector_score=0.9
    )

    result = reranker.rerank(query, [long_chunk], top_k=1)

    # Preview should be truncated
    preview = result.ranked_chunks[0].preview
    assert len(preview) <= 403  # 400 chars + "..."
    assert preview.endswith('...')


def test_combined_scoring_weights():
    """Test that scoring weights affect final scores"""
    chunks = [
        RAGChunk(
            doc_id='d1',
            chunk_id='c1',
            content='exact query match here',
            vector_score=0.5  # Low vector score
        ),
        RAGChunk(
            doc_id='d2',
            chunk_id='c2',
            content='completely different text',
            vector_score=0.9  # High vector score
        )
    ]

    query = "exact query match"

    # With high lexical weight, first chunk should rank higher
    reranker_lexical = LexicalReranker(vector_weight=0.1, lexical_weight=0.9)
    result_lexical = reranker_lexical.rerank(query, chunks, top_k=2)

    # First should be the lexical match
    assert result_lexical.ranked_chunks[0].chunk.doc_id == 'd1'

    # With high vector weight, second chunk should rank higher
    reranker_vector = LexicalReranker(vector_weight=0.9, lexical_weight=0.1)
    result_vector = reranker_vector.rerank(query, chunks, top_k=2)

    # First should be the high vector score
    assert result_vector.ranked_chunks[0].chunk.doc_id == 'd2'
