#pragma once

#include "CoreMinimal.h"
#include "VRSecretaryChatTypes.generated.h"

/** Which backend to use for chat. */
UENUM(BlueprintType)
enum class EVRSecretaryBackendMode : uint8
{
    /** Go through the FastAPI gateway using Ollama */
    GatewayOllama    UMETA(DisplayName = "Gateway (Ollama)"),

    /** Go through the FastAPI gateway using IBM watsonx.ai */
    GatewayWatsonx   UMETA(DisplayName = "Gateway (watsonx.ai)"),

    /** Call Ollama’s OpenAI-compatible HTTP API directly from Unreal */
    DirectOllama     UMETA(DisplayName = "Direct Ollama (HTTP)"),

    /** Placeholder for a future native llama.cpp integration */
    LocalLlamaCpp    UMETA(DisplayName = "Local Llama.cpp (stub)")
};

/** Generic sampling config passed to the backends. */
USTRUCT(BlueprintType)
struct FVRSecretaryChatConfig
{
    GENERATED_BODY()

    /** Sampling temperature, 0.0–2.0 (typical: 0.2–1.0). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float Temperature = 0.7f;

    /** Nucleus sampling probability (Top-p). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float TopP = 0.9f;

    /** Maximum number of tokens to generate. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    int32 MaxTokens = 256;
};

/** Fired when the assistant replies. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FVRSecretaryOnAssistantResponse,
    const FString&, AssistantText,
    const FString&, AudioWavBase64
);

/** Fired when something goes wrong (HTTP failure, JSON error, etc.). */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(
    FVRSecretaryOnError,
    const FString&, ErrorMessage
);
