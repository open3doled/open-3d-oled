#include <reshade.hpp>
#include <windows.h>
#include <string>

static HANDLE hSerial = INVALID_HANDLE_VALUE;

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID)
{
    if (fdwReason == DLL_PROCESS_ATTACH)
    {
        // Open COM3 at 115200 baud
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
            dcb.Parity   = NOPARITY;
            SetCommState(hSerial, &dcb);
        }

        reshade::register_event<reshade::addon_event::present>(
            [](reshade::api::command_queue *queue,
               reshade::api::swapchain *swapchain,
               const reshade::api::rect *, const reshade::api::rect *,
               uint32_t, const reshade::api::rect *)
            {
                if (hSerial == INVALID_HANDLE_VALUE)
                    return;

                // Get current frame backbuffer
                auto backbuffer = swapchain->get_current_back_buffer();
                auto device = swapchain->get_device();

                // Create 1x1 staging texture
                auto desc = backbuffer.get_desc();
                desc.width = 1;
                desc.height = 1;
                desc.heap = reshade::api::memory_heap::cpu_to_gpu;
                desc.usage = reshade::api::resource_usage::copy_dest |
                             reshade::api::resource_usage::cpu_access;

                reshade::api::resource staging;
                if (device->create_resource(desc, nullptr,
                                            reshade::api::resource_usage::copy_dest, &staging))
                {
                    reshade::api::subresource_box box = {0, 0, 0, 1, 1, 1};
                    queue->copy_texture_region(backbuffer, 0, nullptr, staging, 0, &box);

                    void *data = nullptr;
                    if (queue->map_buffer_region(staging, 0, nullptr,
                                                 reshade::api::map_access::read_only, &data))
                    {
                        uint8_t *rgba = reinterpret_cast<uint8_t *>(data);

                        // Format string: R=123 G=45 B=67\n
                        char msg[64];
                        sprintf_s(msg, "R=%d G=%d B=%d\n", rgba[0], rgba[1], rgba[2]);

                        DWORD written;
                        WriteFile(hSerial, msg, (DWORD)strlen(msg), &written, nullptr);

                        queue->unmap_buffer_region(staging);
                    }

                    device->destroy_resource(staging);
                }
            }
        );
    }
    else if (fdwReason == DLL_PROCESS_DETACH)
    {
        if (hSerial != INVALID_HANDLE_VALUE)
            CloseHandle(hSerial);
    }

    return TRUE;
}
