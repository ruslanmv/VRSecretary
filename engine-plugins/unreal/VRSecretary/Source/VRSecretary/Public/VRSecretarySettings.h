#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretarySettings.generated.h"

/**
 * Global project settings for VRSecretary.
 */
UCLASS(config=Game, defaultconfig, meta=(DisplayName="VRSecretary Settings"))
class VRSECRETARY_API UVRSecretarySettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    UVRSecretarySettings();

    /** Base URL of the VRSecretary Gateway backend (FastAPI). */
    UPROPERTY(EditAnywhere, config, Category="Gateway", meta=(DisplayName="Gateway URL"))
    FString GatewayUrl;

    /** Backend mode for LLM calls. */
    UPROPERTY(EditAnywhere, config, Category="Backend", meta=(DisplayName="Backend Mode"))
    EVRSecretaryBackendMode BackendMode;

    /** Default request timeout in seconds for HTTP calls. */
    UPROPERTY(EditAnywhere, config, Category="HTTP", meta=(ClampMin="1.0", UIMin="1.0"))
    float HttpTimeout;

    /** Base URL of the Ollama server (used in DirectOllama mode). */
    UPROPERTY(EditAnywhere, config, Category="Direct Ollama")
    FString DirectOllamaUrl;

    /** Default Ollama model name (for DirectOllama mode). */
    UPROPERTY(EditAnywhere, config, Category="Direct Ollama")
    FString DirectOllamaModel;

    // UDeveloperSettings interface
    virtual FName GetCategoryName() const override;
};
