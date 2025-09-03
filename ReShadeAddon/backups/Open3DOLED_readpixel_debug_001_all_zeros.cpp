#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>
#include <atomic>
#include <chrono>
#include <sstream>
#include <iomanip>

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;
static reshade::api::resource staging = {}; // host-readable resource (GPU->CPU)
static std::chrono::steady_clock::time_point last_log_time = std::chrono::steady_clock::now();

// Atomic counters for thread safety
static std::atomic<uint32_t> left_eye_count(0);
static std::atomic<uint32_t> right_eye_count(0);

// Simple logging helpers
static void log_w(const std::wstring& msg)
{
    std::wofstream f("Open3DOLED.log", std::ios::app);
    f << msg << std::endl;
}
static void log_a(const std::string& msg)
{
    std::ofstream f("Open3DOLED_hex.log", std::ios::app);
    f << msg << std::endl;
}

void log_info(const std::wstring& message)
{
    log_w(message);
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
    GetPrivateProfileStringW(L"OPEN3DOLED", L"COMPort", L"COM7", port, 16, exe_path.c_str());
    sComPort = std::wstring(port);

    iThreshold = GetPrivateProfileIntW(L"OPEN3DOLED", L"Threshold", 30, exe_path.c_str());

    log_info(L"COM Port: " + sComPort);
    log_info(L"Threshold: " + std::to_wstring(iThreshold));
}

static void open_serial_port()
{
    hSerial = CreateFileW((L"\\.\\" + sComPort).c_str(),
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

    if (staging.handle != 0)
    {
        device->destroy_resource(staging);
        staging = {};
    }

    if (bb_desc.texture.samples != 1)
    {
        log_info(L"Backbuffer is multisampled (MSAA); single-pixel readback not supported in this build.");
        return;
    }

    using format = reshade::api::format;
    const auto bbfmt = bb_desc.texture.format;
    const bool supportedFormat =
        (bbfmt == format::r8g8b8a8_unorm || bbfmt == format::r8g8b8a8_unorm_srgb ||
            bbfmt == format::b8g8r8a8_unorm || bbfmt == format::b8g8r8a8_unorm_srgb);

    if (!supportedFormat)
    {
        // Still create a staging with same format to allow hex dumps for debugging
        log_info(L"Backbuffer format not recognized as common 8-bit RGBA. Creating staging anyway for debug.");
    }

    reshade::api::resource_desc tex_desc = {};
    tex_desc.type = reshade::api::resource_type::texture_2d;
    tex_desc.texture.width = 1;
    tex_desc.texture.height = 1;
    tex_desc.texture.depth_or_layers = 1;
    tex_desc.texture.levels = 1;
    tex_desc.texture.format = bb_desc.texture.format;
    tex_desc.texture.samples = 1;
    tex_desc.heap = reshade::api::memory_heap::gpu_to_cpu;
    tex_desc.usage = reshade::api::resource_usage::copy_dest;

    if (!device->create_resource(tex_desc, nullptr, reshade::api::resource_usage::copy_dest, &staging))
    {
        log_info(L"Unable to create readback (staging) texture resource. create_resource failed.");
        staging = {};
        return;
    }

    log_info(L"Staging 1x1 readback texture created (debug build).");
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

// Dump raw mapped memory (hex) for debugging
static void dump_mapped_hex(const uint8_t* data, size_t length, uint32_t row_pitch, uint32_t slice_pitch)
{
    std::ostringstream ss;
    ss << "Timestamp: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    ss << " | row_pitch=" << row_pitch << " slice_pitch=" << slice_pitch << " | ";
    for (size_t i = 0; i < length; ++i)
    {
        if (i) ss << ' ';
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)data[i];
    }
    log_a(ss.str());
}

static bool extract_rgb_from_mapped(const reshade::api::subresource_data& mapped, reshade::api::format fmt, uint8_t out_rgb[3])
{
    if (mapped.data == nullptr) return false;
    const uint8_t* row = reinterpret_cast<const uint8_t*>(mapped.data);

    using format = reshade::api::format;
    switch (fmt)
    {
    case format::r8g8b8a8_unorm:
    case format::r8g8b8a8_unorm_srgb:
        out_rgb[0] = row[0];
        out_rgb[1] = row[1];
        out_rgb[2] = row[2];
        return true;
    case format::b8g8r8a8_unorm:
    case format::b8g8r8a8_unorm_srgb:
        out_rgb[0] = row[2];
        out_rgb[1] = row[1];
        out_rgb[2] = row[0];
        return true;
    default:
        // Generic fallback: if bytes_per_pixel >= 3, use first three bytes
        // This helps when the format is something unknown but still 8bpc.
        // We also dump memory so you can inspect it in Open3DOLED_hex.log
        out_rgb[0] = row[0];
        out_rgb[1] = (mapped.row_pitch > 1 ? row[1] : 0);
        out_rgb[2] = (mapped.row_pitch > 2 ? row[2] : 0);
        return true;
    }
}

static void copy_and_read_pixel(reshade::api::command_list* cmd, reshade::api::command_queue* queue, reshade::api::resource backbuffer, reshade::api::resource_desc bb_desc, uint32_t src_x, uint32_t src_y)
{
    // Build source box (left,top,front, right,bottom,back)
    reshade::api::subresource_box src_box = { src_x, src_y, 0, src_x + 1, src_y + 1, 1 };

    // Copy from backbuffer (SRC) into staging (DEST)
    cmd->copy_texture_region(staging, 0, nullptr, backbuffer, 0, &src_box);

    // Flush and wait to ensure copy finished
    queue->flush_immediate_command_list();
    queue->wait_idle();

    // Map and inspect
   // auto device = queue->get_swapchain()->get_device(); // NOTE: swapchain pointer not available here in this helper
}

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*,
    uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE)
    {
        static auto last = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - last).count() > 5)
        {
            log_info(L"No open COM port.");
            last = std::chrono::steady_clock::now();
        }
        return;
    }

    if (staging.handle == 0)
        return;

    auto device = swapchain->get_device();
    auto backbuffer = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(backbuffer);

    if (bb_desc.texture.samples != 1)
        return;

    reshade::api::command_list* cmd = queue->get_immediate_command_list();

    // Try top-left first
    reshade::api::subresource_box src_box = { 0, 0, 0, 1, 1, 1 };
    cmd->copy_texture_region(staging, 0, nullptr, backbuffer, 0, &src_box);
    queue->flush_immediate_command_list();
    queue->wait_idle();

    reshade::api::subresource_data mapped = {};
    if (!device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        log_info(L"Unable to map readback texture region (first attempt).");
        return;
    }

    // Dump some raw bytes for debugging
    const uint32_t dump_len = 64;
    dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped.data), std::min<size_t>(dump_len, (mapped.row_pitch == 0 ? dump_len : mapped.row_pitch)), mapped.row_pitch, mapped.slice_pitch);

    uint8_t rgb[3] = { 0,0,0 };
    bool ok = extract_rgb_from_mapped(mapped, bb_desc.texture.format, rgb);

    // Heuristic: if all three channels are zero, try bottom-left (some APIs have origin differences)
    bool all_zero = (rgb[0] == 0 && rgb[1] == 0 && rgb[2] == 0);

    device->unmap_texture_region(staging, 0);

    if (all_zero)
    {
        // Try bottom-left fallback
        uint32_t y = (bb_desc.texture.height > 0) ? (bb_desc.texture.height - 1) : 0;
        reshade::api::subresource_box src_box2 = { 0, y, 0, 1, y + 1, 1 };
        cmd->copy_texture_region(staging, 0, nullptr, backbuffer, 0, &src_box2);
        queue->flush_immediate_command_list();
        queue->wait_idle();

        reshade::api::subresource_data mapped2 = {};
        if (device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped2))
        {
            dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped2.data), std::min<size_t>(dump_len, (mapped2.row_pitch == 0 ? dump_len : mapped2.row_pitch)), mapped2.row_pitch, mapped2.slice_pitch);
            uint8_t rgb2[3] = { 0,0,0 };
            bool ok2 = extract_rgb_from_mapped(mapped2, bb_desc.texture.format, rgb2);

            if (ok2)
            {
                uint32_t trigger_brightness = (uint32_t)rgb2[0] + (uint32_t)rgb2[1] + (uint32_t)rgb2[2];
                char msg[64];
                if (trigger_brightness > (uint32_t)iThreshold)
                {
                    sprintf_s(msg, "9, 0\n");
                    left_eye_count++;
                }
                else
                {
                    sprintf_s(msg, "9, 1\n");
                    right_eye_count++;
                }
                DWORD written;
                WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);
            }
            device->unmap_texture_region(staging, 0);
        }
        else
        {
            log_info(L"Unable to map readback texture region (second attempt).");
        }
    }
    else if (ok)
    {
        uint32_t trigger_brightness = (uint32_t)rgb[0] + (uint32_t)rgb[1] + (uint32_t)rgb[2];
        char msg[64];
        if (trigger_brightness > (uint32_t)iThreshold)
        {
            sprintf_s(msg, "9, 0\n");
            left_eye_count++;
        }
        else
        {
            sprintf_s(msg, "9, 1\n");
            right_eye_count++;
        }
        DWORD written;
        WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);
    }

    // Log counts once per second
    auto now = std::chrono::steady_clock::now();
    if (std::chrono::duration_cast<std::chrono::seconds>(now - last_log_time).count() >= 1)
    {
        log_info(L"Left eye signals: " + std::to_wstring(left_eye_count.load()) +
            L" | Right eye signals: " + std::to_wstring(right_eye_count.load()));

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

        if (staging.handle != 0)
        {
            // Best-effort cleanup; ReShade should call destroy_swapchain before unload
            staging = {};
        }

        reshade::unregister_addon(hModule);
    }

    return TRUE;
}
