#include "SoftkeyYT88.h"

#include <cstring>

namespace {

constexpr int kBridgeOk = 0;
constexpr int kBridgeLoadFailed = -10001;
constexpr int kBridgeInvalidArgument = -10002;
constexpr int kBridgeNotInitialized = -10003;

SoftkeyYT88* g_softkey = nullptr;

SoftkeyYT88* ensure_softkey()
{
    if (g_softkey == nullptr) {
        g_softkey = new SoftkeyYT88();
    }
    return g_softkey;
}

}  // namespace

extern "C" {

__declspec(dllexport) int __cdecl DongleBridge_Initialize()
{
    SoftkeyYT88* softkey = ensure_softkey();
    if (softkey == nullptr) {
        return kBridgeNotInitialized;
    }
    return softkey->IsLoad ? kBridgeOk : kBridgeLoadFailed;
}

__declspec(dllexport) int __cdecl DongleBridge_IsLoad()
{
    SoftkeyYT88* softkey = ensure_softkey();
    if (softkey == nullptr) {
        return 0;
    }
    return softkey->IsLoad ? 1 : 0;
}

__declspec(dllexport) int __cdecl DongleBridge_FindPort(char* device_path, int device_path_capacity)
{
    SoftkeyYT88* softkey = ensure_softkey();
    if (softkey == nullptr) {
        return kBridgeNotInitialized;
    }
    if (device_path == nullptr || device_path_capacity <= 0) {
        return kBridgeInvalidArgument;
    }

    std::memset(device_path, 0, static_cast<size_t>(device_path_capacity));
    if (!softkey->IsLoad) {
        return kBridgeLoadFailed;
    }
    return softkey->FindPort(0, device_path);
}

__declspec(dllexport) void __cdecl DongleBridge_Destroy()
{
    delete g_softkey;
    g_softkey = nullptr;
}

}  // extern "C"
