#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>
#include <atomic>
#include <chrono>

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;
static reshade::api::resource staging = {};

// Atomic counters for thread safety
static std::atomic<uint32_t> left_eye_count(0);
static std::atomic<uint32_t> right_eye_count(0);
static auto last_log_time = std::chrono::steady_clock::now();

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

    std::wstring exe_path(path);
    size_t pos = exe_path.find_last_of(L"\\/");
    if (pos != std::wstring::npos)
        exe_path = exe_path.substr(0, pos + 1);

    exe_path += L"Open3DOLED.ini";

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

// Add this before each callback
static void on_init_swapchain(reshade::api::swapchain* swapchain, bool)
{
    auto device = swapchain->get_device();
    auto bb_desc = device->get_resource_desc(swapchain->get_current_back_buffer());

    reshade::api::resource_desc tex_desc = {};
    tex_desc.type = reshade::api::resource_type::texture_2d;
    tex_desc.texture.width = 1;
    tex_desc.texture.height = 1;
    tex_desc.texture.depth_or_layers = 1;
    tex_desc.texture.levels = 1;
    tex_desc.texture.format = bb_desc.texture.format;
    tex_desc.heap = reshade::api::memory_heap::gpu_to_cpu;
    tex_desc.usage = reshade::api::resource_usage::copy_dest | reshade::api::resource_usage::cpu_access;

    if (!device->create_resource(tex_desc, nullptr, reshade::api::resource_usage::copy_dest, &staging))
    {
        log_info(L"Unable to create texture resource.");
    }
}

static void on_destroy_swapchain(reshade::api::swapchain* swapchain, bool)
{
    if (staging.handle != 0)
    {
        swapchain->get_device()->destroy_resource(staging);
        staging = {};
    }
}


static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*,
    uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE)
    {
        log_info(L"No open COM port.");
        return;
    }

    auto device = swapchain->get_device();
    reshade::api::resource backbuffer = swapchain->get_current_back_buffer();

    reshade::api::resource_desc bb_desc = device->get_resource_desc(backbuffer);

    reshade::api::command_list* cmd = queue->get_immediate_command_list();
    reshade::api::subresource_box box = { 0,0,0,1,1,1 };
    cmd->copy_texture_region(backbuffer, 0, nullptr, staging, 0, &box);

    reshade::api::subresource_data mapped = {};
    if (device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        log_info(L"Mapped!!!");
        char msg[64];
        const uint8_t* rgba = reinterpret_cast<const uint8_t*>(mapped.data);
        const uint16_t trigger_brightness = rgba[0] + rgba[1] + rgba[2];

        if (trigger_brightness > iThreshold) {
            // Left eye signal
            sprintf_s(msg, "9, 0\n");
            left_eye_count++;
        }
        else {
            // Right eye signal
            sprintf_s(msg, "9, 1\n");
            right_eye_count++;
        }

        DWORD written;
        WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);

        device->unmap_texture_region(staging, 0);
    }
    else {
        log_info(L"Unable to map texture region.");
    }

    // Log counts once per second
    auto now = std::chrono::steady_clock::now();
    if (std::chrono::duration_cast<std::chrono::seconds>(now - last_log_time).count() >= 1)
    {
        log_info(L"Left eye signals: " + std::to_wstring(left_eye_count.load()) +
            L" | Right eye signals: " + std::to_wstring(right_eye_count.load()));

        // Reset counters
        left_eye_count = 0;
        right_eye_count = 0;
        last_log_time = now;
    }
}

BOOL WINAPI DllMain(HMODULE hModule, DWORD fdwReason, LPVOID)
{
    if (fdwReason == DLL_PROCESS_ATTACH)
    {
        read_settings();
        open_serial_port();

        if (!reshade::register_addon(hModule))
            return FALSE;

        reshade::register_event<reshade::addon_event::present>(on_present);
        reshade::register_event<reshade::addon_event::init_swapchain>(on_init_swapchain);
        reshade::register_event<reshade::addon_event::destroy_swapchain>(on_destroy_swapchain);
    }
    else if (fdwReason == DLL_PROCESS_DETACH)
    {
        if (hSerial != INVALID_HANDLE_VALUE)
            CloseHandle(hSerial);

        reshade::unregister_addon(hModule);
    }

    return TRUE;
}
