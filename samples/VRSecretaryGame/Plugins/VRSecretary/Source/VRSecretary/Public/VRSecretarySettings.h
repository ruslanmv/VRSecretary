#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretarySettings.generated.h"

/**
 * Project-wide settings for the VRSecretary plugin.
 * Shown under: Project Settings → Plugins → VRSecretary
 */
UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="VRSecretary"))
class VRSECRETARY_API UVRSecretarySettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    UVRSecretarySettings();

    /** Default backend mode used when components don't override it. */
    UPROPERTY(EditAnywhere, Config, Category="Backend")
    EVRSecretaryBackendMode BackendMode;

    /** Base URL of the FastAPI gateway, e.g. http://localhost:8000 */
    UPROPERTY(EditAnywhere, Config, Category="Gateway")
    FString GatewayUrl;

    /** HTTP timeout in seconds for all backend calls. */
    UPROPERTY(EditAnywhere, Config, Category="HTTP", meta=(ClampMin="1.0", UIMin="1.0"))
    float HttpTimeout;

    /** Base URL of the Ollama server (for DirectOllama mode). */
    UPROPERTY(EditAnywhere, Config, Category="Direct Ollama")
    FString DirectOllamaUrl;

    /** Default Ollama model to use (for DirectOllama mode). */
    UPROPERTY(EditAnywhere, Config, Category="Direct Ollama")
    FString DirectOllamaModel;

    // UDeveloperSettings interface
    virtual FName GetCategoryName() const override;
};
