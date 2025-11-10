// Copyright 2025 VRSecretary Project. Licensed under Apache 2.0.

#include "Audio/VRSAudioDecoder.h"
#include "Misc/Base64.h"
#include "Sound/SoundWave.h"
#include "AudioDevice.h"

// Logging
DEFINE_LOG_CATEGORY_STATIC(LogVRSAudioDecoder, Log, All);

USoundWave* UVRSAudioDecoder::DecodeBase64WavToSoundWave(const FString& Base64String)
{
    // Validate input
    if (Base64String.IsEmpty())
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("DecodeBase64WavToSoundWave: Empty Base64 string"));
        return nullptr;
    }

    // Step 1: Decode Base64 to raw bytes
    TArray<uint8> WavData;
    if (!FBase64::Decode(Base64String, WavData))
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("DecodeBase64WavToSoundWave: Base64 decode failed"));
        return nullptr;
    }

    // Sanity check: minimum WAV size (44 bytes header)
    if (WavData.Num() < 44)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("DecodeBase64WavToSoundWave: WAV data too small (%d bytes)"), WavData.Num());
        return nullptr;
    }

    // Step 2: Parse WAV header
    int32 SampleRate = 0;
    int32 NumChannels = 0;
    int32 BitsPerSample = 0;
    int32 DataOffset = 0;
    int32 DataSize = 0;

    if (!ParseWavHeader(WavData, SampleRate, NumChannels, BitsPerSample, DataOffset, DataSize))
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("DecodeBase64WavToSoundWave: Failed to parse WAV header"));
        return nullptr;
    }

    UE_LOG(LogVRSAudioDecoder, Verbose, 
           TEXT("Parsed WAV: %d Hz, %d channels, %d bits/sample, %d bytes data"),
           SampleRate, NumChannels, BitsPerSample, DataSize);

    // Step 3: Validate parameters
    if (SampleRate < 8000 || SampleRate > 48000)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid sample rate: %d Hz"), SampleRate);
        return nullptr;
    }

    if (NumChannels < 1 || NumChannels > 2)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid channel count: %d"), NumChannels);
        return nullptr;
    }

    if (BitsPerSample != 16)
    {
        UE_LOG(LogVRSAudioDecoder, Error, 
               TEXT("Unsupported bits per sample: %d (only 16-bit PCM supported)"), 
               BitsPerSample);
        return nullptr;
    }

    // Step 4: Create USoundWave
    USoundWave* SoundWave = NewObject<USoundWave>(GetTransientPackage(), NAME_None, RF_Transient);
    if (!SoundWave)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Failed to create USoundWave object"));
        return nullptr;
    }

    // Step 5: Configure SoundWave properties
    SoundWave->SetSampleRate(SampleRate);
    SoundWave->NumChannels = NumChannels;
    SoundWave->Duration = (float)DataSize / (float)(SampleRate * NumChannels * 2); // 2 bytes per sample (16-bit)
    SoundWave->RawPCMDataSize = DataSize;
    SoundWave->SoundGroup = SOUNDGROUP_Default;

    // Step 6: Copy audio data to SoundWave
    // Unreal expects raw PCM data without WAV header
    const int32 AudioDataSize = WavData.Num() - DataOffset;
    if (AudioDataSize != DataSize)
    {
        UE_LOG(LogVRSAudioDecoder, Warning, 
               TEXT("Data size mismatch: header says %d, actual %d"), 
               DataSize, AudioDataSize);
        // Use smaller value to be safe
        DataSize = FMath::Min(DataSize, AudioDataSize);
    }

    // Allocate and copy PCM data
    SoundWave->RawPCMData = (uint8*)FMemory::Malloc(DataSize);
    if (!SoundWave->RawPCMData)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Failed to allocate %d bytes for PCM data"), DataSize);
        return nullptr;
    }

    FMemory::Memcpy(SoundWave->RawPCMData, WavData.GetData() + DataOffset, DataSize);

    // Step 7: Finalize SoundWave
    SoundWave->InvalidateCompressedData();

    UE_LOG(LogVRSAudioDecoder, Log, 
           TEXT("Successfully created SoundWave: %.2f seconds, %d Hz, %d channels"),
           SoundWave->Duration, SampleRate, NumChannels);

    return SoundWave;
}

bool UVRSAudioDecoder::ParseWavHeader(
    const TArray<uint8>& WavData,
    int32& OutSampleRate,
    int32& OutNumChannels,
    int32& OutBitsPerSample,
    int32& OutDataOffset,
    int32& OutDataSize)
{
    // WAV file structure:
    // Offset | Size | Description
    // -------|------|-------------
    // 0      | 4    | "RIFF"
    // 4      | 4    | File size - 8
    // 8      | 4    | "WAVE"
    // 12     | 4    | "fmt "
    // 16     | 4    | Format chunk size (16 for PCM)
    // 20     | 2    | Audio format (1 = PCM)
    // 22     | 2    | Num channels
    // 24     | 4    | Sample rate
    // 28     | 4    | Byte rate
    // 32     | 2    | Block align
    // 34     | 2    | Bits per sample
    // 36     | 4    | "data"
    // 40     | 4    | Data size

    // Check RIFF header
    if (WavData[0] != 'R' || WavData[1] != 'I' || WavData[2] != 'F' || WavData[3] != 'F')
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid WAV: Missing RIFF header"));
        return false;
    }

    // Check WAVE format
    if (WavData[8] != 'W' || WavData[9] != 'A' || WavData[10] != 'V' || WavData[11] != 'E')
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid WAV: Missing WAVE format"));
        return false;
    }

    // Check fmt chunk
    if (WavData[12] != 'f' || WavData[13] != 'm' || WavData[14] != 't' || WavData[15] != ' ')
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid WAV: Missing fmt chunk"));
        return false;
    }

    // Read format chunk size
    const int32 FmtChunkSize = ReadInt32(WavData, 16);
    if (FmtChunkSize < 16)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid WAV: fmt chunk too small"));
        return false;
    }

    // Read audio format (must be 1 for PCM)
    const int16 AudioFormat = ReadInt16(WavData, 20);
    if (AudioFormat != 1)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Unsupported WAV format: %d (only PCM=1 supported)"), AudioFormat);
        return false;
    }

    // Read audio parameters
    OutNumChannels = ReadInt16(WavData, 22);
    OutSampleRate = ReadInt32(WavData, 24);
    OutBitsPerSample = ReadInt16(WavData, 34);

    // Find data chunk (might not be at offset 36 if there are extra chunks)
    int32 Offset = 36;
    bool FoundData = false;

    while (Offset + 8 <= WavData.Num())
    {
        // Read chunk ID
        if (WavData[Offset] == 'd' && WavData[Offset + 1] == 'a' && 
            WavData[Offset + 2] == 't' && WavData[Offset + 3] == 'a')
        {
            // Found data chunk
            OutDataSize = ReadInt32(WavData, Offset + 4);
            OutDataOffset = Offset + 8;
            FoundData = true;
            break;
        }

        // Skip this chunk
        const int32 ChunkSize = ReadInt32(WavData, Offset + 4);
        Offset += 8 + ChunkSize;
    }

    if (!FoundData)
    {
        UE_LOG(LogVRSAudioDecoder, Error, TEXT("Invalid WAV: Missing data chunk"));
        return false;
    }

    return true;
}

int32 UVRSAudioDecoder::ReadInt32(const TArray<uint8>& Data, int32 Offset)
{
    if (Offset + 4 > Data.Num())
    {
        return 0;
    }

    // Little-endian read
    return (int32)Data[Offset] |
           ((int32)Data[Offset + 1] << 8) |
           ((int32)Data[Offset + 2] << 16) |
           ((int32)Data[Offset + 3] << 24);
}

int16 UVRSAudioDecoder::ReadInt16(const TArray<uint8>& Data, int32 Offset)
{
    if (Offset + 2 > Data.Num())
    {
        return 0;
    }

    // Little-endian read
    return (int16)Data[Offset] | ((int16)Data[Offset + 1] << 8);
}