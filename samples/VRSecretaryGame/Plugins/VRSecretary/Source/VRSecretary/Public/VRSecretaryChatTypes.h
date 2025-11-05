#pragma once

#include "CoreMinimal.h"
#include "VRSecretaryChatTypes.generated.h"

/**
 * Backend selection used globally (UVRSecretarySettings) and optionally per component.
 */
UENUM(BlueprintType)
enum class EVRSecretaryBackendMode : uint8
{
    /** Use the FastAPI gateway with Ollama as the underlying model provider. */
    GatewayOllama     UMETA(DisplayName = "Gateway (Ollama)"),

    /** Use the FastAPI gateway with IBM watsonx.ai as the underlying provider. */
    GatewayWatsonx    UMETA(DisplayName = "Gateway (watsonx.ai)"),

    /** Call an OpenAI-compatible HTTP endpoint directly (e.g. Ollama with an OpenAI proxy). */
    DirectOllama      UMETA(DisplayName = "Direct Ollama (OpenAI-style)"),

    /** Use a fully local llama.cpp model via the Llama-Unreal plugin. */
    LocalLlamaCpp     UMETA(DisplayName = "Local Llama.cpp")
};

/**
 * Per-request generation configuration. This is intentionally minimal and
 * maps cleanly onto typical OpenAI-style /v1/chat/completions parameters.
 */
USTRUCT(BlueprintType)
struct FVRSecretaryChatConfig
{
    GENERATED_BODY()

    /** Sampling temperature in the range [0, 2]. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float Temperature;

    /** Maximum number of new tokens to generate. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    int32 MaxTokens;

    /** Nucleus sampling parameter. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float TopP;

    /** Positive values penalise new tokens based on whether they appear in the text so far. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float PresencePenalty;

    /** Positive values penalise new tokens based on their existing frequency in the text so far. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float FrequencyPenalty;

    FVRSecretaryChatConfig()
        : Temperature(0.7f)
        , MaxTokens(256)
        , TopP(1.0f)
        , PresencePenalty(0.0f)
        , FrequencyPenalty(0.0f)
    {
    }
};

/** Broadcast when the assistant has produced a full response (and optional audio). */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FVRSecretaryOnAssistantResponse,
    const FString&, AssistantText,
    const FString&, AudioBase64
);

/** Broadcast when any backend reports an error. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(
    FVRSecretaryOnError,
    const FString&, ErrorMessage
);
