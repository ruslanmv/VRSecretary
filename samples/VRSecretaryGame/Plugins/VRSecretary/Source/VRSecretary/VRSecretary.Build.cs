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
                "JsonUtilities",
                "LlamaCore"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "Projects",
                "DeveloperSettings"
            }
        );

        // If you wire in llama.cpp directly as a static third-party library instead of
        // using the Llama-Unreal plugin, you can add includes / libs here, e.g.:
        //
        // PublicIncludePaths.Add("ThirdParty/LlamaCpp/Include");
        // PublicAdditionalLibraries.Add("ThirdParty/LlamaCpp/Lib/Win64/llama.lib");
    }
}
