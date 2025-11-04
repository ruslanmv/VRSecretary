#include "VRSecretaryComponent.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Misc/Guid.h"
#include "Json.h"
#include "JsonUtilities.h"

UVRSecretaryComponent::UVRSecretaryComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    BackendMode = EAIBackendMode::GatewayOllama;
    GatewayUrl = TEXT("http://localhost:8000");
}

void UVRSecretaryComponent::BeginPlay()
{
    Super::BeginPlay();

    if (SessionId.IsEmpty())
    {
        SessionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensInBraces);
    }
}

void UVRSecretaryComponent::SendUserText(const FString& UserText)
{
    if (UserText.IsEmpty())
    {
        OnError.Broadcast(TEXT("UserText is empty"));
        return;
    }

    if (BackendMode == EAIBackendMode::LocalLlamaCpp)
    {
        OnError.Broadcast(TEXT("LocalLlamaCpp mode not implemented yet"));
        return;
    }

    SendRequest_Internal(UserText);
}

void UVRSecretaryComponent::SendRequest_Internal(const FString& UserText)
{
    if (GatewayUrl.IsEmpty())
    {
        OnError.Broadcast(TEXT("GatewayUrl is empty"));
        return;
    }

    FString Url = GatewayUrl;
    if (!Url.EndsWith(TEXT("/")))
    {
        Url += TEXT("/");
    }
    Url += TEXT("api/vr_chat");

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedPtr<FJsonObject> JsonObject = MakeShared<FJsonObject>();
    JsonObject->SetStringField(TEXT("session_id"), SessionId);
    JsonObject->SetStringField(TEXT("user_text"), UserText);

    FString Body;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    Request->SetContentAsString(Body);
    Request->OnProcessRequestComplete().BindUObject(this, &UVRSecretaryComponent::HandleHttpResponse);
    Request->ProcessRequest();
}

void UVRSecretaryComponent::HandleHttpResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
    if (!bWasSuccessful || !Response.IsValid())
    {
        OnError.Broadcast(TEXT("HTTP request failed"));
        return;
    }

    if (!EHttpResponseCodes::IsOk(Response->GetResponseCode()))
    {
        const FString ErrorMsg = FString::Printf(TEXT("Gateway HTTP error: %d"), Response->GetResponseCode());
        OnError.Broadcast(ErrorMsg);
        return;
    }

    FString ResponseBody = Response->GetContentAsString();

    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseBody);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        OnError.Broadcast(TEXT("Failed to parse JSON response"));
        return;
    }

    FString AssistantText;
    FString AudioBase64;

    if (!JsonObject->TryGetStringField(TEXT("assistant_text"), AssistantText) ||
        !JsonObject->TryGetStringField(TEXT("audio_wav_base64"), AudioBase64))
    {
        OnError.Broadcast(TEXT("Missing fields in JSON response"));
        return;
    }

    OnResponse.Broadcast(AssistantText, AudioBase64);
}
