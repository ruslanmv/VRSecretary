using UnrealBuildTool;

public class VRSecretary : ModuleRules
{
    public VRSecretary(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "HTTP",
                "Json",
                "JsonUtilities"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "Projects",
                "DeveloperSettings"
            }
        );

        // feature flags
        PublicDefinitions.Add("VRSECRETARY_WITH_GATEWAY=1");
        PublicDefinitions.Add("VRSECRETARY_WITH_DIRECT_OLLAMA=1");
        PublicDefinitions.Add("VRSECRETARY_WITH_LOCAL_LLAMA_STUB=1");
    }
}
