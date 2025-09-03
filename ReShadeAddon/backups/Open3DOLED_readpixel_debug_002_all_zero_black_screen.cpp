#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>
#include <atomic>
#include <chrono>
#include <sstream>
#include <iomanip>

// Debug-heavy version: create a full-size staging texture (same size as backbuffer)
// and copy the entire backbuffer into it. Dump mapped bytes and sample a few pixels.

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;
static reshade::api::resource staging = {}; // host-readable resource (GPU->CPU)
static reshade::api::resource_desc staging_desc = {};
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
    size_t pos = exe_path.find_last_of(L"\/");
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

static const char* format_to_string(reshade::api::format f)
{
    using fmt = reshade::api::format;
    switch (f)
    {
    case fmt::unknown: return "unknown";
    case fmt::r8g8b8a8_unorm: return "r8g8b8a8_unorm";
    case fmt::r8g8b8a8_unorm_srgb: return "r8g8b8a8_unorm_srgb";
    case fmt::b8g8r8a8_unorm: return "b8g8r8a8_unorm";
    case fmt::b8g8r8a8_unorm_srgb: return "b8g8r8a8_unorm_srgb";
    case fmt::r10g10b10a2_unorm: return "r10g10b10a2_unorm";
    case fmt::r16g16b16a16_float: return "r16g16b16a16_float";
    case fmt::r32g32b32a32_float: return "r32g32b32a32_float";
        // add cases here for any formats you want to recognize
    default: return "FORMAT_#(unknown)";
    }
}

static void on_init_swapchain(reshade::api::swapchain* swapchain, bool)
{
    auto device = swapchain->get_device();
    auto bb = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(bb);

    // destroy previous staging if present
    if (staging.handle != 0)
    {
        device->destroy_resource(staging);
        staging = {};
        staging_desc = {};
    }

    // Log backbuffer characteristics
    std::wstringstream ss;
    ss << L"Backbuffer: w=" << bb_desc.texture.width << L" h=" << bb_desc.texture.height
        << L" fmt=" << (int)bb_desc.texture.format << L"(" << format_to_string(bb_desc.texture.format) << L")"
        << L" samples=" << bb_desc.texture.samples
        << L" heap=" << (int)bb_desc.heap
        << L" usage_bits=" << (int)bb_desc.usage;
    log_info(ss.str());

    // Create a staging resource that matches the backbuffer size & format (full size)
    reshade::api::resource_desc tex_desc = {};
    tex_desc.type = reshade::api::resource_type::texture_2d;
    tex_desc.texture.width = bb_desc.texture.width;
    tex_desc.texture.height = bb_desc.texture.height;
    tex_desc.texture.depth_or_layers = 1;
    tex_desc.texture.levels = 1;
    tex_desc.texture.format = bb_desc.texture.format;
    tex_desc.texture.samples = 1; // single-sample staging
    tex_desc.heap = reshade::api::memory_heap::gpu_to_cpu;
    tex_desc.usage = reshade::api::resource_usage::copy_dest;

    if (!device->create_resource(tex_desc, nullptr, reshade::api::resource_usage::copy_dest, &staging))
    {
        log_info(L"Unable to create readback (staging) texture resource. create_resource failed.");
        staging = {};
        return;
    }

    staging_desc = tex_desc;
    log_info(L"Created full-size staging texture for debug readback.");
}

static void on_destroy_swapchain(reshade::api::swapchain* swapchain, bool)
{
    if (staging.handle != 0)
    {
        swapchain->get_device()->destroy_resource(staging);
        staging = {};
        staging_desc = {};
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

static bool extract_rgb_from_row(const uint8_t* row, reshade::api::format fmt, uint8_t out_rgb[3])
{
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
        // fallback: take first 3 bytes
        out_rgb[0] = row[0];
        out_rgb[1] = row[1];
        out_rgb[2] = row[2];
        return true;
    }
}

static void sample_mapped(const reshade::api::subresource_data& mapped, const reshade::api::resource_desc& desc)
{
    if (mapped.data == nullptr) return;

    // Dump the first 128 bytes for analysis
    const size_t dump_len = 128;
    dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped.data), std::min<size_t>(dump_len, mapped.row_pitch * 2), mapped.row_pitch, mapped.slice_pitch);

    // Sample pixel at (0,0)
    const uint8_t* base = reinterpret_cast<const uint8_t*>(mapped.data);
    uint8_t rgb[3] = { 0,0,0 };
    if (mapped.row_pitch >= 4)
    {
        extract_rgb_from_row(base, desc.texture.format, rgb);
    }

    // Sample pixel at center (if available)
    uint8_t rgb_center[3] = { 0,0,0 };
    if (desc.texture.width > 2 && desc.texture.height > 2)
    {
        uint32_t cx = desc.texture.width / 2;
        uint32_t cy = desc.texture.height / 2;
        const uint8_t* row = base + (size_t)mapped.row_pitch * cy;
        const uint8_t* p = row + (size_t)(cx * 4); // assume 4 bytes per pixel for typical formats
        extract_rgb_from_row(p, desc.texture.format, rgb_center);
    }

    std::ostringstream ss;
    ss << "Sample top-left: " << (int)rgb[0] << "," << (int)rgb[1] << "," << (int)rgb[2]
        << " | center: " << (int)rgb_center[0] << "," << (int)rgb_center[1] << "," << (int)rgb_center[2];
    log_a(ss.str());
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

    // Try to transition to copy_source / perform copy of full resource
    reshade::api::command_list* cmd = queue->get_immediate_command_list();

    // Insert barrier to copy_source
    cmd->barrier(backbuffer, reshade::api::resource_usage::present, reshade::api::resource_usage::copy_source);

    // Copy whole backbuffer into staging (dst = staging, src = backbuffer)
    cmd->copy_texture_region(staging, 0, nullptr, backbuffer, 0, nullptr);

    // Optional: restore state after copy
    cmd->barrier(backbuffer, reshade::api::resource_usage::copy_source, reshade::api::resource_usage::present);

    // flush/wait
    queue->flush_immediate_command_list();
    queue->wait_idle();

    reshade::api::subresource_data mapped = {};
    if (!device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        log_info(L"Unable to map readback texture region (full-size staging).");
        return;
    }

    // Dump and sample
    sample_mapped(mapped, staging_desc);

    // Also write a short hex line for quick visual inspection
    dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped.data), 32, mapped.row_pitch, mapped.slice_pitch);

    // Unmap
    device->unmap_texture_region(staging, 0);

    // Send serial based on top-left sample (as before)
    // For safety, re-map quickly to extract exact bytes into trigger calc
    if (!device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        // unable to map, just skip serial send
        return;
    }
    uint8_t rgb[3] = { 0,0,0 };
    if (mapped.row_pitch >= 4)
    {
        const uint8_t* base = reinterpret_cast<const uint8_t*>(mapped.data);
        extract_rgb_from_row(base, staging_desc.texture.format, rgb);
    }
    device->unmap_texture_region(staging, 0);

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
            staging_desc = {};
        }

        reshade::unregister_addon(hModule);
    }

    return TRUE;
}
