#pragma once

#include "CoreMinimal.h"
#include "VRSecretaryChatTypes.generated.h"

USTRUCT(BlueprintType)
struct FVRSecretaryChatMessage
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "VRSecretary")
    FString Role;

    UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "VRSecretary")
    FString Content;
};

USTRUCT(BlueprintType)
struct FVRSecretaryChatResponse
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "VRSecretary")
    FString AssistantText;

    UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "VRSecretary")
    FString AudioWavBase64;
};
