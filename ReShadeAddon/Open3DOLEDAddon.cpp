#include <reshade.hpp>
#include <windows.h>
#include <string>

static HANDLE hSerial = INVALID_HANDLE_VALUE;

static void on_present(reshade::api::command_queue* queue, reshade::api::swapchain* swapchain,
    const reshade::api::rect*, const reshade::api::rect*,
    uint32_t, const reshade::api::rect*)
{
    if (hSerial == INVALID_HANDLE_VALUE)
        return;

    auto device = swapchain->get_device();
    reshade::api::resource backbuffer = swapchain->get_current_back_buffer();

    // Get backbuffer description
    reshade::api::resource_desc bb_desc = device->get_resource_desc(backbuffer);

    // Create 1x1 staging texture
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



    // Copy pixel using immediate command list
    reshade::api::command_list* cmd = queue->get_immediate_command_list();
    reshade::api::subresource_box box = { 0,0,0,1,1,1 };
    cmd->copy_texture_region(backbuffer, 0, nullptr, staging, 0, &box);

    // Map staging texture
    reshade::api::subresource_data mapped = {};
    if (device->map_texture_region(staging, 0, nullptr, reshade::api::map_access::read_only, &mapped))
    {
        const uint8_t* rgba = reinterpret_cast<const uint8_t*>(mapped.data);

        // Format string and send over serial
        char msg[64];
        sprintf_s(msg, "R=%d G=%d B=%d\n", rgba[0], rgba[1], rgba[2]);

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
        // Open COM3 at 115200 baud (adjust as needed)
        hSerial = CreateFileW(L"\\\\.\\COM3",
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
        }

        reshade::register_event<reshade::addon_event::present>(on_present);
    }
    else if (fdwReason == DLL_PROCESS_DETACH)
    {
        if (hSerial != INVALID_HANDLE_VALUE)
            CloseHandle(hSerial);
    }

    return TRUE;
}
