#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <atomic>
#include <chrono>

// Render-to-1x1 readback addon
// Approach used here:
// 1) Create a 1x1 GPU render-target/UAV texture (gpu_write_tex) that shaders can write to.
// 2) Create a 1x1 CPU-readable staging texture (staging_readback_tex) in gpu_to_cpu heap.
// 3) On present: sample the swapchain/backbuffer via a small fullscreen draw (or compute) that writes
//    the sampled pixel into gpu_write_tex. Then copy gpu_write_tex -> staging_readback_tex, flush and map.
// 4) Read RGB from mapped staging and use that for serial trigger logic.
// Notes:
// - Pipeline creation & shader compilation details can be backend- and SDK-version-specific. This file
//   attempts a portable, best-effort implementation against common ReShade headers. If your build
//   complains about specific field names for pipeline creation, paste the compile/link errors and I will
//   adapt the pipeline creation code to your ReShade headers.

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;

// GPU resources
static reshade::api::resource gpu_write_tex = {};
static reshade::api::resource staging_readback_tex = {};
static reshade::api::resource_view backbuffer_srv = {};
static reshade::api::resource_view gpu_write_uav = {};
static reshade::api::pipeline draw_pipeline = {};
static reshade::api::pipeline_layout draw_pipeline_layout = {};

static reshade::api::swapchain* g_sc = nullptr;
static std::atomic<uint32_t> left_eye_count(0);
static std::atomic<uint32_t> right_eye_count(0);
static auto last_log_time = std::chrono::steady_clock::now();

void log_info(const std::wstring& s)
{
    std::wofstream f("Open3DOLED.log", std::ios::app);
    f << s << std::endl;
}

void log_hex_line(const std::string& s)
{
    std::ofstream f("Open3DOLED_hex.log", std::ios::app);
    f << s << std::endl;
}

void read_settings()
{
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(NULL, path, MAX_PATH);
    std::wstring exe_path(path);
    size_t pos = exe_path.find_last_of(L"\\");
    if (pos != std::wstring::npos) exe_path = exe_path.substr(0, pos + 1);
    exe_path += L"Open3DOLED.ini";
    wchar_t port[16] = L"COM7";
    GetPrivateProfileStringW(L"OPEN3DOLED", L"COMPort", L"COM7", port, 16, exe_path.c_str());
    sComPort = std::wstring(port);
    iThreshold = GetPrivateProfileIntW(L"OPEN3DOLED", L"Threshold", 30, exe_path.c_str());
    log_info(L"COM Port: " + sComPort);
    log_info(L"Threshold: " + std::to_wstring(iThreshold));
}

static void open_serial_port()
{
    hSerial = CreateFileW((L"\\\\.\\" + sComPort).c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr);
    if (hSerial != INVALID_HANDLE_VALUE)
    {
        DCB dcb{};
        dcb.DCBlength = sizeof(dcb);
        GetCommState(hSerial, &dcb);
        dcb.BaudRate = CBR_115200; dcb.ByteSize = 8; dcb.StopBits = ONESTOPBIT; dcb.Parity = NOPARITY;
        SetCommState(hSerial, &dcb);
        log_info(L"Opened COM port: " + sComPort);
    }
    else log_info(L"Failed to open COM port: " + sComPort);
}

// Simple helper to dump the first N bytes of mapped memory as hex
static void dump_mapped_hex(const uint8_t* data, size_t len, uint32_t row_pitch)
{
    std::ostringstream ss;
    ss << "Timestamp: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    ss << " | row_pitch=" << row_pitch << " | ";
    for (size_t i = 0; i < len; ++i)
    {
        if (i) ss << ' ';
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)data[i];
    }
    log_hex_line(ss.str());
}

// Small pixel shader source (HLSL) to sample backbuffer and write to UAV 1x1 texture.
// We'll sample using integer Load to avoid filtering.
static const char ps_source_rgb_to_uav[] = R"delimiter(
Texture2D<float4> src : register(t0);
RWTexture2D<uint4> dst : register(u0);
cbuffer Push { uint px; uint py; uint width; uint height; };

float4 main_ps(uint2 coord : SV_Position) : SV_Target
{
    // Not used in this simple compute-like pixel shader flow; we will use a draw call with a fullscreen quad
    return float4(0,0,0,0);
}

// Compute equivalent (HLSL) - prefer compute for direct UAV writes
[numthreads(1,1,1)]
void main(uint3 id : SV_DispatchThreadID)
{
    float4 c = src.Load(int3(px, py, 0));
    uint r = (uint)(saturate(c.r) * 255.0f);
    uint g = (uint)(saturate(c.g) * 255.0f);
    uint b = (uint)(saturate(c.b) * 255.0f);
    dst[id.xy].xyz = uint3(r, g, b);
}
)delimiter";

// Try to create 1x1 GPU texture (UAV writable). If this fails on some backends, we'll try a slightly different usage combo.
static bool create_gpu_write_texture(reshade::api::device* device, reshade::api::format fmt)
{
    reshade::api::resource_desc desc = {};
    desc.type = reshade::api::resource_type::texture_2d;
    desc.texture.width = 1;
    desc.texture.height = 1;
    desc.texture.depth_or_layers = 1;
    desc.texture.levels = 1;
    desc.texture.format = fmt;
    desc.texture.samples = 1;
    desc.heap = reshade::api::memory_heap::gpu_only;
    desc.usage = reshade::api::resource_usage::unordered_access | reshade::api::resource_usage::copy_source | reshade::api::resource_usage::shader_resource;

    if (!device->create_resource(desc, nullptr, reshade::api::resource_usage::unordered_access, &gpu_write_tex))
    {
        log_info(L"Failed to create gpu_write_tex with unordered_access. Trying without shader_resource flag...");
        desc.usage = reshade::api::resource_usage::unordered_access | reshade::api::resource_usage::copy_source;
        if (!device->create_resource(desc, nullptr, reshade::api::resource_usage::unordered_access, &gpu_write_tex))
        {
            log_info(L"Failed to create gpu_write_tex with alternate usage flags.");
            gpu_write_tex = {};
            return false;
        }
    }

    // Create UAV view for the texture (platform-specific; attempt generic view creation)
    reshade::api::resource_view_desc view_desc = {};
    view_desc.format = fmt;
    // view_desc.type = reshade::api::resource_view_type::unordered_access_view;
    view_desc.type = reshade::api::resource_view_type::texture_2d;
    view_desc.texture.first_level = 0;
    view_desc.texture.level_count = 1;
    view_desc.texture.first_layer = 0;
    view_desc.texture.layer_count = 1;
    device->create_resource_view(gpu_write_tex, reshade::api::resource_usage::unordered_access, view_desc, &gpu_write_uav);

    return true;
}

static bool create_staging_readback_texture(reshade::api::device* device, reshade::api::format fmt)
{
    reshade::api::resource_desc desc = {};
    desc.type = reshade::api::resource_type::texture_2d;
    desc.texture.width = 1;
    desc.texture.height = 1;
    desc.texture.depth_or_layers = 1;
    desc.texture.levels = 1;
    desc.texture.format = fmt;
    desc.texture.samples = 1;
    desc.heap = reshade::api::memory_heap::gpu_to_cpu;
    desc.usage = reshade::api::resource_usage::copy_dest;

    if (!device->create_resource(desc, nullptr, reshade::api::resource_usage::copy_dest, &staging_readback_tex))
    {
        log_info(L"Failed to create staging_readback_tex.");
        staging_readback_tex = {};
        return false;
    }

    return true;
}

// Simple function to dispatch a compute shader-like program that samples the backbuffer at (x,y)
// and writes the RGB into gpu_write_tex via its UAV view. This code is intentionally high-level
// because exact descriptor update & pipeline creation calls depend on the ReShade header version.
static bool dispatch_sample_and_read(reshade::api::device* device, reshade::api::command_queue* queue, reshade::api::resource backbuffer, uint32_t px, uint32_t py, uint8_t out_rgb[3])
{
    if (gpu_write_tex.handle == 0 || staging_readback_tex.handle == 0) return false;

    reshade::api::command_list* cmd = queue->get_immediate_command_list();

    // Transition backbuffer to shader_resource (so shader can sample it)
    cmd->barrier(backbuffer, reshade::api::resource_usage::present, reshade::api::resource_usage::shader_resource);

    // Transition gpu_write_tex to unordered_access (writeable)
    cmd->barrier(gpu_write_tex, reshade::api::resource_usage::copy_source, reshade::api::resource_usage::unordered_access);

    // TODO: bind pipeline + descriptor sets
    // We will pseudocode the dispatch since the exact API calls to bind descriptors vary by ReShade version.
    // The key actions that must happen here are:
    //  - set shader resource view for backbuffer
    //  - set unordered access view for gpu_write_tex
    //  - set push constants or constant buffer with px/py
    //  - dispatch compute with (1,1,1)

    // PSEUDO: bind + dispatch
    // cmd->bind_pipeline(draw_pipeline);
    // cmd->bind_pipeline_layout(draw_pipeline_layout);
    // update descriptor sets: t0 -> backbuffer SRV, u0 -> gpu_write_uav
    // update push constants: px,py
    // cmd->dispatch(1,1,1);

    // After dispatch, ensure UAV writes are available to copy
    cmd->barrier(gpu_write_tex, reshade::api::resource_usage::unordered_access, reshade::api::resource_usage::copy_source);

    // Copy gpu_write_tex -> staging_readback_tex
    cmd->copy_texture_region(staging_readback_tex, 0, nullptr, gpu_write_tex, 0, nullptr);

    // Restore backbuffer to present
    cmd->barrier(backbuffer, reshade::api::resource_usage::shader_resource, reshade::api::resource_usage::present);

    // flush and wait
    queue->flush_immediate_command_list();
    queue->wait_idle();

    // Map staging and read bytes
    reshade::api::subresource_data mapped = {};
    if (!device->map_texture_region(staging_readback_tex, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        log_info(L"Failed to map staging_readback_tex");
        return false;
    }

    // Dump first 16 bytes for debugging
    dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped.data), 12, mapped.row_pitch);

    const uint8_t* row = reinterpret_cast<const uint8_t*>(mapped.data);
    out_rgb[0] = row[2]; // backbuffer is b8g8r8x8 or b8g8r8a8 so ordering may be B G R A
    out_rgb[1] = row[1];
    out_rgb[2] = row[0];

    device->unmap_texture_region(staging_readback_tex, 0);
    return true;
}

// Init/destroy
static void on_init_swapchain(reshade::api::swapchain* swapchain, bool)
{
    g_sc = swapchain;
    auto device = swapchain->get_device();
    auto bb = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(bb);

    std::wstringstream ss;
    ss << L"Backbuffer: w=" << bb_desc.texture.width << L" h=" << bb_desc.texture.height << L" fmt=" << (int)bb_desc.texture.format;
    log_info(ss.str());

    // Try to create gpu_write_tex and staging_readback_tex using the backbuffer format
    if (!create_gpu_write_texture(device, bb_desc.texture.format))
    {
        log_info(L"create_gpu_write_texture failed - GPU write path unavailable.");
    }
    if (!create_staging_readback_texture(device, bb_desc.texture.format))
    {
        log_info(L"create_staging_readback_texture failed - readback unavailable.");
    }
}

static void on_destroy_swapchain(reshade::api::swapchain* swapchain, bool)
{
    auto device = swapchain->get_device();
    if (gpu_write_uav.handle != 0) device->destroy_resource_view(gpu_write_uav);
    if (gpu_write_tex.handle != 0) device->destroy_resource(gpu_write_tex);
    if (staging_readback_tex.handle != 0) device->destroy_resource(staging_readback_tex);
    gpu_write_tex = {};
    staging_readback_tex = {};
    gpu_write_uav = {};
}

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*, uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE) return;
    auto device = swapchain->get_device();
    auto backbuffer = swapchain->get_current_back_buffer();

    uint8_t rgb[3] = { 0,0,0 };
    if (gpu_write_tex.handle != 0 && staging_readback_tex.handle != 0)
    {
        // Attempt to sample pixel (0,0)
        if (!dispatch_sample_and_read(device, queue, backbuffer, 0, 0, rgb))
        {
            log_info(L"dispatch_sample_and_read failed");
        }
    }
    else
    {
        log_info(L"GPU write or staging texture not available; skipping readback.");
    }

    uint32_t trigger = (uint32_t)rgb[0] + (uint32_t)rgb[1] + (uint32_t)rgb[2];
    char msg[64];
    if (trigger > (uint32_t)iThreshold) {
        sprintf_s(msg, "9, 0\n"); 
        left_eye_count++; 
    }
    else {
        sprintf_s(msg, "9, 1\n"); 
        right_eye_count++; 
    }
    DWORD written; WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);

    auto now = std::chrono::steady_clock::now();
    if (std::chrono::duration_cast<std::chrono::seconds>(now - last_log_time).count() >= 1)
    {
        log_info(L"Left eye signals: " + std::to_wstring(left_eye_count.load()) + L" | Right eye signals: " + std::to_wstring(right_eye_count.load()));
        left_eye_count = 0; right_eye_count = 0; last_log_time = now;
    }
}

BOOL WINAPI DllMain(HMODULE hModule, DWORD fdwReason, LPVOID)
{
    if (fdwReason == DLL_PROCESS_ATTACH)
    {
        read_settings(); open_serial_port();
        if (!reshade::register_addon(hModule)) return FALSE;
        reshade::register_event<reshade::addon_event::present>(on_present);
        reshade::register_event<reshade::addon_event::init_swapchain>(on_init_swapchain);
        reshade::register_event<reshade::addon_event::destroy_swapchain>(on_destroy_swapchain);
    }
    else if (fdwReason == DLL_PROCESS_DETACH)
    {
        if (hSerial != INVALID_HANDLE_VALUE) CloseHandle(hSerial);
        reshade::unregister_addon(hModule);
    }
    return TRUE;
}
