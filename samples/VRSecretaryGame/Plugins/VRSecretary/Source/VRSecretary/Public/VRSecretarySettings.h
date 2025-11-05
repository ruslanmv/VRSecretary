#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretarySettings.generated.h"

/**
 * Global project settings for VRSecretary.
 *
 * These appear under Project Settings → Plugins → VRSecretary.
 * They provide defaults which individual UVRSecretaryComponent instances
 * can optionally override.
 */
UCLASS(config=Game, defaultconfig, meta=(DisplayName="VRSecretary Settings"))
class VRSECRETARY_API UVRSecretarySettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    UVRSecretarySettings();

    /** Base URL of the FastAPI gateway (e.g. http://localhost:8000). */
    UPROPERTY(EditAnywhere, config, Category="Gateway")
    FString GatewayUrl;

    /** Default backend mode used when a component does not override it. */
    UPROPERTY(EditAnywhere, config, Category="Gateway")
    EVRSecretaryBackendMode BackendMode;

    /** HTTP timeout in seconds for all backend calls. */
    UPROPERTY(EditAnywhere, config, Category="Gateway", meta=(ClampMin="1.0", UIMin="1.0"))
    float HttpTimeout;

    /**
     * Base URL of the OpenAI-compatible Ollama (or other) endpoint,
     * used when EVRSecretaryBackendMode::DirectOllama is selected.
     * Example: http://localhost:11434
     */
    UPROPERTY(EditAnywhere, config, Category="DirectOllama")
    FString DirectOllamaUrl;

    /** Model name to send to the OpenAI-style /v1/chat/completions endpoint. */
    UPROPERTY(EditAnywhere, config, Category="DirectOllama")
    FString DirectOllamaModel;

    // UDeveloperSettings interface
    virtual FName GetCategoryName() const override;
};
