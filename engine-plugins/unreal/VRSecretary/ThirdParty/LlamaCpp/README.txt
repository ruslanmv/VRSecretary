This is a placeholder for llama.cpp third-party binaries and headers.

To enable true in-engine Local Llama.cpp mode in VRSecretary:

1. Build llama.cpp as a static library for Win64 (or your target platform).
2. Copy the headers into:
   engine-plugins/unreal/VRSecretary/ThirdParty/LlamaCpp/Include
3. Copy the compiled library (.lib) files into:
   engine-plugins/unreal/VRSecretary/ThirdParty/LlamaCpp/Lib/Win64

4. Update VRSecretary.Build.cs to add the library paths and definitions, e.g.:
   - PublicIncludePaths.Add("ThirdParty/LlamaCpp/Include");
   - PublicAdditionalLibraries.Add("ThirdParty/LlamaCpp/Lib/Win64/llama.lib");

5. Replace the stub implementation in SendViaLocalLlamaCpp() with real llama.cpp calls,
   or reuse the patterns from your existing Llama-Unreal plugin.

If you don't need Local Llama.cpp, you can ignore this folder. The Gateway and Direct
Ollama modes work without it.
