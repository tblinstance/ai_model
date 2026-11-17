"""Comprehensive verification tests for AI-Model platform services and engine."""

import pytest
from ai_engine.schemas import GenerationRequest, TaskType, ModelTier
from ai_engine.config import TIER_SPECS
from ai_engine.router import AIEngineRouter
from ai_engine.utils.vector_store import VectorMemory


def test_task_types_include_audio():
    assert TaskType.AUDIO == "audio"
    assert TaskType.CHAT == "chat"
    assert TaskType.CODE == "code"
    assert TaskType.IMAGES == "images"
    assert TaskType.VIDEO == "video"


def test_credit_cost_computation_all_tasks():
    for tier, spec in TIER_SPECS.items():
        for task in [TaskType.CHAT, TaskType.CODE, TaskType.IMAGES, TaskType.VIDEO, TaskType.AUDIO]:
            cost = spec.credit_cost.get(task)
            assert isinstance(cost, int)
            assert cost > 0


def test_tier_specs_support_audio():
    for tier, spec in TIER_SPECS.items():
        assert TaskType.AUDIO in spec.supported_tasks
        assert TaskType.AUDIO in spec.credit_cost


def test_vector_memory_rag_retrieval():
    mem = VectorMemory()
    mem.add_document("doc_test", "What is neural video rendering and transformer attention?")
    assert mem.count() > 0

    results = mem.search("neural video rendering", top_k=1)
    assert len(results) > 0
    assert results[0]["score"] > 0
    assert "neural video rendering" in results[0]["text"]


def test_task_router_rag_methods():
    router = AIEngineRouter()
    router.add_rag_document(
        doc_id="doc_custom",
        text="Deep neural models with multimodal cross-attention",
        metadata={"category": "architecture"}
    )
    matches = router.query_rag("multimodal cross-attention", top_k=2)
    assert len(matches) > 0
    assert any("multimodal" in m["text"].lower() for m in matches)


def test_chat_pipeline_execution():
    router = AIEngineRouter()
    req = GenerationRequest(
        prompt="Explain quantum entanglement",
        task=TaskType.CHAT,
        tier=ModelTier.FLASH,
    )
    resp = router.generate(req)
    assert resp.text is not None and len(resp.text) > 0
    assert resp.credits_used > 0


def test_code_pipeline_execution():
    router = AIEngineRouter()
    req = GenerationRequest(
        prompt="Write a Python function to compute Fibonacci numbers",
        task=TaskType.CODE,
        tier=ModelTier.FLASH,
    )
    resp = router.generate(req)
    assert resp.code is not None or (resp.text is not None and len(resp.text) > 0)
    assert resp.credits_used > 0


def test_audio_pipeline_execution():
    router = AIEngineRouter()
    req = GenerationRequest(
        prompt="Synthesize voice for welcoming users to AI Model Studio",
        task=TaskType.AUDIO,
        tier=ModelTier.FLASH,
    )
    resp = router.generate(req)
    assert resp.artifact_url is not None or resp.artifact_path is not None
    assert resp.credits_used > 0


def test_portrait_synthesis_in_images_pipeline():
    router = AIEngineRouter()
    req = GenerationRequest(
        prompt="Photorealistic portrait of a female software engineer",
        task=TaskType.IMAGES,
        tier=ModelTier.FLASH,
    )
    resp = router.generate(req)
    assert resp.artifact_url is not None or resp.artifact_path is not None or resp.preview_base64 is not None
    assert resp.credits_used > 0


def test_audio_analysis_pipeline():
    router = AIEngineRouter()
    # Generate 1s test waveform
    req = GenerationRequest(
        prompt="Short audio chime",
        task=TaskType.AUDIO,
        tier=ModelTier.FLASH,
    )
    resp = router.generate(req)
    assert resp.artifact_path is not None
    analysis = router.analyze_audio(resp.artifact_path)
    assert analysis.get("success") is True
    assert "duration_seconds" in analysis
    assert "sample_rate" in analysis


def test_rag_url_scrape():
    router = AIEngineRouter()
    sample_html = "<html><head><title>Deep Learning</title></head><body><h1>Transformer Models</h1><p>Transformers use self-attention to process sequential tokens.</p></body></html>"
    res = router.scrape_rag_url("https://example.com/ai", html_content=sample_html)
    assert res.get("success") is True
    assert res.get("title") == "Deep Learning"
    assert res.get("indexed_chunks", 0) > 0


def test_frontier_libraries_health():
    router = AIEngineRouter()
    report = router.frontier_libraries_health()
    assert "transformers" in report
    assert "diffusers" in report
    assert "whisper" in report
    assert "librosa" in report
    assert "soundfile" in report
    assert "chromadb" in report
    assert "peft" in report
    assert report["transformers"]["available"] is True
    assert report["soundfile"]["available"] is True


def test_training_dataset_multimodal_balance():
    from ai_engine.training.dataset import BUILTIN_TRAINING_SAMPLES, INTENT_LABELS, dataset_summary
    
    summary = dataset_summary()
    assert summary["sample_count"] > 3000
    assert summary["audio_sample_count"] > 0
    assert summary["code_sample_count"] > 0
    assert "audio" in summary["task_counts"]
    assert summary["task_counts"]["audio"] > 0
    assert summary["task_counts"]["chat"] > 0
    assert summary["task_counts"]["code"] > 0
    assert summary["task_counts"]["images"] > 0
    assert summary["task_counts"]["video"] > 0
    
    for intent in ("audio_generation", "audio_transcription", "audio_analysis", "rag_knowledge"):
        assert intent in INTENT_LABELS


def test_audio_intent_classification_and_retrieval():
    from ai_engine.router import AIEngineRouter
    from ai_engine.schemas import TaskType

    router = AIEngineRouter()
    trainer = router.registry.trainer

    sample, score = trainer.retrieve_best_match(
        "synthesize voice speech for welcoming users to ai model studio platform",
        task=TaskType.AUDIO,
        min_score=0.35,
    )
    assert sample is not None
    assert sample.task == TaskType.AUDIO
    assert sample.intent == "audio_generation"
    assert score >= 0.35

    asr_sample, asr_score = trainer.retrieve_best_match(
        "transcribe meeting recording multilingual speech recognition whisper timestamps",
        task=TaskType.AUDIO,
        min_score=0.35,
    )
    assert asr_sample is not None
    assert asr_sample.task == TaskType.AUDIO
    assert asr_sample.intent == "audio_transcription"


