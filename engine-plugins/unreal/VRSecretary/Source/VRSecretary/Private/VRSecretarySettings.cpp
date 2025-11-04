#include "VRSecretarySettings.h"

UVRSecretarySettings::UVRSecretarySettings()
{
    CategoryName = TEXT("Plugins");
    SectionName  = TEXT("VRSecretary");

    GatewayUrl        = TEXT("http://localhost:8000");
    BackendMode       = EVRSecretaryBackendMode::GatewayOllama;
    HttpTimeout       = 60.0f;
    DirectOllamaUrl   = TEXT("http://localhost:11434");
    DirectOllamaModel = TEXT("llama3");
}

FName UVRSecretarySettings::GetCategoryName() const
{
    return TEXT("Plugins");
}
