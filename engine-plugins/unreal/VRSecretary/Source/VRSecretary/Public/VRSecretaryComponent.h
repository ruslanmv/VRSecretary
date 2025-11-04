#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretaryComponent.generated.h"

class UVRSecretarySettings;
class ULlamaComponent;
class IHttpRequest;
class IHttpResponse;

typedef TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> FHttpRequestPtr;
typedef TSharedPtr<IHttpResponse, ESPMode::ThreadSafe> FHttpResponsePtr;

/**
 * Main component for interacting with the VRSecretary backends / LLMs.
 *
 * Attach this component to an actor (e.g. your VR manager or avatar) and call
 * SendUserText / SendUserTextWithDefaultConfig. Responses are delivered via
 * the OnAssistantResponse and OnError multicast delegates.
 */
UCLASS(ClassGroup=(VRSecretary), meta=(BlueprintSpawnableComponent))
class VRSECRETARY_API UVRSecretaryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UVRSecretaryComponent();

    /**
     * Send user text to the configured backend using the provided config.
     * This returns immediately; results are delivered asynchronously via
     * OnAssistantResponse / OnError.
     */
    UFUNCTION(BlueprintCallable, Category="VRSecretary")
    void SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /**
     * Convenience overload that uses DefaultChatConfig.
     */
    UFUNCTION(BlueprintCallable, Category="VRSecretary")
    void SendUserTextWithDefaultConfig(const FString& UserText);

    /** Assistant response (full text + optional base64-encoded WAV audio). */
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnAssistantResponse OnAssistantResponse;

    /** Error event (network problems, JSON parse errors, etc). */
    UPROPERTY(BlueprintAssignable, Category="VRSecretary")
    FVRSecretaryOnError OnError;

    /** If true, this component overrides the global backend mode. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    bool bOverrideBackendMode;

    /** Backend mode used when bOverrideBackendMode is true. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary", meta=(EditCondition="bOverrideBackendMode"))
    EVRSecretaryBackendMode BackendMode;

    /** Default chat configuration used when calling SendUserTextWithDefaultConfig. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary")
    FVRSecretaryChatConfig DefaultChatConfig;

    /**
     * Optional reference to a Llama-Unreal component used when BackendMode == LocalLlamaCpp.
     * If not set, the component will try to auto-discover one on the same actor.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="VRSecretary|Llama")
    ULlamaComponent* LlamaComponent;

protected:
    virtual void BeginPlay() override;

private:
    /** Cached pointer to global settings. */
    const UVRSecretarySettings* Settings;

    /** Stable session id that the gateway can use to maintain conversational context. */
    FString SessionId;

    /** Gateway (FastAPI) path: POST /api/vr_chat */
    void SendViaGateway(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /** Direct HTTP call to OpenAI-style /v1/chat/completions endpoint (e.g. Ollama proxy). */
    void SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /** Local llama.cpp via Llama-Unreal. */
    void SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config);

    /** Internal HTTP completion handlers. */
    void HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
    void HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);

    /** Callback for Llama-Unreal full responses. */
    UFUNCTION()
    void HandleLlamaResponse(const FString& AssistantText);
};
