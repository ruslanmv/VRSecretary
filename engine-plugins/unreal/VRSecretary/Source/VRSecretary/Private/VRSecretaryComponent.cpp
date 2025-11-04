#include "VRSecretaryComponent.h"
#include "VRSecretarySettings.h"
#include "VRSecretaryLog.h"

#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Json.h"
#include "JsonUtilities.h"
#include "Misc/Guid.h"

UVRSecretaryComponent::UVRSecretaryComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    Settings = GetDefault<UVRSecretarySettings>();
}

void UVRSecretaryComponent::BeginPlay()
{
    Super::BeginPlay();
    EnsureSessionId();
}

void UVRSecretaryComponent::EnsureSessionId()
{
    if (SessionId.IsEmpty())
    {
        SessionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
        UE_LOG(LogVRSecretary, Verbose, TEXT("Generated new SessionId: %s"), *SessionId);
    }
}

void UVRSecretaryComponent::SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    if (UserText.IsEmpty())
    {
        UE_LOG(LogVRSecretary, Warning, TEXT("SendUserText: UserText is empty"));
        return;
    }

    EnsureSessionId();

    EVRSecretaryBackendMode Mode =
        (BackendModeOverride != EVRSecretaryBackendMode::GatewayOllama)
            ? BackendModeOverride
            : Settings->BackendMode;

    switch (Mode)
    {
        case EVRSecretaryBackendMode::GatewayOllama:
        case EVRSecretaryBackendMode::GatewayWatsonx:
            SendViaGateway(UserText);
            break;

        case EVRSecretaryBackendMode::DirectOllama:
            SendViaDirectOllama(UserText, Config);
            break;

        case EVRSecretaryBackendMode::LocalLlamaCpp:
            SendViaLocalLlamaCpp(UserText, Config);
            break;

        default:
            UE_LOG(LogVRSecretary, Error, TEXT("Unknown backend mode"));
            OnError.Broadcast(TEXT("Unknown backend mode"));
            break;
    }
}

void UVRSecretaryComponent::SendViaGateway(const FString& UserText)
{
    if (!Settings)
    {
        UE_LOG(LogVRSecretary, Error, TEXT("Settings is null"));
        OnError.Broadcast(TEXT("VRSecretary settings not found"));
        return;
    }

    FString Url = Settings->GatewayUrl;
    Url.RemoveFromEnd(TEXT("/"));
    Url += TEXT("/api/vr_chat");

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("session_id"), SessionId);
    JsonObject->SetStringField(TEXT("user_text"), UserText);

    FString RequestBody;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
    Request->SetContentAsString(RequestBody);

    Request->OnProcessRequestComplete().BindUObject(this, &UVRSecretaryComponent::HandleGatewayResponse);
    Request->SetTimeout(Settings->HttpTimeout);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending Gateway request to %s"), *Url);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        FString Error = TEXT("Gateway request failed");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    if (!EHttpResponseCodes::IsOk(Response->GetResponseCode()))
    {
        FString Error = FString::Printf(TEXT("Gateway HTTP %d: %s"),
            Response->GetResponseCode(),
            *Response->GetContentAsString());
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    TSharedPtr<FJsonObject> JsonObject;
    const FString Content = Response->GetContentAsString();
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Content);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        FString Error = TEXT("Failed to parse gateway JSON response");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    FString AssistantText;
    FString AudioBase64;
    JsonObject->TryGetStringField(TEXT("assistant_text"), AssistantText);
    JsonObject->TryGetStringField(TEXT("audio_wav_base64"), AudioBase64);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Gateway response text: %s"), *AssistantText);
    OnAssistantResponse.Broadcast(AssistantText, AudioBase64);
}

void UVRSecretaryComponent::SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    if (!Settings)
    {
        OnError.Broadcast(TEXT("VRSecretary settings not found"));
        return;
    }

    FString Url = Settings->DirectOllamaUrl;
    Url.RemoveFromEnd(TEXT("/"));
    Url += TEXT("/v1/chat/completions");

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> Root = MakeShareable(new FJsonObject);
    Root->SetStringField(TEXT("model"), Settings->DirectOllamaModel);

    // messages: system + user
    TArray<TSharedPtr<FJsonValue>> Messages;

    {
        TSharedPtr<FJsonObject> SysMsg = MakeShareable(new FJsonObject);
        SysMsg->SetStringField(TEXT("role"), TEXT("system"));
        SysMsg->SetStringField(TEXT("content"),
            TEXT("You are Ailey, a helpful VR secretary inside a virtual office."));
        Messages.Add(MakeShareable(new FJsonValueObject(SysMsg)));
    }

    {
        TSharedPtr<FJsonObject> UserMsg = MakeShareable(new FJsonObject);
        UserMsg->SetStringField(TEXT("role"), TEXT("user"));
        UserMsg->SetStringField(TEXT("content"), UserText);
        Messages.Add(MakeShareable(new FJsonValueObject(UserMsg)));
    }

    Root->SetArrayField(TEXT("messages"), Messages);
    Root->SetBoolField(TEXT("stream"), false);

    // Optional basic parameters
    Root->SetNumberField(TEXT("temperature"), Config.Temperature);
    Root->SetNumberField(TEXT("top_p"), Config.TopP);
    Root->SetNumberField(TEXT("max_tokens"), Config.MaxTokens);

    FString Body;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Request->SetContentAsString(Body);

    Request->OnProcessRequestComplete().BindUObject(this, &UVRSecretaryComponent::HandleDirectOllamaResponse);
    Request->SetTimeout(Settings->HttpTimeout);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending DirectOllama request to %s"), *Url);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        FString Error = TEXT("Direct Ollama request failed");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    if (!EHttpResponseCodes::IsOk(Response->GetResponseCode()))
    {
        FString Error = FString::Printf(TEXT("Direct Ollama HTTP %d: %s"),
            Response->GetResponseCode(),
            *Response->GetContentAsString());
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    TSharedPtr<FJsonObject> JsonObject;
    const FString Content = Response->GetContentAsString();
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Content);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        FString Error = TEXT("Failed to parse Ollama JSON response");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    // Standard OpenAI-style response: choices[0].message.content
    const TArray<TSharedPtr<FJsonValue>>* Choices;
    if (!JsonObject->TryGetArrayField(TEXT("choices"), Choices) || Choices->Num() == 0)
    {
        FString Error = TEXT("Ollama response missing choices");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    TSharedPtr<FJsonObject> FirstChoice = (*Choices)[0]->AsObject();
    TSharedPtr<FJsonObject> MessageObj;
    if (!FirstChoice.IsValid() ||
        !FirstChoice->TryGetObjectField(TEXT("message"), MessageObj) ||
        !MessageObj.IsValid())
    {
        FString Error = TEXT("Ollama response missing message object");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    FString AssistantText;
    MessageObj->TryGetStringField(TEXT("content"), AssistantText);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Direct Ollama response text: %s"), *AssistantText);

    // NOTE: Direct Ollama mode does not generate audio; return empty AudioBase64.
    OnAssistantResponse.Broadcast(AssistantText, TEXT(""));
}

void UVRSecretaryComponent::SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    // Stub implementation – this is where you would integrate llama.cpp
    // either by wrapping your Llama-Unreal logic or directly
    // linking against llama.cpp in ThirdParty/LlamaCpp.
    //
    // For now, we log a warning and fall back to Gateway mode.
    UE_LOG(LogVRSecretary, Warning,
        TEXT("LocalLlamaCpp backend is not wired yet; falling back to Gateway."));

    SendViaGateway(UserText);
}
