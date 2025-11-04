#pragma once

#include "CoreMinimal.h"
#include "VRSecretaryChatTypes.generated.h"

UENUM(BlueprintType)
enum class EVRSecretaryBackendMode : uint8
{
    GatewayOllama     UMETA(DisplayName = "Gateway (Ollama)"),
    GatewayWatsonx    UMETA(DisplayName = "Gateway (watsonx.ai)"),
    DirectOllama      UMETA(DisplayName = "Direct Ollama"),
    LocalLlamaCpp     UMETA(DisplayName = "Local Llama.cpp (stub)")
};

USTRUCT(BlueprintType)
struct FVRSecretaryChatConfig
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float Temperature = 0.7f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    float TopP = 0.9f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    int32 MaxTokens = 256;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FVRSecretaryOnAssistantResponse,
    const FString&, AssistantText,
    const FString&, AudioBase64
);

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(
    FVRSecretaryOnError,
    const FString&, ErrorMessage
);
