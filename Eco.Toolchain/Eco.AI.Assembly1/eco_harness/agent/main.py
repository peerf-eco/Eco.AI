"""EcoOS Component Agent — model factory for the active pipeline.

``get_model()`` builds a ``pi_ai.Model`` for the configured OpenRouter endpoint.
It is the only public entry here; the /ws/chat endpoint (backend/server.py)
calls it. Streaming goes through pi_ai.stream_simple, which passes
``delta.reasoning`` through correctly (langchain_openai 1.2.1 dropped it).

No LangGraph / LangChain. The legacy CLI and ``get_llm()`` are not part of the
active runtime.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def get_model(profile=None, *, role: str | None = None, providers: dict | None = None):
    """Build a pi_ai.Model for the configured endpoint.

    Profiles whose ``provider`` names an entry in ``providers`` route to a
    custom endpoint (e.g. a local LM Studio / Ollama / vLLM server): the
    registered ``base_url`` is used and an API key is optional (local servers
    accept any bearer token). Anything else (and the historical default)
    routes to OpenRouter via ``OPENROUTER_URL`` / ``OPENAI_API_KEY``.
    """
    from agent.pi_ai import Model, ModelCost, OpenAICompletionsCompat, OpenRouterRouting
    from agent.pi_ai.env_api_keys import get_api_key as _get_api_key

    provider_name = getattr(profile, "provider", None) or "openrouter"
    entry = (providers or {}).get(provider_name)
    custom = entry is not None

    if custom:
        # Self-hosted / custom OpenAI-compat endpoint.
        base_url = entry.base_url
        api_key = _get_api_key(provider_name)
        if api_key is None and getattr(entry, "api_key_env", None):
            api_key = os.getenv(entry.api_key_env)
        # Local servers don't require a credential — omit the header if none.
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    else:
        # OpenRouter (default). A key is mandatory here; without it the harness
        # cannot reach any model, so fail loudly rather than emitting bad calls.
        base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[ERROR] OPENAI_API_KEY not set")
            print("[INFO] Set it in .env file or export OPENAI_API_KEY=your-key")
            sys.exit(1)
        headers = {"Authorization": f"Bearer {api_key}"}

    role_model = os.getenv(f"ECO_ROLE_{role.upper()}_MODEL") if role else None
    configured_model = getattr(profile, "id", None)
    model_id = (
        role_model
        or configured_model
        or os.getenv("LLM_MODEL")
        or "tencent/hy3-preview"
    )

    # Implicit prompt cache lives per upstream provider; OpenRouter's default
    # load-balancing hops between providers and zeroes the hit-rate. Pinning
    # one provider keeps the prefix cache warm across agent-loop iterations
    # (measured 2026-06-12: cached=99.6%, -81% per-call cost on z-ai/glm-5.1).
    # Provider pinning only applies to OpenRouter.
    routing = None
    if not custom:
        # Per-model provider pin (from config/models.yaml) takes precedence over the
        # global OPENROUTER_PROVIDER_PIN env. Roles whose model profile omits
        # provider_pin fall back to the env default (the LLM_MODEL + pin "default
        # combination"). If neither is set, no pin is applied and OpenRouter
        # load-balances across the model's serving providers.
        profile_pin = (getattr(profile, "provider_pin", None) or "").strip()
        pin = profile_pin or os.getenv("OPENROUTER_PROVIDER_PIN", "").strip()
        # Default to allow_fallbacks=True: the pinned provider is only the *preferred*
        # order. If its endpoint is briefly unavailable (or an aliased snapshot like
        # tencent/hy3 -> tencent/hy3-20260706 has no live pinned endpoint), OpenRouter
        # routes to the other providers serving the same model instead of failing with
        # HTTP 404 "No endpoints found". Set OPENROUTER_ALLOW_FALLBACKS=false to restore
        # strict single-provider pinning (availability traded for cache warmth).
        allow_fallbacks = os.getenv("OPENROUTER_ALLOW_FALLBACKS", "true").strip().lower() != "false"
        if pin:
            routing = OpenRouterRouting(
                order=[p.strip() for p in pin.split(",") if p.strip()],
                allow_fallbacks=allow_fallbacks,
            )
            print(f"[INFO] OpenRouter provider pin: {pin} (allow_fallbacks={allow_fallbacks})")

    print(f"[INFO] Using pi_ai Model: {model_id}")
    print(f"[INFO] API URL: {base_url}")

    # Resolve the model's context window so max_tokens can be clamped to fit
    # (the system prompt routinely injects a large stitched-source codebase,
    # which otherwise overflows the context and yields HTTP 400).
    context_window = 262_144
    try:
        from agent.pi_ai.models import known_models
        for _m in known_models():
            if _m.id == model_id:
                context_window = _m.contextWindow or context_window
                break
    except Exception:
        pass

    return Model(
        id=model_id,
        name=model_id,
        api="openai-completions",
        provider=provider_name,
        baseUrl=base_url.rstrip("/"),
        contextWindow=context_window,
        reasoning=getattr(profile, "reasoning", "medium") != "minimal",
        cost=ModelCost(),
        headers=headers,
        compat=OpenAICompletionsCompat(
            thinkingFormat="openrouter",
            openRouterRouting=routing,
        ),
    )
