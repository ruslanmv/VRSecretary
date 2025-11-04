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
                "Projects"
            }
        );

        // NOTE:
        // If you wire in llama.cpp as a static third-party library, add it here, e.g.:
        //
        // PublicIncludePaths.Add("ThirdParty/LlamaCpp/Include");
        // PublicAdditionalLibraries.Add("ThirdParty/LlamaCpp/Lib/Win64/llama.lib");
    }
}
