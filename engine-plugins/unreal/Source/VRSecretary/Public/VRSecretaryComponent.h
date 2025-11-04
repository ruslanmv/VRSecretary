#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VRSecretaryChatTypes.h"
#include "VRSecretaryComponent.generated.h"

UENUM(BlueprintType)
enum class EAIBackendMode : uint8
{
    GatewayOllama     UMETA(DisplayName = "Gateway (Ollama)"),
    GatewayWatsonx    UMETA(DisplayName = "Gateway (Watsonx)"),
    LocalLlamaCpp     UMETA(DisplayName = "Local LlamaCpp")
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FOnVRSecretaryResponse,
    const FString&, AssistantText,
    const FString&, AudioBase64
);

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(
    FOnVRSecretaryError,
    const FString&, ErrorMessage
);

/**
 * UVRSecretaryComponent
 *
 * Lightweight HTTP client component for talking to the VRSecretary Gateway.
 * Attach this to any Actor (e.g., a VR manager Blueprint) and call SendUserText
 * from Blueprints or C++.
 */
UCLASS(ClassGroup = (VRSecretary), meta = (BlueprintSpawnableComponent))
class VRSECRETARY_API UVRSecretaryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UVRSecretaryComponent();

    /** Backend mode used by this component (gateway vs local llama.cpp) */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VRSecretary")
    EAIBackendMode BackendMode;

    /** Base URL of the VRSecretary Gateway service, e.g. http://localhost:8000 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VRSecretary")
    FString GatewayUrl;

    /** Optional session identifier; if empty, one is generated on BeginPlay */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "VRSecretary")
    FString SessionId;

    /** Fired when a reply and audio are successfully received from the backend */
    UPROPERTY(BlueprintAssignable, Category = "VRSecretary")
    FOnVRSecretaryResponse OnResponse;

    /** Fired when any error occurs (HTTP, JSON parsing, etc.) */
    UPROPERTY(BlueprintAssignable, Category = "VRSecretary")
    FOnVRSecretaryError OnError;

    /** Send a text message from the user to the AI backend */
    UFUNCTION(BlueprintCallable, Category = "VRSecretary")
    void SendUserText(const FString& UserText);

protected:
    virtual void BeginPlay() override;

private:
    void SendRequest_Internal(const FString& UserText);
    void HandleHttpResponse(class FHttpRequestPtr Request, class FHttpResponsePtr Response, bool bWasSuccessful);
};
