#include "VRSecretarySettings.h"
#include "VRSecretaryLog.h"

UVRSecretarySettings::UVRSecretarySettings()
{
    // Category/section for Project Settings UI
    CategoryName = TEXT("Plugins");
    SectionName  = TEXT("VRSecretary");

    // Defaults
    BackendMode         = EVRSecretaryBackendMode::GatewayOllama;
    GatewayUrl          = TEXT("http://localhost:8000");
    DefaultLanguageCode = TEXT("en");               // Default to English
    HttpTimeout         = 60.0f;
    DirectOllamaUrl     = TEXT("http://localhost:11434");
    DirectOllamaModel   = TEXT("llama3");

    UE_LOG(
        LogVRSecretary,
        Verbose,
        TEXT("UVRSecretarySettings constructed (GatewayUrl=%s, DefaultLanguage=%s)"),
        *GatewayUrl,
        *DefaultLanguageCode
    );
}

FName UVRSecretarySettings::GetCategoryName() const
{
    return FName(TEXT("Plugins"));
}
