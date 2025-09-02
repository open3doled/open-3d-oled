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
static reshade::api::resource staging = {}; // host-readable resource (GPU->CPU)
static std::chrono::steady_clock::time_point last_log_time = std::chrono::steady_clock::now();

// Atomic counters for thread safety
static std::atomic<uint32_t> left_eye_count(0);
static std::atomic<uint32_t> right_eye_count(0);

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

static void on_init_swapchain(reshade::api::swapchain* swapchain, bool)
{
    auto device = swapchain->get_device();
    auto bb = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(bb);

    // If there's an old staging resource destroy it
    if (staging.handle != 0)
    {
        device->destroy_resource(staging);
        staging = {};
    }

    // Only support non-multisampled backbuffers in this simple example
    if (bb_desc.texture.samples != 1)
    {
        log_info(L"Backbuffer is multisampled (MSAA); single-pixel readback not supported in this build.");
        return;
    }

    // Only support typical 8-bit four-channel formats (common backbuffer formats)
    using format = reshade::api::format;
    const auto bbfmt = bb_desc.texture.format;
    const bool supportedFormat =
        (bbfmt == format::r8g8b8a8_unorm || bbfmt == format::r8g8b8a8_unorm_srgb ||
            bbfmt == format::b8g8r8a8_unorm || bbfmt == format::b8g8r8a8_unorm_srgb);

    if (!supportedFormat)
    {
        log_info(L"Backbuffer format not supported for simple 1-pixel readback.");
        return;
    }

    // Create a 1x1 readback (host-visible) texture
    reshade::api::resource_desc tex_desc = {};
    tex_desc.type = reshade::api::resource_type::texture_2d;
    tex_desc.texture.width = 1;
    tex_desc.texture.height = 1;
    tex_desc.texture.depth_or_layers = 1;
    tex_desc.texture.levels = 1;
    tex_desc.texture.format = bb_desc.texture.format;
    tex_desc.texture.samples = 1;
    tex_desc.heap = reshade::api::memory_heap::gpu_to_cpu; // readback heap
    // IMPORTANT: initial usage/state must be copy_dest (don't include cpu_access here).
    // Some backends (DX12) require the resource's initial state to match the readback heap semantics.
    tex_desc.usage = reshade::api::resource_usage::copy_dest;

    if (!device->create_resource(tex_desc, nullptr, reshade::api::resource_usage::copy_dest, &staging))
    {
        log_info(L"Unable to create readback (staging) texture resource. create_resource failed.");
        staging = {};
        return;
    }

    log_info(L"Staging 1x1 readback texture created.");
}

static void on_destroy_swapchain(reshade::api::swapchain* swapchain, bool)
{
    if (staging.handle != 0)
    {
        swapchain->get_device()->destroy_resource(staging);
        staging = {};
        log_info(L"Destroyed staging resource.");
    }
}

// Helper to interpret mapped bytes based on format
static bool extract_rgb_from_mapped(const reshade::api::subresource_data& mapped, reshade::api::format fmt, uint8_t out_rgb[3])
{
    if (mapped.data == nullptr) return false;

    const uint8_t* row = reinterpret_cast<const uint8_t*>(mapped.data);

    using format = reshade::api::format;
    switch (fmt)
    {
    case format::r8g8b8a8_unorm:
    case format::r8g8b8a8_unorm_srgb:
        // layout: R G B A
        out_rgb[0] = row[0];
        out_rgb[1] = row[1];
        out_rgb[2] = row[2];
        return true;
    case format::b8g8r8a8_unorm:
    case format::b8g8r8a8_unorm_srgb:
        // layout: B G R A
        out_rgb[0] = row[2];
        out_rgb[1] = row[1];
        out_rgb[2] = row[0];
        return true;
    default:
        return false;
    }
}

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*,
    uint32_t, const reshade::api::rect*)
{
    // If serial isn't open, don't do anything
    if (hSerial == INVALID_HANDLE_VALUE)
    {
        // Only log once per few seconds to avoid spam
        static auto last = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - last).count() > 5)
        {
            log_info(L"No open COM port.");
            last = std::chrono::steady_clock::now();
        }
        return;
    }

    if (staging.handle == 0)
    {
        // staging either not created or unsupported backbuffer — nothing to do
        return;
    }

    auto device = swapchain->get_device();
    auto backbuffer = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(backbuffer);

    // Quick sanity: only handle non-multisampled 4-channel 8-bit formats here
    if (bb_desc.texture.samples != 1)
    {
        // skip (we logged this earlier in init)
        return;
    }

    using format = reshade::api::format;
    const auto bbfmt = bb_desc.texture.format;
    const bool supportedFormat =
        (bbfmt == format::r8g8b8a8_unorm || bbfmt == format::r8g8b8a8_unorm_srgb ||
            bbfmt == format::b8g8r8a8_unorm || bbfmt == format::b8g8r8a8_unorm_srgb);

    if (!supportedFormat)
    {
        return;
    }

    reshade::api::command_list* cmd = queue->get_immediate_command_list();

    // Copy ONE pixel from the top-left (0,0) of the backbuffer into the 1x1 staging resource.
    // NOTE: copy_texture_region(dest, dest_subresource, dest_box, src, src_subresource, src_box)
    // Destination is the staging resource.
    reshade::api::subresource_box src_box = { 0, 0, 0, 1, 1, 1 };

    // Correct order: staging is DEST, backbuffer is SRC
    cmd->copy_texture_region(staging, 0, nullptr, backbuffer, 0, &src_box);

    // Make sure the immediate command list is flushed and the GPU has finished executing the copy
    // before we attempt to map the readback resource.
    queue->flush_immediate_command_list();
    queue->wait_idle();


    reshade::api::subresource_data mapped = {};
    if (device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        uint8_t rgb[3] = { 0,0,0 };
        if (extract_rgb_from_mapped(mapped, bbfmt, rgb))
        {
            uint32_t trigger_brightness = (uint32_t)rgb[0] + (uint32_t)rgb[1] + (uint32_t)rgb[2];

            log_info(L"Trigger Brightness: " + std::to_wstring(trigger_brightness));
            char msg[64];
            if (trigger_brightness > (uint32_t)iThreshold)
            {
                // Left eye signal
                sprintf_s(msg, "9, 0\n");
                left_eye_count++;
            }
            else
            {
                // Right eye signal
                sprintf_s(msg, "9, 1\n");
                right_eye_count++;
            }

            DWORD written;
            WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);
        }
        else
        {
            log_info(L"Unsupported format when extracting mapped pixel.");
        }

        device->unmap_texture_region(staging, 0);
    }
    else
    {
        log_info(L"Unable to map readback texture region.");
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

        // destroy staging if still present
        if (staging.handle != 0)
        {
            // We cannot call swapchain here; get a device if you need to explicitly destroy.
            // Clean up best-effort: attempt to find device via other means is complex inside DllMain,
            // but ReShade will call destroy_swapchain before DLL unload in normal flows.
            staging = {};
        }

        reshade::unregister_addon(hModule);
    }

    return TRUE;
}
