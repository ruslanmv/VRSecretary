using UnrealBuildTool;
using System.Collections.Generic;

public class VRSecretaryGameTarget : TargetRules
{
    public VRSecretaryGameTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V2;
        ExtraModuleNames.AddRange(new string[] { "VRSecretaryGame" });
    }
}
