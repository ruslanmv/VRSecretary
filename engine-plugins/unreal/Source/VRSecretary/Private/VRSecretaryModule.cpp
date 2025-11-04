#include "Modules/ModuleManager.h"
#include "Logging/LogMacros.h"

DEFINE_LOG_CATEGORY_STATIC(LogVRSecretary, Log, All);

class FVRSecretaryModule : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
        UE_LOG(LogVRSecretary, Log, TEXT("VRSecretary module starting up"));
    }

    virtual void ShutdownModule() override
    {
        UE_LOG(LogVRSecretary, Log, TEXT("VRSecretary module shutting down"));
    }
};

IMPLEMENT_MODULE(FVRSecretaryModule, VRSecretary)
