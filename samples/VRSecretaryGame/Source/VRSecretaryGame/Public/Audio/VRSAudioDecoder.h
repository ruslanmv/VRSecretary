// Copyright 2025 VRSecretary Project. Licensed under Apache 2.0.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Sound/SoundWave.h"
#include "VRSAudioDecoder.generated.h"

/**
 * Audio decoder for VRSecretary TTS responses.
 * Converts Base64-encoded WAV audio into USoundWave objects for playback.
 */
UCLASS()
class VRSECRETARYGAME_API UVRSAudioDecoder : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * Decode a Base64-encoded WAV string into a playable USoundWave.
     * 
     * @param Base64String - Base64-encoded WAV audio from backend
     * @return USoundWave ready for playback, or nullptr on error
     * 
     * Requirements:
     * - Input must be valid Base64 WAV (PCM 16-bit, mono/stereo)
     * - Supports 8000-48000 Hz sample rates
     * - Max size: ~10MB decoded (prevents memory issues)
     */
    UFUNCTION(BlueprintCallable, Category = "VRSecretary|Audio", 
              meta = (DisplayName = "Decode Base64 WAV to Sound Wave"))
    static USoundWave* DecodeBase64WavToSoundWave(const FString& Base64String);

private:
    /**
     * Parse WAV header to extract audio parameters.
     * 
     * @param WavData - Raw WAV file bytes
     * @param OutSampleRate - Extracted sample rate (Hz)
     * @param OutNumChannels - Extracted channel count (1=mono, 2=stereo)
     * @param OutBitsPerSample - Bits per sample (8, 16, 24, 32)
     * @param OutDataOffset - Offset to audio data in bytes
     * @param OutDataSize - Size of audio data in bytes
     * @return true if header parsed successfully
     */
    static bool ParseWavHeader(
        const TArray<uint8>& WavData,
        int32& OutSampleRate,
        int32& OutNumChannels,
        int32& OutBitsPerSample,
        int32& OutDataOffset,
        int32& OutDataSize
    );

    /**
     * Read 32-bit integer from byte array (little-endian).
     */
    static int32 ReadInt32(const TArray<uint8>& Data, int32 Offset);

    /**
     * Read 16-bit integer from byte array (little-endian).
     */
    static int16 ReadInt16(const TArray<uint8>& Data, int32 Offset);
};