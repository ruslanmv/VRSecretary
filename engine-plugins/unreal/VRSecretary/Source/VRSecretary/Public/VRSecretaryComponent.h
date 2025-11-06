#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Interfaces/IHttpRequest.h"    // FHttpRequestPtr
#include "Interfaces/IHttpResponse.h"   // FHttpResponsePtr
#include "VRSecretaryChatTypes.h"
#include "VRSecretaryComponent.generated.h"

class UVRSecretarySettings;

/**
 * Main component for interacting with the VRSecretary backends.
 * Attach this to an actor (e.g. your VR manager or avatar) and call SendUserText.
 */
UCLASS(ClassGroup=(VRSecretary), meta=(BlueprintSpawnableComponent))
class VRSECRETARY_API UVRSecretaryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UVRSecretaryComponent();

    /** Optional per-component override of the backend mode. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    EVRSecretaryBackendMode BackendModeOverride;

    /**
     * Optional per-component TTS language override (ISO 639-1, e.g. "en", "it", "fr").
     *
     * - If left empty, the plugin uses the project-wide DefaultLanguage
     *   from UVRSecretarySettings.
     * - If set, this language will be sent to the gateway for all requests
     *   issued by this component.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary|TTS", meta=(
        DisplayName="Language Override",
        ToolTip="Optional language code for TTS (ISO 639-1, e.g. \"en\", \"it\", \"fr\"). "
                "Leave empty to use the project-wide default configured in VRSecretary settings."
    ))
    FString LanguageOverride;

    /** Optional: custom session ID. If empty, a GUID is generated at BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    FString SessionId;

    /** Fired when a response (text + optional audio) is received. */
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnAssistantResponse OnAssistantResponse;

    /** Fired when an error occurs. */
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnError OnError;

    /**
     * Send user text to the configured backend.
     * Returns immediately; result is delivered via delegates.
     *
     * @param UserText Text to send to the assistant.
     * @param Config   Runtime chat configuration (voice, etc.).
     */
    UFUNCTION(BlueprintCallable, Category="VRSecretary")
    void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);

protected:
    virtual void BeginPlay() override;

private:
    /** Cached pointer to the global settings object. */
    const UVRSecretarySettings* Settings;

    /** Ensure SessionId is non-empty. */
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
