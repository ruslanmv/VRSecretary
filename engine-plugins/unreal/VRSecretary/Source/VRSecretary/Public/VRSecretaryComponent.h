#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
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
     * Optional per-component language code override (ISO 639-1: en, it, es, fr, etc.)
     * If empty, uses project default from VRSecretarySettings.
     * If both empty, backend defaults to "en".
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary", meta=(
        DisplayName="Language Code Override",
        ToolTip="ISO 639-1 code (en, it, es, etc.). Leave empty to use project default."
    ))
    FString LanguageCode;

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
     */
    UFUNCTION(BlueprintCallable, Category="VRSecretary")
    void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);

protected:
    virtual void BeginPlay() override;

private:
    const UVRSecretarySettings* Settings;

    void EnsureSessionId();
    FString GetEffectiveLanguageCode() const;

    void SendViaGateway(const FString& UserText);
    void SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config);
    void SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config);

    void HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
};