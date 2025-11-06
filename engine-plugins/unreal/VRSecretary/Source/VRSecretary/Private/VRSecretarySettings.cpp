#include "VRSecretarySettings.h"
#include "VRSecretaryLog.h"

UVRSecretarySettings::UVRSecretarySettings()
{
    CategoryName = TEXT("Plugins");
    SectionName  = TEXT("VRSecretary");

    BackendMode       = EVRSecretaryBackendMode::GatewayOllama;
    GatewayUrl        = TEXT("http://localhost:8000");
    HttpTimeout       = 60.0f;
    DirectOllamaUrl   = TEXT("http://localhost:11434");
    DirectOllamaModel = TEXT("llama3");

    UE_LOG(LogVRSecretary, Verbose, TEXT("UVRSecretarySettings constructed"));
}

FName UVRSecretarySettings::GetCategoryName() const
{
    return FName(TEXT("Plugins"));
}
