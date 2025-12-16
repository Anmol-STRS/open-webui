#!/usr/bin/env python3
"""
Verification script for multi-provider implementation

This script checks that all components are properly installed and configured.
"""

import sys
import os
from pathlib import Path


def check_file_exists(filepath, description):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - File not found: {filepath}")
        return False


def check_imports():
    """Check that all modules can be imported"""
    print("\n=== Checking Module Imports ===\n")

    modules = [
        ("open_webui.services.model_registry", "Model Registry"),
        ("open_webui.services.provider_adapters", "Provider Adapters"),
        ("open_webui.services.model_router", "Model Router"),
        ("open_webui.services.fallback_handler", "Fallback Handler"),
        ("open_webui.services.rag_reranker", "RAG Reranker"),
        ("open_webui.services.completion_handler", "Completion Handler"),
        ("open_webui.models.observability", "Observability Models"),
        ("open_webui.routers.observability", "Observability Router"),
    ]

    all_ok = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✓ {description} can be imported")
        except ImportError as e:
            print(f"✗ {description} import failed: {e}")
            all_ok = False

    return all_ok


def check_config():
    """Check configuration file"""
    print("\n=== Checking Configuration ===\n")

    config_path = "backend/open_webui/config/model_registry.yaml"

    if not Path(config_path).exists():
        print(f"✗ Config file not found: {config_path}")
        return False

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Check structure
        if 'providers' not in config:
            print("✗ Config missing 'providers' section")
            return False

        if 'models' not in config:
            print("✗ Config missing 'models' section")
            return False

        if 'routes' not in config:
            print("✗ Config missing 'routes' section")
            return False

        print(f"✓ Config file is valid")
        print(f"  - {len(config['providers'])} providers configured")
        print(f"  - {len(config['models'])} models defined")
        print(f"  - {len(config['routes'])} routes configured")

        return True

    except yaml.YAMLError as e:
        print(f"✗ Config file has YAML syntax errors: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading config: {e}")
        return False


def check_environment():
    """Check environment variables"""
    print("\n=== Checking Environment Variables ===\n")

    required_vars = [
        ("OPENAI_API_KEY", "OpenAI"),
        ("DEEPSEEK_API_KEY", "DeepSeek"),
    ]

    all_ok = True
    for var_name, description in required_vars:
        if os.getenv(var_name):
            print(f"✓ {description} API key is set ({var_name})")
        else:
            print(f"⚠ {description} API key not set ({var_name}) - Provider will not work")
            all_ok = False

    return all_ok


def check_database_models():
    """Check database models"""
    print("\n=== Checking Database Models ===\n")

    try:
        from open_webui.models.observability import RequestLog, RAGLog, CircuitBreakerState
        print("✓ Database models can be imported")

        # Check that models have required columns
        required_attrs = {
            'RequestLog': ['id', 'timestamp', 'user_id', 'provider', 'model_id', 'route_name'],
            'RAGLog': ['id', 'request_id', 'query', 'candidates_json'],
            'CircuitBreakerState': ['provider', 'state', 'failure_count']
        }

        all_ok = True
        for model_name, attrs in required_attrs.items():
            model = locals()[model_name]
            for attr in attrs:
                if not hasattr(model, attr):
                    print(f"✗ {model_name} missing attribute: {attr}")
                    all_ok = False

        if all_ok:
            print("✓ All database models have required attributes")

        return all_ok

    except Exception as e:
        print(f"✗ Database models check failed: {e}")
        return False


def check_test_files():
    """Check test files"""
    print("\n=== Checking Test Files ===\n")

    test_files = [
        "backend/tests/test_model_router.py",
        "backend/tests/test_rag_reranker.py",
        "backend/tests/test_fallback_handler.py",
    ]

    all_ok = True
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✓ {test_file}")
        else:
            print(f"✗ {test_file} not found")
            all_ok = False

    return all_ok


def run_quick_functional_test():
    """Run a quick functional test"""
    print("\n=== Running Quick Functional Test ===\n")

    try:
        from open_webui.services.model_registry import ModelRegistry
        from open_webui.services.model_router import ModelRouter, RoutingContext

        # Test 1: Load registry
        print("Test 1: Loading model registry...")
        registry = ModelRegistry()
        registry.load_config("backend/open_webui/config/model_registry.yaml")
        print(f"✓ Loaded {len(registry.models_by_id)} models")

        # Test 2: Analyze message content
        print("\nTest 2: Analyzing message content...")
        context = ModelRouter.analyze_message_content(
            messages=[{"role": "user", "content": "```python\nprint('hello')\n```"}]
        )
        assert context.has_code_block == True, "Should detect code block"
        print("✓ Code block detection works")

        # Test 3: Route a request
        print("\nTest 3: Routing a request...")
        router = ModelRouter()
        router.registry = registry
        decision = router.route(context)
        print(f"✓ Routed to: {decision.route_name} -> {decision.primary_model_id}")

        # Test 4: Reranker
        print("\nTest 4: Testing RAG reranker...")
        from open_webui.services.rag_reranker import LexicalReranker, RAGChunk

        reranker = LexicalReranker()
        chunks = [
            RAGChunk(
                doc_id="d1",
                chunk_id="c1",
                content="Python is a programming language",
                vector_score=0.8
            )
        ]
        result = reranker.rerank("What is Python?", chunks, top_k=1)
        print(f"✓ Reranked 1 chunk in {result.rerank_latency_ms:.1f}ms")

        print("\n✓ All functional tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Functional test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("Multi-Provider Implementation Verification")
    print("=" * 60)

    # File structure checks
    print("\n=== Checking File Structure ===\n")

    files = [
        ("backend/open_webui/services/model_registry.py", "Model Registry"),
        ("backend/open_webui/services/provider_adapters.py", "Provider Adapters"),
        ("backend/open_webui/services/model_router.py", "Model Router"),
        ("backend/open_webui/services/fallback_handler.py", "Fallback Handler"),
        ("backend/open_webui/services/rag_reranker.py", "RAG Reranker"),
        ("backend/open_webui/services/completion_handler.py", "Completion Handler"),
        ("backend/open_webui/models/observability.py", "Observability Models"),
        ("backend/open_webui/routers/observability.py", "Observability Router"),
        ("backend/open_webui/config/model_registry.yaml", "Config File"),
        ("src/lib/components/admin/Observability.svelte", "Dashboard UI"),
        ("MULTI_PROVIDER_GUIDE.md", "Documentation"),
    ]

    files_ok = all(check_file_exists(f, d) for f, d in files)

    # Module import checks
    imports_ok = check_imports()

    # Config checks
    config_ok = check_config()

    # Environment checks
    env_ok = check_environment()

    # Database checks
    db_ok = check_database_models()

    # Test file checks
    tests_ok = check_test_files()

    # Functional test
    functional_ok = run_quick_functional_test()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    results = [
        ("File Structure", files_ok),
        ("Module Imports", imports_ok),
        ("Configuration", config_ok),
        ("Environment Variables", env_ok),
        ("Database Models", db_ok),
        ("Test Files", tests_ok),
        ("Functional Tests", functional_ok),
    ]

    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{name:.<40} {status}")

    all_ok = all(ok for _, ok in results)

    if all_ok:
        print("\n✓ All checks passed! Multi-provider system is ready.")
        return 0
    else:
        print("\n⚠ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
