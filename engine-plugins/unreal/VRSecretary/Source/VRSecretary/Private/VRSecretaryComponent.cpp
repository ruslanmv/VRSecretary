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
    BackendModeOverride = EVRSecretaryBackendMode::GatewayOllama;
    LanguageCode = TEXT(""); // Empty = use project default
}

void UVRSecretaryComponent::BeginPlay()
{
    Super::BeginPlay();
    Settings = GetDefault<UVRSecretarySettings>();
    EnsureSessionId();

    const FString EffectiveLang = GetEffectiveLanguageCode();
    UE_LOG(LogVRSecretary, Log, TEXT("VRSecretaryComponent started (Session: %s, Language: %s)"), 
           *SessionId, *EffectiveLang);
}

void UVRSecretaryComponent::EnsureSessionId()
{
    if (SessionId.IsEmpty())
    {
        SessionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
        UE_LOG(LogVRSecretary, Verbose, TEXT("Generated new SessionId: %s"), *SessionId);
    }
}

FString UVRSecretaryComponent::GetEffectiveLanguageCode() const
{
    // Priority:
    // 1. Component's LanguageCode (if set)
    // 2. Project's DefaultLanguageCode (if set)
    // 3. Fall back to "en"

    if (!LanguageCode.IsEmpty())
    {
        return LanguageCode;
    }

    if (Settings && !Settings->DefaultLanguageCode.IsEmpty())
    {
        return Settings->DefaultLanguageCode;
    }

    return TEXT("en"); // Final fallback
}

void UVRSecretaryComponent::SendUserText(const FString& UserText, const FVRSecretaryChatConfig& Config)
{
    if (UserText.IsEmpty())
    {
        UE_LOG(LogVRSecretary, Warning, TEXT("SendUserText: UserText is empty"));
        OnError.Broadcast(TEXT("UserText is empty"));
        return;
    }

    if (!Settings)
    {
        UE_LOG(LogVRSecretary, Error, TEXT("VRSecretary settings not found"));
        OnError.Broadcast(TEXT("VRSecretary settings not found"));
        return;
    }

    EnsureSessionId();

    // Use project-level backend unless this component overrides it
    EVRSecretaryBackendMode Mode = Settings->BackendMode;
    if (BackendModeOverride != EVRSecretaryBackendMode::GatewayOllama)
    {
        Mode = BackendModeOverride;
    }

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
    FString Url = Settings->GatewayUrl;
    Url.RemoveFromEnd(TEXT("/"));
    Url += TEXT("/api/vr_chat");

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    // Build JSON payload with language support
    TSharedPtr<FJsonObject> JsonObject = MakeShared<FJsonObject>();
    JsonObject->SetStringField(TEXT("session_id"), SessionId);
    JsonObject->SetStringField(TEXT("user_text"), UserText);

    // Add language field
    const FString EffectiveLang = GetEffectiveLanguageCode();
    JsonObject->SetStringField(TEXT("language"), EffectiveLang);

    FString Body;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
    Request->SetContentAsString(Body);

    Request->OnProcessRequestComplete().BindUObject(
        this,
        &UVRSecretaryComponent::HandleGatewayResponse
    );
    Request->SetTimeout(Settings->HttpTimeout);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending Gateway request to %s (Language: %s)"), *Url, *EffectiveLang);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleGatewayResponse(
    FHttpRequestPtr Request,
    FHttpResponsePtr Response,
    bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        const FString Error = TEXT("Gateway request failed");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    if (!EHttpResponseCodes::IsOk(Response->GetResponseCode()))
    {
        const FString Error = FString::Printf(
            TEXT("Gateway HTTP %d: %s"),
            Response->GetResponseCode(),
            *Response->GetContentAsString());
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    const FString Content = Response->GetContentAsString();

    TSharedPtr<FJsonObject> JsonObject;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Content);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        const FString Error = TEXT("Failed to parse gateway JSON response");
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

void UVRSecretaryComponent::SendViaDirectOllama(
    const FString& UserText,
    const FVRSecretaryChatConfig& Config)
{
    FString Url = Settings->DirectOllamaUrl;
    Url.RemoveFromEnd(TEXT("/"));
    Url += TEXT("/v1/chat/completions");

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("model"), Settings->DirectOllamaModel);

    TArray<TSharedPtr<FJsonValue>> Messages;

    {
        TSharedPtr<FJsonObject> SysMsg = MakeShared<FJsonObject>();
        SysMsg->SetStringField(TEXT("role"), TEXT("system"));
        SysMsg->SetStringField(
            TEXT("content"),
            TEXT("You are Ailey, a helpful VR secretary inside a virtual office."));
        Messages.Add(MakeShared<FJsonValueObject>(SysMsg));
    }

    {
        TSharedPtr<FJsonObject> UserMsg = MakeShared<FJsonObject>();
        UserMsg->SetStringField(TEXT("role"), TEXT("user"));
        UserMsg->SetStringField(TEXT("content"), UserText);
        Messages.Add(MakeShared<FJsonValueObject>(UserMsg));
    }

    Root->SetArrayField(TEXT("messages"), Messages);
    Root->SetBoolField(TEXT("stream"), false);

    Root->SetNumberField(TEXT("temperature"), Config.Temperature);
    Root->SetNumberField(TEXT("top_p"),       Config.TopP);
    Root->SetNumberField(TEXT("max_tokens"),  Config.MaxTokens);

    FString Body;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Request->SetContentAsString(Body);

    Request->OnProcessRequestComplete().BindUObject(
        this,
        &UVRSecretaryComponent::HandleDirectOllamaResponse
    );
    Request->SetTimeout(Settings->HttpTimeout);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Sending DirectOllama request to %s"), *Url);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleDirectOllamaResponse(
    FHttpRequestPtr Request,
    FHttpResponsePtr Response,
    bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        const FString Error = TEXT("Direct Ollama request failed");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    if (!EHttpResponseCodes::IsOk(Response->GetResponseCode()))
    {
        const FString Error = FString::Printf(
            TEXT("Direct Ollama HTTP %d: %s"),
            Response->GetResponseCode(),
            *Response->GetContentAsString());
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    const FString Content = Response->GetContentAsString();

    TSharedPtr<FJsonObject> JsonObject;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Content);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        const FString Error = TEXT("Failed to parse Ollama JSON response");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    const TArray<TSharedPtr<FJsonValue>>* Choices = nullptr;
    if (!JsonObject->TryGetArrayField(TEXT("choices"), Choices) || !Choices || Choices->Num() == 0)
    {
        const FString Error = TEXT("Ollama response missing choices");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    TSharedPtr<FJsonObject> FirstChoice = (*Choices)[0]->AsObject();
    if (!FirstChoice.IsValid())
    {
        const FString Error = TEXT("Ollama response missing first choice object");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    const TSharedPtr<FJsonObject>* MessageObjPtr = nullptr;
    if (!FirstChoice->TryGetObjectField(TEXT("message"), MessageObjPtr) ||
        !MessageObjPtr ||
        !MessageObjPtr->IsValid())
    {
        const FString Error = TEXT("Ollama response missing message object");
        UE_LOG(LogVRSecretary, Error, TEXT("%s"), *Error);
        OnError.Broadcast(Error);
        return;
    }

    FString AssistantText;
    (*MessageObjPtr)->TryGetStringField(TEXT("content"), AssistantText);

    UE_LOG(LogVRSecretary, Verbose, TEXT("Direct Ollama response text: %s"), *AssistantText);

    OnAssistantResponse.Broadcast(AssistantText, TEXT(""));
}

void UVRSecretaryComponent::SendViaLocalLlamaCpp(
    const FString& UserText,
    const FVRSecretaryChatConfig& /*Config*/)
{
    UE_LOG(
        LogVRSecretary,
        Warning,
        TEXT("LocalLlamaCpp backend is not wired yet; falling back to Gateway.")
    );

    SendViaGateway(UserText);
}