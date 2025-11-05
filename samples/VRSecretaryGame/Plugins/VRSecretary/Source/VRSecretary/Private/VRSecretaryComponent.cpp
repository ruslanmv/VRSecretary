#include "VRSecretaryComponent.h"

#include "VRSecretaryLog.h"
#include "VRSecretarySettings.h"

#include "HttpModule.h"
#include "Http.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Json.h"
#include "JsonUtilities.h"
#include "Misc/Guid.h"

// Llama-Unreal
#include "LlamaComponent.h"
#include "LlamaDataTypes.h"

UVRSecretaryComponent::UVRSecretaryComponent()
{
    PrimaryComponentTick.bCanEverTick = false;

    Settings = GetDefault<UVRSecretarySettings>();
    bOverrideBackendMode = false;
    BackendMode = Settings ? Settings->BackendMode : EVRSecretaryBackendMode::GatewayOllama;
    DefaultChatConfig = FVRSecretaryChatConfig();
    LlamaComponent = nullptr;
}

void UVRSecretaryComponent::BeginPlay()
{
    Super::BeginPlay();

    if (SessionId.IsEmpty())
    {
        SessionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
    }
}

void UVRSecretaryComponent::SendUserTextWithDefaultConfig(const FString& UserText)
{
    SendUserText(UserText, DefaultChatConfig);
}

void UVRSecretaryComponent::SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    if (!Settings)
    {
        UE_LOG(LogVRSecretary, Error, TEXT("UVRSecretaryComponent: Settings asset not found."));
        OnError.Broadcast(TEXT("VRSecretary settings not found; ensure plugin is enabled correctly."));
        return;
    }

    EVRSecretaryBackendMode EffectiveMode = Settings->BackendMode;
    if (bOverrideBackendMode)
    {
        EffectiveMode = BackendMode;
    }

    switch (EffectiveMode)
    {
    case EVRSecretaryBackendMode::GatewayOllama:
    case EVRSecretaryBackendMode::GatewayWatsonx:
        SendViaGateway(UserText, Config);
        break;

    case EVRSecretaryBackendMode::DirectOllama:
        SendViaDirectOllama(UserText, Config);
        break;

    case EVRSecretaryBackendMode::LocalLlamaCpp:
        SendViaLocalLlamaCpp(UserText, Config);
        break;

    default:
        OnError.Broadcast(TEXT("Unsupported VRSecretary backend mode."));
        break;
    }
}

static FString NormalizeBaseUrl(const FString& InUrl)
{
    FString Url = InUrl;
    Url.TrimStartAndEndInline();

    if (!Url.EndsWith(TEXT("/")))
    {
        Url += TEXT("/");
    }
    return Url;
}

void UVRSecretaryComponent::SendViaGateway(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    const FString BaseUrl = NormalizeBaseUrl(Settings->GatewayUrl);
    const FString Url     = BaseUrl + TEXT("api/vr_chat");

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending VRSecretary gateway request to %s"), *Url);

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("session_id"), SessionId);
    Root->SetStringField(TEXT("user_text"), UserText);

    FString Body;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Request->SetContentAsString(Body);

    Request->OnProcessRequestComplete().Unbind();
    Request->OnProcessRequestComplete().BindUObject(this, &UVRSecretaryComponent::HandleGatewayResponse);
    Request->SetTimeout(Settings->HttpTimeout);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleGatewayResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        OnError.Broadcast(TEXT("Gateway request failed or no response received."));
        return;
    }

    const int32 Code = Response->GetResponseCode();
    if (!EHttpResponseCodes::IsOk(Code))
    {
        const FString Msg = FString::Printf(TEXT("Gateway HTTP error: %d"), Code);
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Msg);
        OnError.Broadcast(Msg);
        return;
    }

    TSharedPtr<FJsonObject> Json;
    const FString ResponseStr = Response->GetContentAsString();
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseStr);

    if (!FJsonSerializer::Deserialize(Reader, Json) || !Json.IsValid())
    {
        UE_LOG(LogVRSecretary, Error, TEXT("Failed to parse gateway JSON: %s"), *ResponseStr);
        OnError.Broadcast(TEXT("Failed to parse gateway JSON response."));
        return;
    }

    FString AssistantText;
    if (!Json->TryGetStringField(TEXT("assistant_text"), AssistantText))
    {
        OnError.Broadcast(TEXT("Gateway JSON did not contain 'assistant_text'."));
        return;
    }

    FString AudioBase64;
    Json->TryGetStringField(TEXT("audio_wav_base64"), AudioBase64);

    OnAssistantResponse.Broadcast(AssistantText, AudioBase64);
}

void UVRSecretaryComponent::SendViaDirectOllama(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    const FString BaseUrl = NormalizeBaseUrl(Settings->DirectOllamaUrl);
    const FString Url     = BaseUrl + TEXT("v1/chat/completions");

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending DirectOllama request to %s"), *Url);

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("model"), Settings->DirectOllamaModel);

    // Minimal OpenAI-style messages array: [ { "role": "user", "content": UserText } ]
    TArray<TSharedPtr<FJsonValue>> Messages;
    {
        TSharedPtr<FJsonObject> Msg = MakeShared<FJsonObject>();
        Msg->SetStringField(TEXT("role"), TEXT("user"));
        Msg->SetStringField(TEXT("content"), UserText);
        Messages.Add(MakeShared<FJsonValueObject>(Msg));
    }
    Root->SetArrayField(TEXT("messages"), Messages);

    Root->SetNumberField(TEXT("temperature"), Config.Temperature);
    Root->SetNumberField(TEXT("top_p"), Config.TopP);
    Root->SetNumberField(TEXT("presence_penalty"), Config.PresencePenalty);
    Root->SetNumberField(TEXT("frequency_penalty"), Config.FrequencyPenalty);
    Root->SetNumberField(TEXT("max_tokens"), Config.MaxTokens);

    FString Body;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Request->SetContentAsString(Body);

    Request->OnProcessRequestComplete().Unbind();
    Request->OnProcessRequestComplete().BindUObject(this, &UVRSecretaryComponent::HandleDirectOllamaResponse);
    Request->SetTimeout(Settings->HttpTimeout);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleDirectOllamaResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        OnError.Broadcast(TEXT("DirectOllama request failed or no response received."));
        return;
    }

    const int32 Code = Response->GetResponseCode();
    if (!EHttpResponseCodes::IsOk(Code))
    {
        const FString Msg = FString::Printf(TEXT("DirectOllama HTTP error: %d"), Code);
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Msg);
        OnError.Broadcast(Msg);
        return;
    }

    TSharedPtr<FJsonObject> Json;
    const FString ResponseStr = Response->GetContentAsString();
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseStr);

    if (!FJsonSerializer::Deserialize(Reader, Json) || !Json.IsValid())
    {
        UE_LOG(LogVRSecretary, Error, TEXT("Failed to parse DirectOllama JSON: %s"), *ResponseStr);
        OnError.Broadcast(TEXT("Failed to parse DirectOllama JSON response."));
        return;
    }

    const TArray<TSharedPtr<FJsonValue>>* ChoicesArray = nullptr;
    if (!Json->TryGetArrayField(TEXT("choices"), ChoicesArray) || !ChoicesArray || ChoicesArray->Num() == 0)
    {
        OnError.Broadcast(TEXT("DirectOllama JSON did not contain 'choices[0]'."));
        return;
    }

    const TSharedPtr<FJsonObject> ChoiceObj = (*ChoicesArray)[0]->AsObject();
    if (!ChoiceObj.IsValid())
    {
        OnError.Broadcast(TEXT("DirectOllama choices[0] was not an object."));
        return;
    }

    TSharedPtr<FJsonObject> MessageObj;
    if (ChoiceObj->HasField(TEXT("message")))
    {
        MessageObj = ChoiceObj->GetObjectField(TEXT("message"));
    }

    if (!MessageObj.IsValid())
    {
        OnError.Broadcast(TEXT("DirectOllama choices[0] did not contain 'message'."));
        return;
    }

    FString AssistantText;
    if (!MessageObj->TryGetStringField(TEXT("content"), AssistantText))
    {
        OnError.Broadcast(TEXT("DirectOllama message did not contain 'content'."));
        return;
    }

    OnAssistantResponse.Broadcast(AssistantText, TEXT(""));
}

void UVRSecretaryComponent::SendViaLocalLlamaCpp(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    // Try to auto-discover a LlamaComponent on the same actor if one was not assigned.
    if (!LlamaComponent && GetOwner())
    {
        LlamaComponent = GetOwner()->FindComponentByClass<ULlamaComponent>();
    }

    if (!LlamaComponent)
    {
        UE_LOG(LogVRSecretary, Warning,
            TEXT("LocalLlamaCpp backend selected but no LlamaComponent found; falling back to Gateway."));
        SendViaGateway(UserText, Config);
        return;
    }

    // Bind to the full-response delegate; remove any previous binding to avoid duplicates.
    LlamaComponent->OnResponseGenerated.RemoveDynamic(this, &UVRSecretaryComponent::HandleLlamaResponse);
    LlamaComponent->OnResponseGenerated.AddDynamic(this, &UVRSecretaryComponent::HandleLlamaResponse);

    FLlamaChatPrompt Prompt;
    Prompt.Prompt           = UserText;
    Prompt.Role             = EChatTemplateRole::User;
    Prompt.bAddAssistantBOS = true;
    Prompt.bGenerateReply   = true;

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending prompt to Local Llama via Llama-Unreal."));
    LlamaComponent->InsertTemplatedPromptStruct(Prompt);
}

void UVRSecretaryComponent::HandleLlamaResponse(const FString& AssistantText)
{
    UE_LOG(LogVRSecretary, Verbose, TEXT("Local Llama response: %s"), *AssistantText);

    OnAssistantResponse.Broadcast(AssistantText, TEXT(""));

    if (LlamaComponent)
    {
        LlamaComponent->OnResponseGenerated.RemoveDynamic(this, &UVRSecretaryComponent::HandleLlamaResponse);
    }
}
