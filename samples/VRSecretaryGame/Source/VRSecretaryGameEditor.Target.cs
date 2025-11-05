using UnrealBuildTool;
using System.Collections.Generic;

public class VRSecretaryGameEditorTarget : TargetRules
{
    public VRSecretaryGameEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V2;
        ExtraModuleNames.AddRange(new string[] { "VRSecretaryGame" });
    }
}
