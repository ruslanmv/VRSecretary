#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretaryComponent.generated.h"

class UVRSecretarySettings;

/**
 * Main component for interacting with the VRSecretary backend / LLMs.
 * Attach this component to an actor (e.g. your VR manager or avatar) and call SendUserText.
 */
UCLASS(ClassGroup=(VRSecretary), meta=(BlueprintSpawnableComponent))
class VRSECRETARY_API UVRSecretaryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UVRSecretaryComponent();

    /** Backend mode override (if not GatewayOllama, overrides project settings). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VRSecretary")
    EVRSecretaryBackendMode BackendModeOverride;

    /** Optional: custom session ID. If empty, a GUID is generated at BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VRSecretary")
    FString SessionId;

    /** Delegates fired when a response or error is received. */
    UPROPERTY(BlueprintAssignable, Category = "VRSecretary")
    FVRSecretaryOnAssistantResponse OnAssistantResponse;

    UPROPERTY(BlueprintAssignable, Category = "VRSecretary")
    FVRSecretaryOnError OnError;

    /**
     * Send user text to the configured backend.
     * This returns immediately; result is delivered via OnAssistantResponse / OnError.
     */
    UFUNCTION(BlueprintCallable, Category = "VRSecretary")
    void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);

protected:
    virtual void BeginPlay() override;

private:
    /** Cached pointer to global settings. */
    const UVRSecretarySettings* Settings;

    /** Ensure we have a valid session ID. */
    void EnsureSessionId();

    /** Gateway (FastAPI) path: POST /api/vr_chat */
    void SendViaGateway(const FString& UserText);

    /** Direct HTTP call to Ollama server (no Python gateway). */
    void SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /** Local llama.cpp (stub) – currently logs and falls back to gateway. */
    void SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /** Internal HTTP completion handlers. */
    void HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
};
