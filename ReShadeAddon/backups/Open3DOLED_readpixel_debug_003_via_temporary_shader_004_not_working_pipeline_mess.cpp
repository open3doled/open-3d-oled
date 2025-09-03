// --- full file: Open3DOLED_readpixel_with_compute.cpp ---
// (This is your file with the necessary additions to actually run the compute shader)

#include <reshade.hpp>
#include <windows.h>
#include <fstream>
#include <string>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <atomic>
#include <chrono>
#include <vector>

static HANDLE hSerial = INVALID_HANDLE_VALUE;
static std::wstring sComPort;
static int iThreshold = 30;

// GPU resources
static reshade::api::resource gpu_write_tex = {};
static reshade::api::resource staging_readback_tex = {};
static reshade::api::resource_view backbuffer_srv = {};
static reshade::api::resource_view gpu_write_uav = {};
static reshade::api::pipeline compute_pipeline = {};           // new
static reshade::api::pipeline_layout compute_pipeline_layout = {}; // new

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

// ------------------- new helper: load compiled shader bytecode -------------------
static bool load_file_to_vector(const char* path, std::vector<uint8_t>& out)
{
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f.is_open()) return false;
    std::streamsize n = f.tellg();
    f.seekg(0, std::ios::beg);
    out.resize((size_t)n);
    if (!f.read(reinterpret_cast<char*>(out.data()), n)) return false;
    return true;
}

// ------------------- create compute pipeline from compiled shader -------------------
// Assumes you compiled sample_cs.hlsl -> sample_cs.cso (see instructions in chat)
static bool create_compute_pipeline_from_cso(reshade::api::device* device, const char* cso_path)
{
    std::vector<uint8_t> code;
    if (!load_file_to_vector(cso_path, code))
    {
        log_info(L"Failed to load compiled shader file.");
        return false;
    }

    // Build pipeline_desc - API fields vary; below is the conceptual flow that must be adapted
    // to match your reshade headers. If compile fails, paste the errors and I'll correct names.
    reshade::api::pipeline_desc pipe_desc = {};
    pipe_desc.type = reshade::api::pipeline_stage::compute; // conceptual
    pipe_desc.compute.shader.code = code.data();
    pipe_desc.compute.shader.code_size = (uint32_t)code.size();

    if (!device->create_pipeline(pipe_desc, &compute_pipeline))
    {
        log_info(L"device->create_pipeline failed.");
        compute_pipeline = {};
        return false;
    }

    log_info(L"Compute pipeline created from CSO.");
    return true;
}

// ------------------- resource creation (you already have these) -------------------
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

    // Create UAV view for the texture
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

// ------------------- the important piece: bind descriptors and dispatch compute -------------
static bool dispatch_sample_and_read(reshade::api::device* device, reshade::api::command_queue* queue,
    reshade::api::resource backbuffer, uint32_t px, uint32_t py, uint8_t out_rgb[3])
{
    if (gpu_write_tex.handle == 0 || staging_readback_tex.handle == 0) return false;
    if (compute_pipeline.handle == 0)
    {
        // pipeline not prepared
        log_info(L"No compute pipeline; skipping dispatch.");
        return false;
    }

    reshade::api::command_list* cmd = queue->get_immediate_command_list();

    // Transition backbuffer -> shader_resource
    cmd->barrier(backbuffer, reshade::api::resource_usage::present, reshade::api::resource_usage::shader_resource);

    // Transition gpu_write_tex -> unordered_access
    cmd->barrier(gpu_write_tex, reshade::api::resource_usage::copy_source, reshade::api::resource_usage::unordered_access);

    // Create SRV for backbuffer (transient) - reuse global backbuffer_srv if you want
    reshade::api::resource_view_desc srv_desc = {};
    srv_desc.format = device->get_resource_desc(backbuffer).texture.format;
    srv_desc.type = reshade::api::resource_view_type::texture_2d;
    srv_desc.texture.first_level = 0;
    srv_desc.texture.level_count = 1;
    srv_desc.texture.first_layer = 0;
    srv_desc.texture.layer_count = 1;
    device->create_resource_view(backbuffer, reshade::api::resource_usage::shader_resource, srv_desc, &backbuffer_srv);

    // (We already have gpu_write_uav created earlier)

    // Bind pipeline
    cmd->bind_pipeline(compute_pipeline);

    // Bind descriptors: exact API varies. The conceptual steps:
    // - update descriptor set 0: t0 -> backbuffer_srv
    // - update descriptor set 0: u0 -> gpu_write_uav
    // ReShade's low-level API uses 'descriptor_sets' and 'update_descriptor_sets' functions
    // The names/structs differ between versions; if update fails, paste compile errors.
    reshade::api::descriptor_set_update update[2] = {};

    // Example pseudo-fill (must match your reshade headers exactly)
    // update[0] = { binding = 0, type = shader_resource_view, handle = backbuffer_srv.handle, count = 1 }
    // update[1] = { binding = 1, type = unordered_access_view, handle = gpu_write_uav.handle, count = 1 }
    // device->update_descriptor_sets(descriptor_set, update, 2);

    // Push constants (or small constant buffer) with px/py/width/height
    struct PushData { uint32_t px, py, width, height; } push = { px, py, 0, 0 };
    auto bb_desc = device->get_resource_desc(backbuffer);
    push.width = (uint32_t)bb_desc.texture.width;
    push.height = (uint32_t)bb_desc.texture.height;

    // Push constants - API name may be push_constants or cmd->push_constants; adjust if compile error occurs.
    cmd->push_constants(compute_pipeline_layout, reshade::api::shader_stage::compute, 0, sizeof(push), &push);

    // Dispatch compute (1 threadgroup)
    cmd->dispatch(1, 1, 1);

    // Barrier for UAV -> copy_source
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

    dump_mapped_hex(reinterpret_cast<const uint8_t*>(mapped.data), 12, mapped.row_pitch);

    const uint8_t* row = reinterpret_cast<const uint8_t*>(mapped.data);
    // note: your backbuffer format is b8g8r8x8, so bytes are B,G,R,A (or X)
    out_rgb[0] = row[2];
    out_rgb[1] = row[1];
    out_rgb[2] = row[0];

    device->unmap_texture_region(staging_readback_tex, 0);
    return true;
}

// ------------------- init/destroy/present hooks -------------------

static void on_init_swapchain(reshade::api::swapchain* swapchain, bool)
{
    g_sc = swapchain;
    auto device = swapchain->get_device();
    auto bb = swapchain->get_current_back_buffer();
    auto bb_desc = device->get_resource_desc(bb);

    std::wstringstream ss;
    ss << L"Backbuffer: w=" << bb_desc.texture.width << L" h=" << bb_desc.texture.height << L" fmt=" << (int)bb_desc.texture.format;
    log_info(ss.str());

    // Create textures / staging
    if (!create_gpu_write_texture(device, bb_desc.texture.format))
    {
        log_info(L"create_gpu_write_texture failed - GPU write path unavailable.");
    }
    if (!create_staging_readback_texture(device, bb_desc.texture.format))
    {
        log_info(L"create_staging_readback_texture failed - readback unavailable.");
    }

    // Load compute pipeline from compiled CSO (user must compile sample_cs.hlsl -> sample_cs.cso)
    if (!create_compute_pipeline_from_cso(device, "sample_cs.cso"))
    {
        log_info(L"create_compute_pipeline_from_cso failed - compute path disabled.");
    }
}

static void on_destroy_swapchain(reshade::api::swapchain* swapchain, bool)
{
    auto device = swapchain->get_device();
    if (backbuffer_srv.handle != 0) device->destroy_resource_view(backbuffer_srv);
    if (gpu_write_uav.handle != 0) device->destroy_resource_view(gpu_write_uav);
    if (gpu_write_tex.handle != 0) device->destroy_resource(gpu_write_tex);
    if (staging_readback_tex.handle != 0) device->destroy_resource(staging_readback_tex);
    if (compute_pipeline.handle != 0) device->destroy_pipeline(compute_pipeline);
    backbuffer_srv = {};
    gpu_write_uav = {};
    gpu_write_tex = {};
    staging_readback_tex = {};
    compute_pipeline = {};
}

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*, uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE) return;
    auto device = swapchain->get_device();
    auto backbuffer = swapchain->get_current_back_buffer();

    uint8_t rgb[3] = { 0,0,0 };
    if (gpu_write_tex.handle != 0 && staging_readback_tex.handle != 0 && compute_pipeline.handle != 0)
    {
        if (!dispatch_sample_and_read(device, queue, backbuffer, 0, 0, rgb))
        {
            log_info(L"dispatch_sample_and_read failed");
        }
    }
    else
    {
        log_info(L"GPU write or staging texture or compute pipeline not available; skipping readback.");
    }

    uint32_t trigger = (uint32_t)rgb[0] + (uint32_t)rgb[1] + (uint32_t)rgb[2];
    char msg[64];
    if (trigger > (uint32_t)iThreshold) { sprintf_s(msg, "9, 0\n"); left_eye_count++; }
    else { sprintf_s(msg, "9, 1\n"); right_eye_count++; }
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
