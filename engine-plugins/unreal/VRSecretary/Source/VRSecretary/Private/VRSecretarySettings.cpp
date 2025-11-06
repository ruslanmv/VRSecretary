#include "VRSecretarySettings.h"
#include "VRSecretaryLog.h"

UVRSecretarySettings::UVRSecretarySettings()
{
    CategoryName = TEXT("Plugins");
    SectionName  = TEXT("VRSecretary");

    // Default backend: go through the FastAPI gateway using Ollama
    BackendMode       = EVRSecretaryBackendMode::GatewayOllama;

    // Default gateway / LLM addresses
    GatewayUrl        = TEXT("http://localhost:8000");
    HttpTimeout       = 60.0f;
    DirectOllamaUrl   = TEXT("http://localhost:11434");
    DirectOllamaModel = TEXT("llama3");

    // NEW: default TTS language for the whole project (ISO 639-1)
    // This is forwarded by the gateway to the multilingual TTS server when
    // no per-request override is provided.
    DefaultLanguage   = TEXT("en");

    UE_LOG(LogVRSecretary, Verbose, TEXT("UVRSecretarySettings constructed"));
}

FName UVRSecretarySettings::GetCategoryName() const
{
    // Show under Project Settings → Plugins
    return FName(TEXT("Plugins"));
}
