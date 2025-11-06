This folder is reserved for a future native llama.cpp integration.

At the moment the VRSecretary plugin only contains a "LocalLlamaCpp"
stub and does not link against any llama.cpp static libraries.

If you later decide to ship llama.cpp inside this plugin, you can:
  - place headers under ThirdParty/LlamaCpp/Include
  - place platform libraries under ThirdParty/LlamaCpp/Lib/<Platform>/
  - update VRSecretary.Build.cs to add include paths & libs.
