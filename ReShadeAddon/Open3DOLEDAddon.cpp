#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;


void log_info(const std::wstring& message)
{
    std::wofstream log("Open3DOLED.log", std::ios::app);
    log << message << std::endl;
}

// Helper to read COM port from ReShade.ini
void read_settings()
{
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(NULL, path, MAX_PATH);

    // Remove executable name
    std::wstring exe_path(path);
    size_t pos = exe_path.find_last_of(L"\\/");
    if (pos != std::wstring::npos)
        exe_path = exe_path.substr(0, pos + 1);

    exe_path += L"Open3DOLED.ini"; // assumes ReShade.ini is next to exe

    wchar_t port[16] = L"COM7"; // default
    GetPrivateProfileStringW(L"OPEN3DOLED", L"COMPort", L"COM3", port, 16, exe_path.c_str());
    sComPort = std::wstring(port);

    iThreshold = GetPrivateProfileIntW(L"OPEN3DOLED", L"Threshold", 30, exe_path.c_str());

    log_info(L"COM Port: " + sComPort);
    log_info(L"Threshold: " + std::to_wstring(iThreshold));
}

static void open_serial_port()
{
    hSerial = CreateFileW((L"\\\\.\\" + sComPort).c_str(),
        GENERIC_WRITE, 0, nullptr,
        OPEN_EXISTING, 0, nullptr);

    if (hSerial != INVALID_HANDLE_VALUE)
    {
        DCB dcb{};
        dcb.DCBlength = sizeof(dcb);
        GetCommState(hSerial, &dcb);
        dcb.BaudRate = CBR_115200;
        dcb.ByteSize = 8;
        dcb.StopBits = ONESTOPBIT;
        dcb.Parity = NOPARITY;
        SetCommState(hSerial, &dcb);
        log_info(L"Opened COM port: " + sComPort);
    }
    else {
        log_info(L"Failed to open COM port: " + sComPort);
    }
}

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*,
    uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE)
        return;

    auto device = swapchain->get_device();
    reshade::api::resource backbuffer = swapchain->get_current_back_buffer();

    reshade::api::resource_desc bb_desc = device->get_resource_desc(backbuffer);

    reshade::api::resource_desc desc = {};
    desc.type = reshade::api::resource_type::texture_2d;
    desc.texture.width = 1;
    desc.texture.height = 1;
    desc.texture.depth_or_layers = 1;
    desc.texture.levels = 1;
    desc.texture.format = bb_desc.texture.format;
    desc.heap = reshade::api::memory_heap::cpu_to_gpu;
    desc.usage = reshade::api::resource_usage::copy_dest | reshade::api::resource_usage::cpu_access;

    reshade::api::resource staging = {};
    if (!device->create_resource(desc, nullptr, reshade::api::resource_usage::copy_dest, &staging))
        return;

    reshade::api::command_list* cmd = queue->get_immediate_command_list();
    reshade::api::subresource_box box = { 0,0,0,1,1,1 };
    cmd->copy_texture_region(backbuffer, 0, nullptr, staging, 0, &box);

    reshade::api::subresource_data mapped = {};
    if (device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        char msg[64];
        const uint8_t* rgba = reinterpret_cast<const uint8_t*>(mapped.data);
        const uint16_t trigger_brightness = rgba[0] + rgba[1] + rgba[2];
        if (trigger_brightness > iThreshold) {
            sprintf_s(msg, "9, 0\n");
        }
        else {
            sprintf_s(msg, "9, 1\n");
        }

        DWORD written;
        WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);

        device->unmap_texture_region(staging, 0);
    }

    device->destroy_resource(staging);
}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID)
{
    if (fdwReason == DLL_PROCESS_ATTACH)
    {
        read_settings();
        open_serial_port();

        reshade::register_event<reshade::addon_event::present>(on_present);
    }
    else if (fdwReason == DLL_PROCESS_DETACH)
    {
        if (hSerial != INVALID_HANDLE_VALUE)
            CloseHandle(hSerial);
    }

    return TRUE;
}
